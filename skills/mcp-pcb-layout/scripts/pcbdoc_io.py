"""Read and patch an Altium PcbDoc (AD 19+ binary format) without Altium, using olefile.

Only fixed-size fields are ever written, so no stream changes length. Verified on AD 23.1.1 files (QPA2609, 2026-10).
Units: Altium internal = 1e-4 mil; everything here is returned / taken in mil, absolute board coordinates.

Record layouts used (first subrecord, offsets in bytes; same as KiCad's Altium importer):
  Texts6   type 5 : @0 legacy layer u8, @7 component index u16 (65535 = free text), @13 x i32, @17 y i32,
                    @21 height i32, @27 rotation f64, @35 mirror u8, @36 stroke width i32, @40 isComment u8,
                    @41 isDesignator u8, @226 V7 layer u32  <- Altium READS THIS ONE; keep both in step.
                    Second subrecord = u32 length + text (pascal-prefixed, latin-1).
  Tracks6  type 4 : @0 layer, @7 component, @13 x1 @17 y1 @21 x2 @25 y2 @29 width (i32)
  Arcs6    type 1 : @0 layer, @7 component, @13 cx @17 cy @21 radius (i32), @25 start f64, @33 end f64, @41 width i32
  Vias6    type 3 : @13 x @17 y @21 diameter (i32)
  BoardRegions    : property string (OBJECTKIND=BoardRegion ... LAYERSTACKID={...}) then 0x00/0x?? byte, u32 vertex count,
                    vertices as (x f64, y f64). This is the "Layer Stack Region"; pcb_set_board_shape does NOT update it.
  Components6     : one '|KEY=VALUE|...' string per component, in component-index order (SOURCEDESIGNATOR, X, Y, ROTATION ...).

CLI (read-only unless stated):
  python -I pcbdoc_io.py summary  <PcbDoc>              counts per layer, board region, V7 consistency
  python -I pcbdoc_io.py texts    <PcbDoc> [layer]      list texts (layer name e.g. TopOverlay, Mechanical13)
  python -I pcbdoc_io.py v7check  <PcbDoc>              texts whose two layer fields disagree
  python -I pcbdoc_io.py v7fix    <PcbDoc>              WRITES: make @226 agree with @0 (close the project in AD first)
"""
import struct, sys, collections, olefile

LAYER = {1: 'TopLayer', 32: 'BottomLayer', 33: 'TopOverlay', 34: 'BottomOverlay', 74: 'MultiLayer', 56: 'KeepOutLayer', 35: 'TopPaste', 36: 'BottomPaste', 37: 'TopSolder', 38: 'BottomSolder', 55: 'DrillGuide', 73: 'DrillDrawing'}
LAYER.update({56 + i: f'Mechanical{i}' for i in range(1, 17)})
LAYER[56] = 'KeepOutLayer'
LAYER.update({1 + i: f'MidLayer{i}' for i in range(1, 31)})
LAYER_ID = {v: k for k, v in LAYER.items()}
FREE = 65535
V7_OFF = 226


# ---------------------------------------------------------------- generic record walking
def _records(data, rtype, two_sub=False):
    """Yield (offset of first subrecord, its length, offset just past the record)."""
    i = 0
    while i < len(data):
        t = data[i]; n = struct.unpack_from('<I', data, i + 1)[0]
        if t != rtype:
            raise ValueError(f'unexpected record type {t} at {i} (want {rtype})')
        s = i + 5; j = s + n
        if two_sub:
            j += 4 + struct.unpack_from('<I', data, j)[0]
        yield s, n, j
        i = j


def _stream(path, name):
    o = olefile.OleFileIO(path)
    try:
        return o.openstream(name).read()
    finally:
        o.close()


def component_names(path):
    """Designators in component-index order (index = the u16 'component' field of primitives)."""
    txt = _stream(path, 'Components6/Data').decode('latin-1')
    return [dict(kv.split('=', 1) for kv in r.strip('|').split('|') if '=' in kv).get('SOURCEDESIGNATOR')
            for r in txt.split('\x00') if 'SOURCEDESIGNATOR' in r]


# ---------------------------------------------------------------- texts
def read_texts(path):
    data = _stream(path, 'Texts6/Data')
    names = component_names(path)
    out = []
    for idx, (s, n, end) in enumerate(_records(data, 5, two_sub=True)):
        j = s + n; m = struct.unpack_from('<I', data, j)[0]
        text = data[j + 4:j + 4 + m].decode('latin-1').rstrip('\x00')
        if text and ord(text[0]) == len(text) - 1:
            text = text[1:]
        comp = struct.unpack_from('<H', data, s + 7)[0]
        x, y, h = struct.unpack_from('<iii', data, s + 13)
        out.append(dict(idx=idx, off=s, layer=LAYER.get(data[s], data[s]),
                        v7=struct.unpack_from('<I', data, s + V7_OFF)[0] if n >= V7_OFF + 4 else None,
                        comp=comp, owner=None if comp == FREE or comp >= len(names) else names[comp],
                        x=x / 1e4, y=y / 1e4, h=h / 1e4, rot=struct.unpack_from('<d', data, s + 27)[0],
                        mirror=data[s + 35], width=struct.unpack_from('<i', data, s + 36)[0] / 1e4,
                        is_comment=bool(data[s + 40]), is_designator=bool(data[s + 41]), text=text))
    return out


def v7_map(data):
    """legacy layer id -> V7 layer code, learned from the records (majority pair per legacy id)."""
    pairs = collections.Counter((data[s], struct.unpack_from('<I', data, s + V7_OFF)[0]) for s, n, _ in _records(data, 5, True))
    best = {}
    for (a, b), c in pairs.most_common():
        best.setdefault(a, b)
    return best, pairs


def patch_texts(path, edits):
    """edits: list of (record offset `off` from read_texts, {layer, x, y, rot, h, width}) -- mil / degrees / layer name.
    Writes BOTH layer fields. Raises if the target layer's V7 code is not already present in the file."""
    o = olefile.OleFileIO(path, write_mode=True)
    try:
        data = bytearray(o.openstream('Texts6/Data').read())
        vmap, _ = v7_map(data)
        for s, e in edits:
            if 'layer' in e:
                lid = LAYER_ID[e['layer']]
                if lid not in vmap:
                    raise KeyError(f"no text on {e['layer']} in this file to learn its V7 code from; check by hand")
                data[s] = lid
                struct.pack_into('<I', data, s + V7_OFF, vmap[lid])
            if 'x' in e: struct.pack_into('<i', data, s + 13, round(e['x'] * 1e4))
            if 'y' in e: struct.pack_into('<i', data, s + 17, round(e['y'] * 1e4))
            if 'h' in e: struct.pack_into('<i', data, s + 21, round(e['h'] * 1e4))
            if 'rot' in e: struct.pack_into('<d', data, s + 27, float(e['rot']))
            if 'width' in e: struct.pack_into('<i', data, s + 36, round(e['width'] * 1e4))
        o.write_stream('Texts6/Data', bytes(data))
    finally:
        o.close()


def v7_inconsistent(path):
    data = _stream(path, 'Texts6/Data')
    vmap, pairs = v7_map(data)
    bad = [s for s, n, _ in _records(data, 5, True) if vmap.get(data[s]) != struct.unpack_from('<I', data, s + V7_OFF)[0]]
    return bad, vmap, pairs


def v7_fix(path):
    bad, vmap, _ = v7_inconsistent(path)
    o = olefile.OleFileIO(path, write_mode=True)
    try:
        data = bytearray(o.openstream('Texts6/Data').read())
        for s in bad:
            struct.pack_into('<I', data, s + V7_OFF, vmap[data[s]])
        o.write_stream('Texts6/Data', bytes(data))
    finally:
        o.close()
    return len(bad)


# ---------------------------------------------------------------- board region (layer stack region)
def _region_vertex_base(b):
    k = b.find(b'}', b.find(b'LAYERSTACKID')) + 1
    return k, struct.unpack_from('<I', b, k + 1)[0]


def read_region(path):
    b = _stream(path, 'BoardRegions/Data')
    k, nv = _region_vertex_base(b)
    return [tuple(v / 1e4 for v in struct.unpack_from('<dd', b, k + 5 + 16 * i)) for i in range(nv)]


def region_move_edge(path, axis, old, new, tol=1.0):
    """Move every region vertex whose x (axis='x') or y (axis='y') is within tol mil of `old` to `new`. Returns count."""
    o = olefile.OleFileIO(path, write_mode=True)
    try:
        b = bytearray(o.openstream('BoardRegions/Data').read())
        k, nv = _region_vertex_base(b)
        moved = 0
        for v in range(nv):
            p = k + 5 + 16 * v + (0 if axis == 'x' else 8)
            if abs(struct.unpack_from('<d', b, p)[0] / 1e4 - old) < tol:
                struct.pack_into('<d', b, p, new * 1e4); moved += 1
        o.write_stream('BoardRegions/Data', bytes(b))
    finally:
        o.close()
    return moved


# ---------------------------------------------------------------- tracks / arcs / vias
def read_tracks(path, layer=None):
    data = _stream(path, 'Tracks6/Data'); out = []
    for s, n, _ in _records(data, 4):
        if layer is None or data[s] == LAYER_ID[layer]:
            x1, y1, x2, y2, w = (v / 1e4 for v in struct.unpack_from('<iiiii', data, s + 13))
            out.append(dict(layer=LAYER.get(data[s], data[s]), comp=struct.unpack_from('<H', data, s + 7)[0],
                            x1=x1, y1=y1, x2=x2, y2=y2, width=w))
    return out


def read_arcs(path, layer=None):
    data = _stream(path, 'Arcs6/Data'); out = []
    for s, n, _ in _records(data, 1):
        if layer is None or data[s] == LAYER_ID[layer]:
            cx, cy, r = (v / 1e4 for v in struct.unpack_from('<iii', data, s + 13))
            a0, a1 = struct.unpack_from('<dd', data, s + 25)
            out.append(dict(layer=LAYER.get(data[s], data[s]), comp=struct.unpack_from('<H', data, s + 7)[0],
                            cx=cx, cy=cy, r=r, a0=a0, a1=a1, width=struct.unpack_from('<i', data, s + 41)[0] / 1e4))
    return out


def read_vias(path):
    data = _stream(path, 'Vias6/Data'); out = []
    for s, n, _ in _records(data, 3):
        x, y, d = (v / 1e4 for v in struct.unpack_from('<iii', data, s + 13))
        out.append(dict(x=x, y=y, diameter=d))
    return out


# ---------------------------------------------------------------- CLI
if __name__ == '__main__':
    cmd, path = sys.argv[1], sys.argv[2]
    if cmd == 'summary':
        T = read_texts(path)
        print('texts per layer', dict(collections.Counter(t['layer'] for t in T)))
        print('tracks per layer', dict(collections.Counter(t['layer'] for t in read_tracks(path))))
        print('arcs', len(read_arcs(path)), 'vias', len(read_vias(path)), 'components', len(component_names(path)))
        print('board region vertices (mil)', read_region(path))
        bad, vmap, pairs = v7_inconsistent(path)
        print('legacy->V7 layer pairs', {(LAYER.get(a, a), hex(b)): c for (a, b), c in pairs.items()}, '| inconsistent texts', len(bad))
    elif cmd == 'texts':
        lay = sys.argv[3] if len(sys.argv) > 3 else None
        for t in read_texts(path):
            if lay is None or t['layer'] == lay:
                print(f"{t['idx']:4d} {t['layer']:13s} {t['text']!r:18s} owner={t['owner']!s:8s} "
                      f"{'D' if t['is_designator'] else ' '}{'C' if t['is_comment'] else ' '} "
                      f"({t['x']:.3f}, {t['y']:.3f}) rot {t['rot']:g} h {t['h']:g} w {t['width']:g}")
    elif cmd == 'v7check':
        bad, vmap, pairs = v7_inconsistent(path)
        print('inconsistent texts:', len(bad))
    elif cmd == 'v7fix':
        print('fixed', v7_fix(path), '| still inconsistent', len(v7_inconsistent(path)[0]))
    else:
        sys.exit(__doc__)

"""Read / patch text records in an Altium PcbDoc (Texts6/Data) and the board region (BoardRegions/Data).

Text record = type byte 5, uint32 length, then the first subrecord (layout as in KiCad's ATEXT6 parser):
  @0 layer u8 | @7 component u16 | @13 x int32 | @17 y int32 | @21 height int32 | @27 rotation double
  @35 mirror u8 | @36 stroke width int32 | @40 isComment u8 | @41 isDesignator u8
then a second subrecord (uint32 length + string). Coordinates are 1e-4 mil, absolute.
Everything patched here is fixed size, so the stream length never changes."""
import olefile, struct

LAYER = {33: 'TopOverlay', 34: 'BottomOverlay'}
for i in range(1, 17):
    LAYER[56 + i] = f'Mechanical{i}'
LAYER_ID = {v: k for k, v in LAYER.items()}
V7_LAYER = {'TopOverlay': 0x01030006, 'Mechanical13': 0x0102000D}   # seen in AD 23 files; add others only after checking


def read_texts(path):
    o = olefile.OleFileIO(path)
    data = o.openstream('Texts6/Data').read()
    o.close()
    out, i, idx = [], 0, 0
    while i < len(data):
        t = data[i]; n = struct.unpack_from('<I', data, i + 1)[0]
        assert t == 5, (i, t)
        s = i + 5                                   # start of first subrecord
        layer = data[s]
        comp = struct.unpack_from('<H', data, s + 7)[0]
        x, y, h = struct.unpack_from('<iii', data, s + 13)
        rot = struct.unpack_from('<d', data, s + 27)[0]
        width = struct.unpack_from('<i', data, s + 36)[0]
        is_c, is_d = data[s + 40], data[s + 41]
        j = s + n                                   # second subrecord: uint32 len + string
        m = struct.unpack_from('<I', data, j)[0]
        text = data[j + 4:j + 4 + m].decode('latin-1')
        text = text[1:] if text and ord(text[0]) == len(text) - 1 else text   # pascal length prefix
        out.append(dict(idx=idx, off=s, layer=LAYER.get(layer, layer), comp=comp, x=x / 1e4, y=y / 1e4,
                        h=h / 1e4, rot=rot, width=width / 1e4, is_comment=is_c, is_designator=is_d,
                        text=text.rstrip('\x00')))
        i = j + 4 + m; idx += 1
    return out


def patch(path, text_edits, region_top=None):
    """text_edits: list of (record offset, dict with any of layer/x/y/rot). region_top: new top y (mil) for the board region."""
    o = olefile.OleFileIO(path, write_mode=True)
    data = bytearray(o.openstream('Texts6/Data').read())
    for s, e in text_edits:
        if 'layer' in e:                    # legacy byte AND the V7 layer u32 @226 (AD reads the V7 one)
            data[s] = LAYER_ID[e['layer']]
            struct.pack_into('<I', data, s + 226, V7_LAYER[e['layer']])
        if 'x' in e: struct.pack_into('<i', data, s + 13, round(e['x'] * 1e4))
        if 'y' in e: struct.pack_into('<i', data, s + 17, round(e['y'] * 1e4))
        if 'rot' in e: struct.pack_into('<d', data, s + 27, float(e['rot']))
        if 'h' in e: struct.pack_into('<i', data, s + 21, round(e['h'] * 1e4))
        if 'width' in e: struct.pack_into('<i', data, s + 36, round(e['width'] * 1e4))
    o.write_stream('Texts6/Data', bytes(data))
    if region_top is not None:
        b = bytearray(o.openstream('BoardRegions/Data').read())
        k = b.find(b'}', b.find(b'LAYERSTACKID')) + 1
        nv = struct.unpack_from('<I', b, k + 1)[0]
        for v in range(nv):
            p = k + 5 + 16 * v
            x, y = struct.unpack_from('<dd', b, p)
            if abs(y / 1e4 - 3758.6225) < 1:
                struct.pack_into('<d', b, p + 8, region_top * 1e4)
        o.write_stream('BoardRegions/Data', bytes(b))
    o.close()


def read_region(path):
    o = olefile.OleFileIO(path)
    b = o.openstream('BoardRegions/Data').read(); o.close()
    k = b.find(b'}', b.find(b'LAYERSTACKID')) + 1
    nv = struct.unpack_from('<I', b, k + 1)[0]
    return [tuple(v / 1e4 for v in struct.unpack_from('<dd', b, k + 5 + 16 * i)) for i in range(nv)]


if __name__ == '__main__':
    import sys, csv, collections
    T = read_texts(sys.argv[1])
    print(len(T), collections.Counter(t['layer'] for t in T))
    csvp = r'E:\<项目根>\电路控制\temp\eda_check\top_overlay_texts.csv'
    ref = list(csv.DictReader(open(csvp, encoding='utf-8-sig')))
    top = [t for t in T if t['layer'] == 'TopOverlay']
    bad = 0
    for r in ref:
        m = [t for t in top if abs(t['x'] - float(r['X'])) < 0.01 and abs(t['y'] - float(r['Y'])) < 0.01]
        if len(m) != 1 or abs(m[0]['rot'] - float(r['Rotation'])) > 1e-6 or abs(m[0]['h'] - float(r['Height'])) > 0.01:
            bad += 1; print('MISMATCH', r['Text'], r['X'], r['Y'], [(t['text'], t['rot'], t['h']) for t in m])
    print('csv rows', len(ref), 'top overlay parsed', len(top), 'mismatches', bad)
    print(read_region(sys.argv[1]))

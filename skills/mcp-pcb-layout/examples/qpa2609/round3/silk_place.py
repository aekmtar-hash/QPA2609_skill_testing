"""Round 3 silkscreen: place the 10 key designators and 11 strings clear of every overlay line, text and pad.
Writes placement.json (board-relative mm + absolute mil) and placement.png; prints every check."""
import sys, os, json, math, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import olefile
from shapely.geometry import box, Point
from shapely.ops import unary_union
from silk_model import mm, text_box, pads, overlay_geoms, PCB, DX, DY, MM, H
from pcbdoc_text import read_texts

K = 0.85                     # char advance / height (calibrated 0.80, + margin)
SILK_GAP = 0.30              # rule 0.254
PAD_GAP = 0.40               # pad copper -> silk: mask expansion 0.102 + rule 0.254 + margin
EDGE = 0.25
BOARD = (0.0, 0.0, 25.4, 108.5)
CUT = (6.0, 19.4)
HERE = os.path.dirname(os.path.abspath(__file__))

names = [dict(kv.split('=', 1) for kv in r.strip('|').split('|') if '=' in kv)['SOURCEDESIGNATOR']
         for r in olefile.OleFileIO(PCB).openstream('Components6/Data').read().decode('latin-1').split('\x00')
         if 'SOURCEDESIGNATOR' in r]
T = read_texts(PCB)
owner = lambda t: names[t['comp']] if t['comp'] < len(names) else None

HIDE_COMPS = {'FB101', 'FB102', 'LED101', 'Q101', 'Q102', 'U101', 'U103', 'D101', 'RV101', 'F101', 'U102'}
hide = [t for t in T if t['layer'] == 'TopOverlay' and not t['is_designator'] and not t['is_comment']
        and owner(t) in HIDE_COMPS and t['text'] in ('.Designator', 'REFDES', 'RefDes')]
free = [t for t in T if t['layer'] == 'TopOverlay' and t['comp'] == 65535]
REPLICA = {'R111', 'R116', 'P101', 'RV101', 'D101', 'U103', 'U101', 'U102'}
replicas = [t for t in free if t['text'] in REPLICA]
strings = [t for t in free if t['text'] not in REPLICA]
real = {t['text']: t for t in T if t['is_designator'] and owner(t) == t['text']
        and t['text'] in REPLICA | {'F101', 'TP103'}}
assert len(hide) == 13 and len(replicas) == 8 and len(strings) == 11 and len(real) == 10, (len(hide), len(replicas), len(strings), len(real))

# ---- obstacles -------------------------------------------------------------------------------------
P = pads()
pad_by_comp = {}
for p in P:
    pad_by_comp.setdefault(p['comp'], []).append(p['geom'])
pad_all = unary_union([p['geom'] for p in P])
BODY_GAP = 0.10            # a text may not sit on top of any component (convex hull of its pads + outline)
OG = overlay_geoms()
over = unary_union([g for _, _, g in OG])
comp_geom = {c: unary_union(gs) for c, gs in pad_by_comp.items()}
for _, ci, g in OG:
    n = names[ci] if ci < len(names) else None
    if n:
        comp_geom[n] = comp_geom[n].union(g) if n in comp_geom else g
bodies = unary_union([g.convex_hull for g in comp_geom.values()])
moving = {id(t) for t in hide + replicas + strings} | {id(t) for t in real.values()}
keep_txt = []
for t in T:
    if t['layer'] != 'TopOverlay' or t['is_comment'] or id(t) in moving:
        continue
    s = owner(t) if t['text'] == '.Designator' else t['text']
    keep_txt.append(text_box(s, *mm(t['x'], t['y']), t['rot'], h=t['h'] * MM, stroke=t['width'] * MM, k=K))
fixed_silk = unary_union([over] + keep_txt)
vias = []
o = olefile.OleFileIO(PCB)
d = o.openstream('Vias6/Data').read(); i = 0
import struct
while i < len(d):
    n = struct.unpack_from('<I', d, i + 1)[0]; r = d[i + 5:i + 5 + n]; i += 5 + n
    x, y, dia = struct.unpack_from('<iii', r, 13)
    vias.append(Point(*mm(x / 1e4, y / 1e4)).buffer(dia / 2e4 * MM))
via_u = unary_union(vias)
print('obstacles: overlay lines/arcs, %d kept texts, %d pads, %d vias' % (len(keep_txt), len(P), len(vias)))

# ---- what to place ---------------------------------------------------------------------------------
items = []
for t in replicas:                                   # 8 designators: start from the round-2 target (the replica)
    items.append(dict(kind='designator', text=t['text'], own=t['text'], start=mm(t['x'], t['y']), rot=t['rot']))
for n in ('F101', 'TP103'):
    t = real[n]; items.append(dict(kind='designator', text=n, own=n, start=mm(t['x'], t['y']), rot=t['rot']))
STR_OWN = {'+12V': 'P101', '-5V': 'TP103', 'VD': 'J3', '+3.5V': 'J3', 'VG': 'J4', 'NEG': 'J4', 'ADJ': 'RV101', 'QPA2609 MODULE': None}
for t in strings:
    x, y = mm(t['x'], t['y'])
    own = STR_OWN.get(t['text'])
    if t['text'] == 'GND':
        own = 'P101' if y > 90 else ('J5' if y > 40 else 'J6')
    items.append(dict(kind='string', text=t['text'], own=own, start=(x, y), rot=t['rot']))
START = {'P101': (0.5, 107.05)}
ROT_START = {'+12V': ((4.95, 104.4), 90.0), 'GND@P101': ((4.95, 101.5), 90.0)}
# the 14-char module name has no free 12 mm strip inside the cut lines: split into two lines
_m = [it for it in items if it['text'] == 'QPA2609 MODULE'][0]
items.remove(_m)
items.append(dict(kind='string', text='QPA2609', own=None, start=(12.7, 80.0), rot=90.0))
items.append(dict(kind='string', text='MODULE', own=None, start=None, rot=90.0, follow='QPA2609'))
for it in items:
    if it['text'] in START:
        it['start'] = START[it['text']]
    it['win'] = 4.0
    it['step'] = 0.05
    if it['text'] == 'QPA2609':
        it['win'], it['step'] = 28.0, 0.1
    k_ = it['text'] + ('@' + it['own'] if it['text'] == 'GND' else '')
    if k_ in ROT_START:
        it['start'], it['rot'] = ROT_START[k_]
OUTSIDE_CUT = {'P101', 'TP103', 'J3', 'J4', 'J5', 'J6'}


def check(it, x, y, rot, placed):
    b = text_box(it['text'], x, y, rot, k=K)
    x0, y0, x1, y1 = b.bounds
    if x0 < BOARD[0] + EDGE or y0 < BOARD[1] + EDGE or x1 > BOARD[2] - EDGE or y1 > BOARD[3] - EDGE:
        return None, 'edge'
    if it['own'] not in OUTSIDE_CUT and (x0 < CUT[0] or x1 > CUT[1]):
        return None, 'cut'
    if b.distance(fixed_silk) < SILK_GAP:
        return None, 'silk'
    if placed and b.distance(unary_union(placed)) < SILK_GAP:
        return None, 'text'
    if b.distance(pad_all) < PAD_GAP:
        return None, 'pad'
    if b.distance(bodies) < BODY_GAP:
        return None, 'body'
    near = None
    if it['own']:
        own_d = b.distance(comp_geom[it['own']])
        other = min(b.distance(g) for c, g in comp_geom.items() if c != it['own'])
        if it['kind'] == 'designator' and (own_d > 1.2 or other - own_d < 0.3):
            return None, 'ambiguous'
        if it['kind'] == 'string' and own_d > 1.5:
            return None, 'far'
        near = (own_d, other)
    return b, near


def score(it, x, y, rot):
    return math.dist((x, y), it['start']) + (0 if rot == it['rot'] else 0.3)


def key(it):
    return it['text'] + ('@' + it['own'] if it['text'] == 'GND' else '')


def place_one(it, placed, fixed_pos):
    if key(it) in fixed_pos:
        x, y, rot = fixed_pos[key(it)]
        b, near = check(it, x, y, rot, placed)
        if b is None:
            print('HAND POSITION FAILS', key(it), near)
            return None
        return (0, x, y, rot, b, near)
    if it.get('follow'):
        p = [o for o in placed_info if o['text'] == it['follow']][0]
        it['start'] = (p['x_mm'] + (1.4 if p['rot'] == 90 else 0), p['y_mm'] - (0 if p['rot'] == 90 else 1.4))
        it['rot'] = p['rot']
    sx, sy = it['start']
    best = None
    for rot in (0.0, 90.0):
        n = int(it['win'] / it['step'])
        for dx in [i * it['step'] for i in range(-n, n + 1)]:
            for dy in [i * it['step'] for i in range(-n, n + 1)]:
                x, y = round(sx + dx, 3), round(sy + dy, 3)
                s = score(it, x, y, rot)
                if best and s >= best[0]:
                    continue
                b, near = check(it, x, y, rot, placed)
                if b is None:
                    continue
                s += 0.5 if b.intersects(via_u) else 0          # soft: rather not over a via
                if not best or s < best[0]:
                    best = (s, x, y, rot, b, near)
    return best


placed_info = []


def main(fixed_pos=None, order=None):
    """fixed_pos: {key: (x, y, rot)} hand-chosen positions that are only checked, not searched."""
    fixed_pos = fixed_pos or {}
    its = sorted(items, key=lambda it: (key(it) not in fixed_pos, it['kind'] != 'designator', bool(it.get('follow')), -len(it['text'])))
    placed, out = [], []
    for it in its:
        best = place_one(it, placed, fixed_pos)
        if not best:
            print('NO POSITION for', key(it)); out.append(dict(kind=it['kind'], text=it['text'], own=it['own'], x_mm=None)); continue
        s, x, y, rot, b, near = best
        placed.append(b)
        placed_info.append(dict(text=it['text'], x_mm=x, y_mm=y, rot=rot))
        out.append(dict(kind=it['kind'], text=it['text'], own=it['own'], x_mm=x, y_mm=y, rot=rot,
                        x_mil=round(x / MM + DX, 3), y_mil=round(y / MM + DY, 3),
                        moved_mm=round(math.dist((x, y), it['start']), 3), over_via=b.intersects(via_u),
                        silk_gap=round(b.distance(fixed_silk), 3), pad_gap=round(b.distance(pad_all), 3),
                        own_other=None if not near else [round(v, 3) for v in near]))
        print(f"{key(it):15s} rot{rot:4.0f} ({x:7.3f},{y:7.3f}) moved {math.dist((x, y), it['start']):.2f} mm  "
              f"silk {b.distance(fixed_silk):.2f} pad {b.distance(pad_all):.2f} via {'Y' if b.intersects(via_u) else '-'} own/other {near}")
    gaps = [a.distance(c) for i, a in enumerate(placed) for c in placed[i + 1:]]
    print('min text-text gap among placed', round(min(gaps), 3))
    json.dump(dict(placement=out,
                   hide=[dict(text=t['text'], owner=owner(t), x_mil=t['x'], y_mil=t['y']) for t in hide],
                   delete=[dict(text=t['text'], x_mil=t['x'], y_mil=t['y']) for t in replicas]),
              open(os.path.join(HERE, 'placement.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    return out


if __name__ == '__main__':
    main(json.load(open(os.path.join(HERE, 'hand.json'))) if os.path.exists(os.path.join(HERE, 'hand.json')) else None)

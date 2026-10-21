"""Re-place the free texts DRC still flagged, with wider glyphs:
- GND next to P101 pin 2 (too close to +12V): small local move
- the QPA2609 / MODULE pair (MODULE hit the D101 symbol line): new spot for both lines together
Obstacles come from the CURRENT file (all other Top Overlay texts, overlay lines, pads, component bodies)."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shapely.ops import unary_union
from silk_model import mm, text_box, pads, overlay_geoms, PCB, DX, DY, MM
from pcbdoc_text import read_texts
import olefile

K_T, K_O = 1.00, 0.95          # target texts / other texts (measured ~0.88-0.91 for wide capitals)
SILK_GAP, PAD_GAP, BODY_GAP, EDGE = 0.30, 0.40, 0.10, 0.25
CUT = (6.0, 19.4)
LINE = 1.5                      # line pitch of the two-line name

names = [dict(kv.split('=', 1) for kv in r.strip('|').split('|') if '=' in kv)['SOURCEDESIGNATOR']
         for r in olefile.OleFileIO(PCB).openstream('Components6/Data').read().decode('latin-1').split('\x00') if 'SOURCEDESIGNATOR' in r]
owner = lambda t: names[t['comp']] if t['comp'] < len(names) else None
T = read_texts(PCB)
tops = [t for t in T if t['layer'] == 'TopOverlay' and not t['is_comment']]
def find(text, x, y):
    m = [t for t in tops if t['text'] == text and abs(t['x'] - x) < 0.01 and abs(t['y'] - y) < 0.01]
    assert len(m) == 1, (text, len(m)); return m[0]
gnd = find('GND', 4949.882, 5707.41)
qpa = find('QPA2609', 5400.669, 5392.449)
mod = find('MODULE', 5459.724, 5392.449)
moving = [gnd, qpa, mod]
others = [text_box(owner(t) if t['text'] == '.Designator' else t['text'], *mm(t['x'], t['y']), t['rot'],
                   h=t['h'] * MM, stroke=t['width'] * MM, k=K_O) for t in tops if all(t is not v for v in moving)]
P = pads()
comp = {}
for p in P:
    comp[p['comp']] = comp[p['comp']].union(p['geom']) if p['comp'] in comp else p['geom']
OG = overlay_geoms()
for _, ci, g in OG:
    n = names[ci] if ci < len(names) else None
    if n: comp[n] = comp[n].union(g) if n in comp else g
bodies = unary_union([g.convex_hull for g in comp.values()])
silk = unary_union([g for _, _, g in OG] + others)
pad_all = unary_union([p['geom'] for p in P])


def ok(b, placed, cut=False):
    x0, y0, x1, y1 = b.bounds
    if x0 < EDGE or y0 < EDGE or x1 > 25.4 - EDGE or y1 > 108.5 - EDGE: return False
    if cut and (x0 < CUT[0] or x1 > CUT[1]): return False
    if b.distance(silk) < SILK_GAP or b.distance(pad_all) < PAD_GAP or b.distance(bodies) < BODY_GAP: return False
    return not placed or b.distance(unary_union(placed)) >= SILK_GAP


def report(t, x, y, rot, b):
    print(f"{t['text']:8s} rot {rot:4.0f}  ({x:.3f},{y:.3f}) mm  ->  X={x / MM + DX:.3f}  Y={y / MM + DY:.3f} mil   "
          f"silk {b.distance(silk):.3f}  pad {b.distance(pad_all):.3f}")


placed = []
# 1) GND: smallest move that clears everything, staying next to P101
sx, sy = mm(gnd['x'], gnd['y']); best = None
for i in range(-30, 31):
    for j in range(-30, 31):
        x, y = round(sx + i * 0.02, 3), round(sy + j * 0.02, 3)
        d = math.dist((x, y), (sx, sy))
        if best and d >= best[0]: continue
        b = text_box('GND', x, y, gnd['rot'], k=K_T)
        if ok(b, placed) and b.distance(comp['P101']) <= 1.5:
            best = (d, x, y, b)
d, x, y, b = best; placed.append(b); report(gnd, x, y, gnd['rot'], b)

# 2) the pair: rot 90 -> MODULE one line to the right; rot 0 -> MODULE one line below. Prefer close to the old spot.
s0 = mm(qpa['x'], qpa['y']); best = None
for rot in (90.0, 0.0):
    for i in range(int(6.0 / 0.1), int(19.4 / 0.1) + 1):
        for j in range(int(52.0 / 0.1), int(108.0 / 0.1) + 1):
            x, y = i * 0.1, j * 0.1
            d = math.dist((x, y), s0) + (0 if rot == 90 else 0.5)
            if best and d >= best[0]: continue
            b1 = text_box('QPA2609', x, y, rot, k=K_T)
            if not ok(b1, placed, cut=True): continue
            x2, y2 = (x + LINE, y) if rot == 90 else (x, y - LINE)
            b2 = text_box('MODULE', x2, y2, rot, k=K_T)
            if not ok(b2, placed + [b1], cut=True): continue
            best = (d, x, y, rot, b1, x2, y2, b2)
d, x, y, rot, b1, x2, y2, b2 = best
report(qpa, x, y, rot, b1); report(mod, x2, y2, rot, b2)
print('pair moved', round(math.dist((x, y), s0), 2), 'mm')

"""Obstacle model for the QPA2609 Top Overlay, in board-relative mm (origin = data offset 4755.000 / 1734.969 mil)."""
import sys, os, csv, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shapely.geometry import box, LineString, Point, Polygon
from shapely.affinity import rotate, translate
from shapely.ops import unary_union
from pcbdoc_prims import overlay
from pcbdoc_text import read_texts

DX, DY, MM = 4755.000, 1734.969, 0.0254
PCB = r'E:\Altium_designer\QPA2609\projects\QPA2609_test\PCB1_no3d.PcbDoc'
CHK = r'E:\<项目根>\电路控制\temp\eda_check'
H, STROKE = 1.0, 0.16                 # mm, all new texts


def mm(x, y):
    return ((x - DX) * MM, (y - DY) * MM)


# Altium default stroke font: advance per character as a fraction of the height (calibrated in calib()).
CHAR_W = 0.80


def text_box(s, x, y, rot, h=H, stroke=STROKE, k=None):
    """Outline of a stroke text (anchor = bottom-left of the unrotated text), grown by half the stroke."""
    k = CHAR_W if k is None else k
    w = len(s) * k * h
    b = box(-stroke / 2, -stroke / 2, w + stroke / 2 - 0.0, h + stroke / 2)
    return translate(rotate(b, rot, origin=(0, 0)), x, y)


def pads():
    out = []
    for p in csv.DictReader(open(CHK + r'\pads.csv', encoding='utf-8-sig')):
        x, y = mm(float(p['X']), float(p['Y']))
        sx, sy = float(p['TopXSize']) * MM, float(p['TopYSize']) * MM
        g = Point(x, y).buffer(sx / 2) if p['TopShape'] == '1' else \
            rotate(box(x - sx / 2, y - sy / 2, x + sx / 2, y + sy / 2), float(p['Rotation']), origin=(x, y))
        out.append(dict(comp=p['Component'], name=p['Name'], geom=g, layer=p['Layer']))
    return out


def overlay_geoms(exclude_texts=()):
    """Footprint lines / arcs and every Top Overlay text that will stay (texts given as (text, x, y) mil keys to skip)."""
    tracks, arcs = overlay(PCB)
    g = []
    for x1, y1, x2, y2, w, c in tracks:
        g.append(('track', c, LineString([mm(x1, y1), mm(x2, y2)]).buffer(w * MM / 2)))
    for cx, cy, r, a0, a1, w, c in arcs:
        a1 = a1 if a1 > a0 else a1 + 360
        n = max(8, int((a1 - a0) / 5))
        pts = [mm(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
                  cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]
        g.append(('arc', c, LineString(pts).buffer(w * MM / 2)))
    return g


def calib():
    """Fit CHAR_W from the round-2 DRC: text-vs-track silk clearances Altium reported."""
    import re
    drc = open(r'E:\Altium_designer\QPA2609\projects\QPA2609_test\Project Outputs for QPA2609_test\Design Rule Check - PCB1_no3d.drc',
               encoding='latin-1').read()
    rot = {t['text']: t['rot'] for t in read_texts(PCB) if t['layer'] == 'TopOverlay' and t['h'] > 39}
    pat = re.compile(r'Text "([^"]+)" \(([\d.]+)mm,([\d.]+)mm\) on Top Overlay And Track \(([\d.]+)mm,([\d.]+)mm\)\(([\d.]+)mm,([\d.]+)mm\) on Top Overlay Silk Text to Silk Clearance \[([\d.]+)mm\]')
    rows = pat.findall(drc)
    for k in (0.70, 0.75, 0.80, 0.85, 0.90):
        err = []
        for s, x, y, x1, y1, x2, y2, d in rows:
            if s not in rot:
                continue
            tb = text_box(s, float(x), float(y), rot[s], k=k)
            ln = LineString([(float(x1), float(y1)), (float(x2), float(y2))]).buffer(0.1)   # overlay width ~0.2 mm
            err.append(tb.distance(ln) - float(d))
        print(f'k={k:.2f}  n={len(err)}  mean err {sum(err)/len(err):+.3f}  max |err| {max(map(abs, err)):.3f}')
    k = 0.80
    for s, x, y, x1, y1, x2, y2, d in rows:
        if s in rot:
            tb = text_box(s, float(x), float(y), rot[s], k=k)
            ln = LineString([(float(x1), float(y1)), (float(x2), float(y2))]).buffer(0.1)
            print(f'   {s:6s} rot{rot[s]:4.0f}  model {tb.distance(ln):.3f}  drc {float(d):.3f}')


if __name__ == '__main__':
    calib()

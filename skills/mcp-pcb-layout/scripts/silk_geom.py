"""Silkscreen geometry for planning text positions on an existing board (board-relative mm).

Obstacles come from the real board: Top Overlay lines/arcs and texts read from the PcbDoc (pcbdoc_io), pads from a CSV
exported by eda-agent (obj_query ePadObject: Component,Name,X,Y,TopXSize,TopYSize,TopShape,Rotation,Layer ...),
vias from the PcbDoc, and component bodies = convex hull of each component's pads + its own overlay outline.

Rules used (defaults = what passed AD 23 DRC with Silk-to-Silk 0.254 / Silk-to-Mask 0.254, mask expansion 0.102):
  SILK_GAP 0.30   text box to any overlay line / other text
  PAD_GAP  0.40   text box to pad copper (expansion + rule + margin)
  BODY_GAP 0.10   text box may not sit on a component (it would be covered after assembly)
  EDGE     0.25   text box to board edge
Stroke font: text box = len(text) * k * height (+ half stroke all round). k: average 0.80 measured; wide capitals
(G N D M O U W) ~0.9; use 0.85 to plan and 1.0 for texts made mostly of wide capitals. AD's DRC has the last word.

Typical use (see examples/qpa2609/round3 for a full run):
    ob = Obstacles(pcbdoc, pads_csv, origin_mil=(4755.0, 1734.969), board_mm=(0, 0, 25.4, 108.5), exclude_offsets={...})
    pos = ob.search('GND', start=(4.95, 100.9), rots=(90,), own='P101', placed=[])
"""
import csv, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shapely.geometry import box, LineString, Point
from shapely.affinity import rotate, translate
from shapely.ops import unary_union
import pcbdoc_io as io

MM = 0.0254
RULES = dict(SILK_GAP=0.30, PAD_GAP=0.40, BODY_GAP=0.10, EDGE=0.25)


def text_box(s, x, y, rot, h=1.0, stroke=0.16, k=0.85):
    """Outline of a stroke text; (x, y) = Altium text location = bottom-left of the unrotated text; rot about it."""
    w = len(s) * k * h
    b = box(-stroke / 2, -stroke / 2, w + stroke / 2, h + stroke / 2)
    return translate(rotate(b, rot, origin=(0, 0)), x, y)


class Obstacles:
    def __init__(self, pcbdoc, pads_csv, origin_mil, board_mm, exclude_offsets=(), k_other=0.95, rules=None):
        self.ox, self.oy = origin_mil
        self.board = board_mm
        self.r = dict(RULES, **(rules or {}))
        mm = self.mm
        names = io.component_names(pcbdoc)
        own = lambda c: names[c] if c < len(names) else None
        lines = []
        for t in io.read_tracks(pcbdoc, 'TopOverlay'):
            lines.append((own(t['comp']), LineString([mm(t['x1'], t['y1']), mm(t['x2'], t['y2'])]).buffer(t['width'] * MM / 2)))
        for a in io.read_arcs(pcbdoc, 'TopOverlay'):
            a1 = a['a1'] if a['a1'] > a['a0'] else a['a1'] + 360
            n = max(8, int((a1 - a['a0']) / 5))
            pts = [mm(a['cx'] + a['r'] * math.cos(math.radians(a['a0'] + (a1 - a['a0']) * i / n)),
                      a['cy'] + a['r'] * math.sin(math.radians(a['a0'] + (a1 - a['a0']) * i / n))) for i in range(n + 1)]
            lines.append((own(a['comp']), LineString(pts).buffer(a['width'] * MM / 2)))
        texts = []
        for t in io.read_texts(pcbdoc):
            if t['layer'] != 'TopOverlay' or t['is_comment'] or t['off'] in exclude_offsets:
                continue
            s = t['owner'] if t['text'] == '.Designator' and t['owner'] else t['text']
            texts.append(text_box(s, *mm(t['x'], t['y']), t['rot'], h=t['h'] * MM, stroke=t['width'] * MM, k=k_other))
        self.silk = unary_union([g for _, g in lines] + texts)
        self.pads, comp = [], {}
        for p in csv.DictReader(open(pads_csv, encoding='utf-8-sig')):
            x, y = mm(float(p['X']), float(p['Y']))
            sx, sy = float(p['TopXSize']) * MM, float(p['TopYSize']) * MM
            g = Point(x, y).buffer(sx / 2) if p['TopShape'] == '1' else \
                rotate(box(x - sx / 2, y - sy / 2, x + sx / 2, y + sy / 2), float(p['Rotation']), origin=(x, y))
            self.pads.append(g)
            comp[p['Component']] = comp[p['Component']].union(g) if p['Component'] in comp else g
        for c, g in lines:
            if c:
                comp[c] = comp[c].union(g) if c in comp else g
        self.comp = comp
        self.pad_all = unary_union(self.pads)
        self.bodies = unary_union([g.convex_hull for g in comp.values()])
        self.vias = unary_union([Point(*mm(v['x'], v['y'])).buffer(v['diameter'] * MM / 2) for v in io.read_vias(pcbdoc)])

    def mm(self, x, y):
        return ((x - self.ox) * MM, (y - self.oy) * MM)

    def mil(self, x, y):
        return (x / MM + self.ox, y / MM + self.oy)

    def check(self, b, placed=(), x_range=None, own=None, designator=False):
        """None if the text box b is acceptable, else the reason."""
        r = self.r
        x0, y0, x1, y1 = b.bounds
        bx0, by0, bx1, by1 = self.board
        if x0 < bx0 + r['EDGE'] or y0 < by0 + r['EDGE'] or x1 > bx1 - r['EDGE'] or y1 > by1 - r['EDGE']:
            return 'edge'
        if x_range and (x0 < x_range[0] or x1 > x_range[1]):
            return 'outside allowed x range'
        if b.distance(self.silk) < r['SILK_GAP']:
            return 'silk'
        if placed and b.distance(unary_union(placed)) < r['SILK_GAP']:
            return 'placed text'
        if b.distance(self.pad_all) < r['PAD_GAP']:
            return 'pad'
        if b.distance(self.bodies) < r['BODY_GAP']:
            return 'on a component'
        if own:
            d_own = b.distance(self.comp[own])
            d_other = min(b.distance(g) for c, g in self.comp.items() if c != own)
            if designator and (d_own > 1.2 or d_other - d_own < 0.3):
                return 'ambiguous owner'
            if not designator and d_own > 1.5:
                return 'too far from owner'
        return None

    def search(self, text, start, rots=(0.0, 90.0), own=None, designator=False, placed=(), x_range=None,
               win=4.0, step=0.05, k=0.85, h=1.0, stroke=0.16, via_penalty=0.5, rot_penalty=0.3):
        """Closest acceptable position to `start` (mm). Returns dict or None."""
        best = None
        n = int(win / step)
        for rot in rots:
            for i in range(-n, n + 1):
                for j in range(-n, n + 1):
                    x, y = round(start[0] + i * step, 3), round(start[1] + j * step, 3)
                    s = math.dist((x, y), start) + (rot_penalty if rot != rots[0] else 0)
                    if best and s >= best['score']:
                        continue
                    b = text_box(text, x, y, rot, h, stroke, k)
                    if self.check(b, placed, x_range, own, designator):
                        continue
                    s += via_penalty if b.intersects(self.vias) else 0
                    if not best or s < best['score']:
                        best = dict(score=s, x=x, y=y, rot=rot, box=b, over_via=b.intersects(self.vias),
                                    silk_gap=b.distance(self.silk), pad_gap=b.distance(self.pad_all))
        if best:
            best['x_mil'], best['y_mil'] = (round(v, 3) for v in self.mil(best['x'], best['y']))
        return best

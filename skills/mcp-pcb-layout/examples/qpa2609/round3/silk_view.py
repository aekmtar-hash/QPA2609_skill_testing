"""Draw a window of the Top Overlay model: overlay lines, kept texts, pads (+ PAD_GAP halo), vias, placed texts."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from silk_model import text_box
import silk_place as sp   # re-runs nothing heavy except obstacle build (placement loop is guarded below)

def draw(ax, g, **kw):
    gs = getattr(g, 'geoms', [g])
    for p in gs:
        if p.is_empty: continue
        x, y = p.exterior.xy; ax.fill(x, y, **kw)
        for h in p.interiors:
            x, y = h.xy; ax.fill(x, y, color='white', lw=0)

def view(win, fname, extra=()):
    fig, ax = plt.subplots(figsize=(10, 10 * (win[3] - win[1]) / (win[2] - win[0])))
    for p in sp.P: draw(ax, p['geom'].buffer(sp.PAD_GAP), color='#fdd', lw=0); draw(ax, p['geom'], color='#c33')
    draw(ax, sp.via_u, color='#888')
    draw(ax, sp.fixed_silk, color='#222')
    for it in json.load(open(os.path.join(sp.HERE, 'placement.json'), encoding='utf-8'))['placement']:
        if it.get('x_mm') is not None:
            draw(ax, text_box(it['text'], it['x_mm'], it['y_mm'], it['rot'], k=sp.K), color='#2a6', alpha=.6)
            ax.text(it['x_mm'], it['y_mm'], it['text'], fontsize=7, color='g', clip_on=True)
    for t, x, y, r in extra:
        draw(ax, text_box(t, x, y, r, k=sp.K), color='#36c', alpha=.4); ax.text(x, y, t, fontsize=7, color='b', clip_on=True)
    for c in sp.CUT: ax.axvline(c, color='orange', lw=.8)
    for p in sp.P:
        c = p['geom'].centroid; ax.text(c.x, c.y, f"{p['comp']}-{p['name']}", fontsize=5, ha='center', clip_on=True)
    ax.set_xlim(win[0], win[2]); ax.set_ylim(win[1], win[3]); ax.set_aspect('equal'); ax.grid(lw=.2)
    ax.set_xticks([x * 0.5 for x in range(int(win[0] * 2), int(win[2] * 2) + 1)], minor=True)
    fig.savefig(os.path.join(sp.HERE, fname), dpi=110, bbox_inches='tight'); plt.close(fig)

if __name__ == '__main__':
    view((0, 96, 25.4, 108.5), 'view_top.png')
    view((5, 62, 20, 76), 'view_rv.png')

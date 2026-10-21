"""Top Overlay tracks / arcs straight from the PcbDoc (KiCad ATRACK6 / AARC6 layouts), cross-checked against the subagent's CSVs."""
import olefile, struct, csv, math, sys

TOP_OVERLAY = 33
PCB = r'E:\Altium_designer\QPA2609\projects\QPA2609_test\PCB1_no3d.PcbDoc'
CHK = r'E:\<项目根>\电路控制\temp\eda_check'


def records(data, rtype):
    i = 0
    while i < len(data):
        t = data[i]; n = struct.unpack_from('<I', data, i + 1)[0]
        assert t == rtype, (i, t)
        yield data[i + 5:i + 5 + n]
        i += 5 + n


def overlay(path=PCB):
    o = olefile.OleFileIO(path)
    tracks, arcs = [], []
    for r in records(o.openstream('Tracks6/Data').read(), 4):
        if r[0] == TOP_OVERLAY:
            x1, y1, x2, y2, w = struct.unpack_from('<iiiii', r, 13)
            tracks.append(tuple(v / 1e4 for v in (x1, y1, x2, y2, w)) + (struct.unpack_from('<H', r, 7)[0],))
    for r in records(o.openstream('Arcs6/Data').read(), 1):
        if r[0] == TOP_OVERLAY:
            cx, cy, rad = struct.unpack_from('<iii', r, 13)
            a0, a1 = struct.unpack_from('<dd', r, 25)
            w = struct.unpack_from('<i', r, 41)[0]
            arcs.append((cx / 1e4, cy / 1e4, rad / 1e4, a0, a1, w / 1e4, struct.unpack_from('<H', r, 7)[0]))
    o.close()
    return tracks, arcs


if __name__ == '__main__':
    tracks, arcs = overlay()
    ct = list(csv.DictReader(open(CHK + r'\overlay_tracks.csv', encoding='utf-8-sig')))
    ca = list(csv.DictReader(open(CHK + r'\overlay_arcs.csv', encoding='utf-8-sig')))
    print('tracks parsed', len(tracks), 'csv', len(ct), '| arcs parsed', len(arcs), 'csv', len(ca))
    def has_t(r):
        a = [float(r[k]) for k in ('X1', 'Y1', 'X2', 'Y2')]
        return any((math.dist(a[:2], t[:2]) < 0.05 and math.dist(a[2:], t[2:4]) < 0.05) or
                   (math.dist(a[:2], t[2:4]) < 0.05 and math.dist(a[2:], t[:2]) < 0.05) for t in tracks)
    bad = [r for r in ct if not has_t(r)]
    print('csv tracks not found in file:', len(bad), bad[:3])
    bad = [r for r in ca if not any(math.dist((float(r['XCenter']), float(r['YCenter'])), a[:2]) < 1.01 and abs(float(r['Radius']) - a[2]) < 1.01 for a in arcs)]
    print('csv arcs not found in file:', len(bad), bad[:3])
    print('widths', sorted({round(t[4], 3) for t in tracks}), sorted({round(a[5], 3) for a in arcs}))

"""Per footprint, count every primitive by kind and layer -- run on EVERY downloaded .PcbLib before planning.

Why: in QPA2609 the footprints carried things nobody looked for: keep-out / Top-layer regions 0.05 mm from their own pads
(26 DRC clearance errors), and Top Overlay texts '.Designator' / 'REFDES' / 'RefDes' that print the designator (or the
literal word) even after the designator itself was hidden.

Usage: python -I pcblib_inventory.py "<folder or glob of .PcbLib>" [--texts]
  --texts   also print every text primitive (layer, string) per footprint
Flags worth a look: region@TopLayer, region@KeepOutLayer, any text@TopOverlay."""
import struct, olefile, sys, glob, os, collections

LAYER = {1: 'TopLayer', 32: 'BottomLayer', 33: 'TopOverlay', 34: 'BottomOverlay', 56: 'KeepOutLayer', 74: 'MultiLayer', 35: 'TopPaste', 36: 'BottomPaste', 37: 'TopSolder', 38: 'BottomSolder', 55: 'DrillGuide', 73: 'DrillDrawing'}
LAYER.update({56 + i: f'Mech{i}' for i in range(1, 17)})
KIND = {1: 'arc', 2: 'pad', 3: 'via', 4: 'track', 5: 'text', 6: 'fill', 11: 'region', 12: 'body'}


def inventory(path, want_texts=False):
    ole = olefile.OleFileIO(path)
    for st in ole.listdir():
        if len(st) != 2 or st[1] != 'Data' or st[0] in ('FileVersionInfo', 'Library'):
            continue
        d = ole.openstream(st).read()
        n = struct.unpack_from('<I', d, 0)[0]; p = 4 + n                 # skip footprint name block
        c, texts = collections.Counter(), []
        while p < len(d):
            rt = d[p]; p += 1
            if rt == 2:                                                  # pad: 6 subrecords
                first = None
                for i in range(6):
                    L = struct.unpack_from('<I', d, p)[0]
                    if i == 4: first = d[p + 4:p + 4 + L]
                    p += 4 + L
                c[f"pad@{LAYER.get(first[0], first[0]) if first else '?'}"] += 1
                continue
            if rt not in KIND:
                c[f'?record{rt}'] += 1; break
            for k in range(2 if rt == 5 else 1):
                L = struct.unpack_from('<I', d, p)[0]; b = d[p + 4:p + 4 + L]; p += 4 + L
                if k == 0:
                    c[f'{KIND[rt]}@{LAYER.get(b[0], b[0])}'] += 1
                    lay = LAYER.get(b[0], b[0])
                elif rt == 5:
                    s = b[4:].decode('latin-1', 'replace').strip('\x00') if len(b) > 4 else ''
                    texts.append((lay, s[1:] if s and ord(s[0]) == len(s) - 1 else s))
        flags = [k for k in c if k in ('region@TopLayer', 'region@KeepOutLayer') or k.startswith('text@TopOverlay')]
        print(f"{os.path.basename(path)} :: {st[0]}  {dict(sorted(c.items()))}" + (f"   <-- CHECK {flags}" if flags else ''))
        if want_texts and texts:
            for lay, s in texts:
                print(f'      text {lay}: {s!r}')
    ole.close()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    arg = sys.argv[1]
    files = sorted(glob.glob(os.path.join(arg, '*.PcbLib')) if os.path.isdir(arg) else glob.glob(arg))
    for f in files:
        inventory(f, '--texts' in sys.argv)

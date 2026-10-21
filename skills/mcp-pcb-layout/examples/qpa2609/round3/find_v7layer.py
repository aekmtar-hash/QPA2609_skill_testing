"""Find where else a text record stores its layer: compare first-subrecord bytes of Top Overlay vs Mechanical13 texts (pre-patch backup)."""
import olefile, struct, sys, collections
P = r'E:\Altium_designer\备份\QPA2609_20261020_2045_第三轮改文件前\PCB1_no3d.PcbDoc'
data = olefile.OleFileIO(P).openstream('Texts6/Data').read()
recs = []
i = 0
while i < len(data):
    n = struct.unpack_from('<I', data, i + 1)[0]
    s = data[i + 5:i + 5 + n]
    j = i + 5 + n; m = struct.unpack_from('<I', data, j)[0]
    recs.append(s); i = j + 4 + m
print('first-subrecord lengths', collections.Counter(len(r) for r in recs))
by = collections.defaultdict(list)
for r in recs:
    by[r[0]].append(r)
print({k: len(v) for k, v in by.items()})
a, b = by[33], by[69]
L = min(len(r) for r in recs)
# offsets whose value is constant inside each layer group but differs between the groups
for off in range(1, L):
    va = {r[off] for r in a}; vb = {r[off] for r in b}
    if len(va) == 1 and len(vb) == 1 and va != vb:
        print('byte offset', off, 'TopOverlay', va, 'Mech13', vb)
for off in range(1, L - 3):
    va = {struct.unpack_from('<I', r, off)[0] for r in a}; vb = {struct.unpack_from('<I', r, off)[0] for r in b}
    if len(va) == 1 and len(vb) == 1 and va != vb:
        print('u32 offset', off, 'TopOverlay', hex(va.pop()), 'Mech13', hex(vb.pop()))

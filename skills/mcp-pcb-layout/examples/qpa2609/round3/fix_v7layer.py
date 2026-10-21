"""Text records keep the layer twice: legacy byte @0 and the V7 layer u32 @226 of the first subrecord (AD reads the V7 one).
Make @226 agree with @0 wherever they disagree, using the pairs seen in untouched records. Usage: fix_v7layer.py check | apply"""
import olefile, struct, sys, collections
PCB = r'E:\Altium_designer\QPA2609\projects\QPA2609_test\PCB1_no3d.PcbDoc'
V7 = 226


def records(data):
    i = 0
    while i < len(data):
        n = struct.unpack_from('<I', data, i + 1)[0]
        s = i + 5
        j = s + n; m = struct.unpack_from('<I', data, j)[0]
        yield s, n
        i = j + 4 + m


o = olefile.OleFileIO(PCB, write_mode=(sys.argv[1:] == ['apply']))
data = bytearray(o.openstream('Texts6/Data').read())
pairs = collections.Counter((data[s], struct.unpack_from('<I', data, s + V7)[0]) for s, n in records(data))
print('legacy layer -> V7 layer pairs:', {(a, hex(b)): c for (a, b), c in pairs.items()})
known = {33: 0x01030006, 69: 0x0102000D}
for (a, b), c in pairs.items():
    assert known.get(a) == b or c <= 21, (a, hex(b), c)       # only our patched records may disagree
fix = [s for s, n in records(data) if known[data[s]] != struct.unpack_from('<I', data, s + V7)[0]]
print('records to fix:', len(fix))
if sys.argv[1:] == ['apply']:
    for s in fix:
        struct.pack_into('<I', data, s + V7, known[data[s]])
    o.write_stream('Texts6/Data', bytes(data))
    o.close()
    d2 = olefile.OleFileIO(PCB).openstream('Texts6/Data').read()
    left = [s for s, n in records(d2) if known[d2[s]] != struct.unpack_from('<I', d2, s + V7)[0]]
    print('after apply, still inconsistent:', len(left))

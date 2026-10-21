"""Round 3, offline step: patch PCB1_no3d.PcbDoc (AD must have the project closed).
- the 10 key designators: layer TopOverlay + exact x / y / rotation from placement.json
- the 12 strings (QPA2609 and MODULE already split by the AD step): exact x / y / rotation, height 1.0 / stroke 0.16
- the 13 footprint texts (.Designator / REFDES / RefDes) of the module parts -> Mechanical13
- board region (Layer Stack Region 1) top edge 3758.6225 -> 6007 mil, same as the board shape
Usage: apply_patch.py check | apply"""
import sys, os, json, shutil, olefile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pcbdoc_text import read_texts, patch, read_region

PCB = r'E:\Altium_designer\QPA2609\projects\QPA2609_test\PCB1_no3d.PcbDoc'
HERE = os.path.dirname(os.path.abspath(__file__))
PL = json.load(open(os.path.join(HERE, 'placement.json'), encoding='utf-8'))
REGION_TOP = 6007.0
H, W = 39.37, 6.299

names = [dict(kv.split('=', 1) for kv in r.strip('|').split('|') if '=' in kv)['SOURCEDESIGNATOR']
         for r in olefile.OleFileIO(PCB).openstream('Components6/Data').read().decode('latin-1').split('\x00')
         if 'SOURCEDESIGNATOR' in r]
owner = lambda t: names[t['comp']] if t['comp'] < len(names) else None


def plan():
    T = read_texts(PCB)
    edits, problems = [], []
    free = [t for t in T if t['layer'] == 'TopOverlay' and t['comp'] == 65535]
    for p in PL['placement']:
        if p['kind'] == 'designator':
            m = [t for t in T if t['is_designator'] and owner(t) == p['text'] and t['text'] == p['text']]
        else:
            m = [t for t in free if t['text'] == p['text']]
            if p['text'] == 'GND':
                side = {'P101': lambda t: t['y'] > 5300, 'J5': lambda t: 3000 < t['y'] < 5300, 'J6': lambda t: t['y'] < 3000}[p['own']]
                m = [t for t in m if side(t)]
        if len(m) != 1:
            problems.append(f"{p['text']}@{p['own']}: {len(m)} matches"); continue
        e = dict(layer='TopOverlay', x=p['x_mil'], y=p['y_mil'], rot=p['rot'])
        if p['kind'] == 'string':
            e.update(h=H, width=W)
        edits.append((m[0], e, p))
    for h in PL['hide']:
        m = [t for t in T if t['layer'] == 'TopOverlay' and owner(t) == h['owner'] and t['text'] == h['text']
             and abs(t['x'] - h['x_mil']) < 0.01 and abs(t['y'] - h['y_mil']) < 0.01]
        if len(m) != 1:
            problems.append(f"hide {h['text']}@{h['owner']}: {len(m)} matches"); continue
        edits.append((m[0], dict(layer='Mechanical13'), h))
    claimed = {t['off'] for t, _, _ in edits}
    left = [t['text'] for t in free if t['off'] not in claimed]
    if left:
        problems.append(f'free Top Overlay texts not in the plan (replicas not deleted?): {left}')
    return edits, problems


def verify(edits):
    T = read_texts(PCB)
    by_off = {t['off']: t for t in T}
    bad = 0
    for t0, e, _ in edits:
        t = by_off[t0['off']]
        for k, v in e.items():
            got = t[k]
            ok = got == v if k == 'layer' else abs(got - v) < 0.001
            if not ok:
                bad += 1; print('  VERIFY FAIL', t0['text'], k, got, '!=', v)
    reg = read_region(PCB)
    print('region vertices', reg)
    return bad


if __name__ == '__main__':
    edits, problems = plan()
    print(f'{len(edits)} text edits planned (expect 10 designators + 12 strings + 13 hides = 35)')
    for p in problems:
        print('  PROBLEM', p)
    if sys.argv[1:] == ['apply']:
        if problems or len(edits) != 35:
            sys.exit('not applying')
        bk = os.path.join(r'E:\Altium_designer\备份', 'QPA2609_' + __import__('time').strftime('%Y%m%d_%H%M') + '_第三轮改文件前')
        os.makedirs(bk, exist_ok=True)
        shutil.copy2(PCB, bk)
        print('backup', bk)
        patch(PCB, [(t['off'], e) for t, e, _ in edits], region_top=REGION_TOP)
        print('verify failures:', verify(edits))

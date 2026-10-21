"""Summarise an Altium DRC report (.drc text file in 'Project Outputs for <project>').

The report file is the authority, not the tool's own 'drc_confirmed'. A rule shown with '(Disabled)' in its header
was not checked. Rules absent from the report were not checked either (e.g. Routing Via Style never appears).

Usage:
  python -I drc_report.py <report.drc>                        per-rule violation counts
  python -I drc_report.py <report.drc> --texts "+12V,GND,U101" violations naming any of these Text "..." objects
  python -I drc_report.py <report.drc> --kinds                 violations grouped by the object kinds involved
"""
import re, sys, collections


def parse(path):
    d = open(path, encoding='latin-1').read()
    rules = []
    for header, body in re.findall(r'Processing Rule : (.*?)\r?\n(.*?)Rule Violations :\d+', d, re.S):
        lines = [l.strip() for l in body.splitlines() if 'Violation between' in l]
        rules.append(dict(rule=header.strip(), disabled='(Disabled)' in header, violations=lines))
    t = re.search(r'Time\s*:\s*(\S+)', d)
    return dict(time=t.group(1) if t else None, rules=rules)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    r = parse(sys.argv[1])
    print('report time', r['time'])
    total = 0
    for x in r['rules']:
        n = len(x['violations']); total += n
        print(f"{n:5d}  {'(off) ' if x['disabled'] else ''}{x['rule'][:110]}")
    print('total violations', total)
    if '--texts' in sys.argv:
        names = sys.argv[sys.argv.index('--texts') + 1].split(',')
        hits = [(x['rule'][:40], v) for x in r['rules'] for v in x['violations'] if any(f'Text "{n}"' in v for n in names)]
        print(f'\nviolations naming {names}: {len(hits)}')
        for rule, v in hits:
            print('  ', rule, '|', re.sub(r'^Violation between .*?Constraint: ', '', v)[:200])
    if '--kinds' in sys.argv:
        k = collections.Counter()
        for x in r['rules']:
            for v in x['violations']:
                k[(x['rule'][:30], tuple(sorted(set(re.findall(r'\b(Arc|Track|Pad|Text|Fill|Region|Via|Component)\b', v)))))] += 1
        print()
        for (rule, kinds), n in k.most_common():
            print(f'{n:5d}  {rule}  {kinds}')


if __name__ == '__main__':
    main()

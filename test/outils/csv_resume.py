"""Résumé d'un CSV de session (export ZIP de l'accordeur) : ce que l'appli a
AFFICHÉ, par segment (note + anches), avec médiane, étendue et sauts > 1 ¢.

    python3 test/outils/csv_resume.py session.csv
"""
import csv, sys, statistics as st
from collections import OrderedDict, defaultdict
rows = list(csv.DictReader(open(sys.argv[1], encoding='utf-8-sig'), delimiter=';'))
byt = OrderedDict()
for r in rows: byt.setdefault(float(r['t_s']), []).append(r)
segs, prev = [], None
for t, rs in byt.items():
    base = [r for r in rs if r['harmonique'] == '0']
    sig = (rs[0]['note'], tuple(sorted({r['label'] or r['anche'] for r in base})))
    if sig != prev: segs.append({'t': t, 'sig': sig, 'd': defaultdict(list)}); prev = sig
    for r in base: segs[-1]['d'][r['label'] or r['anche']].append(float(r['ecart_cents']) if r['ecart_cents'] else None)
for s in segs:
    n = max((len(v) for v in s['d'].values()), default=0)
    if n < 10: continue
    out = []
    for lab, a in s['d'].items():
        v = [c for c in a if c is not None]
        if not v: out.append(f"{lab}: —"); continue
        j = sum(1 for p, q in zip(a, a[1:]) if p is not None and q is not None and abs(p - q) > 1)
        q = sorted(v); out.append(f"{lab}: {st.median(v):+.1f} [{q[len(q) // 10]:+.1f}, {q[9 * len(q) // 10]:+.1f}] {len(v)}/{len(a)} sauts {j}")
    print(f"{s['t']:7.1f} {s['sig'][0]:6} " + ' | '.join(out))

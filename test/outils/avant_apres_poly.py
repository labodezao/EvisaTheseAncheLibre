"""Avant / apres une correction du moteur, sur les passages reels.

    python test/outils/avant_apres_poly.py avant.json [apres.json]

Lit deux sorties de compare_poly.py (moteur d'avant, moteur d'apres). Par
passage, reglage et anche affichee : mediane et |max| de l'ecart a la verite
(c) sur les 40 % finaux du palier ; couverture : part de ces images ou toutes
les anches vraies a plus de -20 dB ont une valeur a 1 c ; f : fantomes ; c :
confusions (octave, quinte). En fin de liste, ce qui se degrade de plus de
0,02 c, les anches perdues et la couverture qui baisse de plus de 5 points.
Attention : l'etiquette d'une anche suit la note lue ; si la note change
(une octave trop haut avant), l'etiquette « 16' » ne porte plus la meme anche.
Moteur d'avant : extraire web/ d'un commit dans un dossier, y copier test/,
et y lancer compare_poly.py (cf. LISEZMOI.md)."""
import sys, json
import numpy as np

def stats(L):
    tail = L[int(0.6 * len(L)):]
    par = {}
    fant = conf = 0
    cov = 0
    for l in tail:
        need = [j for j, r in enumerate(l['reeds']) if not r['alias'] and r['db'] > -20]
        got = set()
        for v in l['vals']:
            if v['cls'] == 'fantome': fant += 1
            elif v['cls'] != 'anche': conf += 1
            else:
                par.setdefault(v['lab'], []).append(v['err'])
                if abs(v['err']) < 1: got.add(v['j'])
        cov += all(j in got for j in need)
    out = {k: (float(np.median(np.abs(e))), float(np.max(np.abs(e))), len(e)) for k, e in par.items()}
    return out, cov / max(1, len(tail)), fant, conf, len(tail)

A = json.load(open(sys.argv[1], encoding='utf-8'))
B = json.load(open(sys.argv[2], encoding='utf-8')) if len(sys.argv) > 2 else None
pire = []
for pid in A:
    for mn in A[pid]['modes']:
        if '@' in mn: continue
        a = stats(A[pid]['modes'][mn]) if A[pid]['modes'][mn] else None
        b = stats(B[pid]['modes'][mn]) if B and pid in B and B[pid]['modes'].get(mn) else None
        def txt(s):
            if not s: return 'aucune image'
            ps = ' '.join(f"{k}:{m:.2f}/{x:.2f}" for k, (m, x, n) in sorted(s[0].items()))
            return f"cov {100*s[1]:3.0f}% f{s[2]} c{s[3]} | {ps}"
        line = f"{pid} {mn:9} {txt(a)}"
        if B:
            line += f"\n              -> {txt(b)}"
            if a and b:
                for k, (m, x, n) in a[0].items():
                    if k in b[0]:
                        dm, dx = b[0][k][0] - m, b[0][k][1] - x
                        if dm > 0.02 or dx > 0.02: pire.append(f"{pid} {mn} {k}: med {m:.2f}->{b[0][k][0]:.2f}, max {x:.2f}->{b[0][k][1]:.2f}")
                    else:
                        pire.append(f"{pid} {mn} {k}: disparu")
                if b[1] < a[1] - 0.05: pire.append(f"{pid} {mn}: couverture {100*a[1]:.0f}% -> {100*b[1]:.0f}%")
        print(line)
if B:
    print('\nDegradations (> 0,02 c, anche perdue, couverture -5 %) :')
    print('\n'.join(pire) if pire else 'aucune')

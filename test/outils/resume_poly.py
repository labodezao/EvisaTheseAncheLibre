"""Resume d'une comparaison (compare_poly.py) : par passage et par reglage,
premiere valeur fine, separation (toutes les anches a 1 c dans 80 % des
images suivantes), ecart a la verite sur la fin du palier (40 % des images),
fantomes et confusions (octave, quinte, douzieme).
    python test/outils/resume_poly.py sortie.json [--frise]"""
import sys, json, math
import numpy as np
from verite_poly import cents, midi_de, nom

R = json.load(open(sys.argv[1], encoding='utf-8'))
detail = '--frise' in sys.argv


def lab(F):
    m = midi_de(F); mi = int(round(m))
    return f"{nom(mi)}{100 * (m - mi):+.2f}"


for pid, d in R.items():
    p = d['p']
    print(f"\n=== {pid} {p['desc']} ({p['wav']} {p['t_on']}-{p['t1']} s)")
    for mn, L in d['modes'].items():
        if not L:
            print(f"  [{mn}] aucune image comparable"); continue
        imgs = d['images'][mn]
        t_on = p['t_on']
        # premiere valeur fine (ni rapide ni maintenue)
        t_first = next((im['t'] for im in imgs if im['t'] >= t_on and any(v['f'] is not None and not v['r'] and not v['h'] for v in im['v'])), None)
        # anches principales du palier (fin)
        fin = L[-1]['principal']
        # separation : premier instant apres lequel chaque anche principale a une valeur a 1 c, dans 80 % des images suivantes
        def ok(l, tol=1.0):
            cover = set(v['j'] for v in l['vals'] if v['cls'] == 'anche' and abs(v['err']) < tol)
            need = [j for j, r in enumerate(l['reeds']) if not r['alias'] and r['db'] > -20]
            return all(j in cover for j in need)
        t_sep = None
        for i in range(len(L)):
            rest = L[i:]
            if sum(ok(l) for l in rest) >= 0.8 * len(rest) and ok(L[i]):
                t_sep = L[i]['t']; break
        # erreurs sur le palier (dernieres 40 % des images), par anche vraie
        tail = L[int(0.6 * len(L)):]
        par = {}
        fant = conf = 0; nvals = 0
        for l in tail:
            for v in l['vals']:
                nvals += 1
                if v['cls'] == 'fantome': fant += 1
                elif v['cls'] != 'anche': conf += 1
                else:
                    key = lab(l['reeds'][v['j']]['F'])[:4]
                    par.setdefault(v['lab'], []).append((v['err'], l['reeds'][v['j']]['u'], v['M'], v['h']))
        txt = []
        for k, a in par.items():
            e = np.array([x[0] for x in a])
            txt.append(f"{k}: med {np.median(e):+.2f} c, ety {e.std():.2f}, |max| {np.abs(e).max():.2f} ({len(a)} im, M{sum(x[2] for x in a)} h{sum(x[3] for x in a)})")
        vrai = ' / '.join(f"{lab(r['F'])}{'(alias)' if r['alias'] else ''}[{r['db']:.0f}dB]" for r in fin)
        print(f"  [{mn:14}] vrai: {vrai}")
        print(f"      1re valeur fine {None if t_first is None else round(t_first - t_on, 2)} s ; toutes les anches a 1 c : {None if t_sep is None else round(t_sep - t_on, 2)} s ; "
              f"fin de palier : fantomes {fant}/{nvals}, confusions {conf}/{nvals}")
        for s in txt: print('      ' + s)
        if detail:
            for l in L[::3]:
                vs = '  '.join(f"{v['lab']}={lab(v['f'])}{'M' if v['M'] else ''}{'h' if v['h'] else ''}{'r' if v['r'] else ''}[{v['cls'][0]}{'' if v['err'] is None else f'{v['err']:+.2f}'}]" for v in l['vals'])
                vr = ' '.join(lab(r['F']) for r in l['reeds'] if not r['alias'])
                print(f"        {l['t'] - t_on:5.2f} vrai {vr} | {vs}")

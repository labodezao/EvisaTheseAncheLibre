"""Anche confondue avec l'octave (le 8' d'un 16'+8') sur les passages reels :
estimation du moteur (confondu.js) et sa marge, face a la verite ESPRIT
calculee sur la MEME fenetre que le moteur (comme compare_poly.py).

    python test/outils/confondu_poly.py passages_poly.json dossier_des_wav [P03 P08 ...]

Par image ou une anche est confondue : estimation (fe, ¢), marge, methode,
verite (F de l'anche la plus proche, a 3 ¢), erreur, dans la marge ou non ;
et l'erreur de l'ancienne valeur (la raie commune, fMeas). Resume par passage.
Resultats : docs/POLYPHONIE-ESSAIS.md, § 4.2.
"""
import sys, json
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from compare_poly import lancer, verite_fenetre
from verite_poly import cents


def main():
    passages = json.load(open(sys.argv[1], encoding='utf-8'))
    dossier = sys.argv[2]
    seuls = set(sys.argv[3:])
    for p in passages:
        if seuls and p['id'] not in seuls:
            continue
        ch = f"{dossier}/{p['wav']}"
        imgs = lancer(ch, p['modes']['registre'], p['t_on'] - 0.5, p['t1'])
        lignes, fen = [], set()
        for im in imgs:
            for v in im['v']:
                if not v.get('cf') or v.get('fe') is None:
                    continue
                dur = max(1.0, v['W'] / v['srd']) if v['W'] else 1.0
                b = round(im['t'] / 0.05) * 0.05
                a = max(p['t_on'] + 0.05, round((im['t'] - dur) / 0.05) * 0.05)
                if b - a < 0.6:
                    continue
                lignes.append((im['t'], v, (ch, round(a, 2), round(b, 2))))
                fen.add((ch, round(a, 2), round(b, 2)))
        fen = sorted(fen)
        with ProcessPoolExecutor(12) as ex:
            vs = dict(zip(fen, ex.map(verite_fenetre, fen, chunksize=2)))
        print(f"\n{p['id']} {p['desc']}")
        res = []
        for t, v, cle in lignes:
            reeds = [r for r in vs[cle] if not r['alias']]
            proche = min(reeds, key=lambda r: abs(cents(v['fe'], r['F'])), default=None)
            if proche is None or abs(cents(v['fe'], proche['F'])) > 3:
                print(f"{t:8.2f}  {v['lab']} {v['ce']:+.2f} ±{v['mg']:.2f} {v['me']:9s}  verite absente")
                continue
            e = cents(v['fe'], proche['F'])
            e0 = cents(v['f'], proche['F'])
            res.append((e, v['mg'], e0, v['me']))
            print(f"{t:8.2f}  {v['lab']} {v['ce']:+.2f} ±{v['mg']:.2f} {v['me']:9s}{'' if v['sg'] else ' signe ?'}  "
                  f"verite {cents(proche['F'], v['nom']):+.2f} (u {proche['u']:.2f})  erreur {e:+.2f} "
                  f"{'dans' if abs(e) <= v['mg'] else 'HORS'} marge ; raie commune {e0:+.2f}")
        if res:
            e = np.array([r[0] for r in res]); m = np.array([r[1] for r in res]); e0 = np.array([r[2] for r in res])
            print(f"  {len(res)} images : |erreur| med {np.median(abs(e)):.2f} max {abs(e).max():.2f} ¢, "
                  f"marge med {np.median(m):.2f}, dans la marge {np.mean(abs(e) <= m) * 100:.0f} % ; "
                  f"raie commune |erreur| med {np.median(abs(e0)):.2f} max {abs(e0).max():.2f}")


if __name__ == '__main__':
    main()

"""Compare le moteur (images.mjs) a la verite terrain (verite_poly.py) calculee
sur la MEME fenetre de son que le moteur, image par image.

    python test/outils/compare_poly.py passages_poly.json dossier_des_wav sortie.json [--bruit] [--seul P04]
    python test/outils/resume_poly.py sortie.json [--frise]

Chaque passage : attaque t_on, fin t1, reglages (auto, registre juste,
auto-anches). --bruit : aussi avec un bruit blanc a 20 et 10 dB (images.mjs).
La verite d'une image est calculee sur la fenetre du traqueur de la voix de
base a cette image (W / srd, au moins 1 s), sans le bruit ajoute.
Resultats et lecture : docs/POLYPHONIE-ESSAIS.md.
"""
import sys, json, math, subprocess, os
import numpy as np
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from verite_poly import lire, composantes, anches, cents, midi_de, nom

DEPOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
NODE = 'node'
_cache_wav = {}


def wav(ch):
    if ch not in _cache_wav:
        _cache_wav[ch] = lire(ch)
    return _cache_wav[ch]


def verite_fenetre(args):
    ch, a, b = args
    sr, x = wav(ch)
    seg = x[int(a * sr):int(b * sr)]
    comps = composantes(seg, sr, 2500)
    rs = anches(comps)
    # secteur : 50 Hz et ses sous-multiples
    rs = [r for r in rs if not any(abs(r['F'] - h) < 0.25 for h in (50, 25, 100, 50 / 3, 150))]
    # echelles de poles (derive dans la fenetre) : meme octave, a moins de 1,5 c -> une anche
    rs.sort(key=lambda r: r['F'])
    fus = []
    for r in rs:
        if fus and cents(r['F'], fus[-1]['F']) < 1.5 and not r['alias'] and not fus[-1]['alias']:
            q = fus[-1]
            w1, w2 = q['amp'] ** 2, r['amp'] ** 2
            q['F'] = (w1 * q['F'] + w2 * r['F']) / (w1 + w2)
            q['etale'] = max(q.get('etale', 0), cents(r['F'], q['F0']))
            q['amp'] = max(q['amp'], r['amp']); q['n'] += r['n']; q['score'] += r['score']
        else:
            r = dict(r); r['F0'] = r['F']; fus.append(r)
    smax = max((r['score'] for r in fus), default=1)
    out = []
    for r in fus:
        if r['score'] < smax * 10 ** (-24 / 20) or r['n'] < 3:
            continue
        out.append({'F': r['F'], 'db': 20 * math.log10(r['score'] / smax), 'u': r['u'], 'alias': r['alias'],
                    'etale': r.get('etale', 0.0), 'n': r['n']})
    return out


def lancer(ch, cfg, t0, t1, snr=None):
    cmd = [NODE, f'{DEPOT}/test/outils/images.mjs', ch, json.dumps(cfg), f'{t0}', f'{t1}']
    if snr is not None:
        cmd += [str(snr), '7']
    p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    if p.returncode:
        raise RuntimeError(p.stderr)
    return [json.loads(l) for l in p.stdout.splitlines() if l.strip()]


def classer(f, reeds, tol=3.0):
    """Ce qu'est une valeur du moteur : anche, octave d'une anche, quinte, ou rien."""
    best = None
    for j, r in enumerate(reeds):
        for rap, nomr in ((1, 'anche'), (2, 'octave'), (0.5, 'octave'), (1.5, 'quinte'), (2 / 3, 'quinte'),
                          (3, 'douzieme'), (1 / 3, 'douzieme')):
            d = cents(f, r['F'] * rap)
            if abs(d) < tol and (best is None or (rap == 1 and best[1] != 'anche') or abs(d) < abs(best[2])):
                if best is not None and best[1] == 'anche' and rap != 1:
                    continue
                best = (j, nomr, d)
    return best


def evaluer(p, mode_nom, imgs, verites, t_on):
    """Par image : appariement des valeurs du moteur aux anches vraies."""
    lignes = []
    for im in imgs:
        if im['t'] < t_on + 0.3:
            continue
        key = im.get('_vk')
        reeds = verites.get(key, []) if key else []
        if not reeds:
            continue
        principal = [r for r in reeds if not r['alias']]
        vals = []
        for v in im['v']:
            if v['f'] is None:
                continue
            c = classer(v['f'], reeds)
            vals.append({'lab': v['lab'], 'f': v['f'], 'M': v['M'], 'h': v['h'], 'r': v['r'], 'mp': v['mp'],
                         'cls': c[1] if c else 'fantome', 'j': c[0] if c else None, 'err': c[2] if c else None})
        lignes.append({'t': im['t'], 'm': im['m'], 'reeds': reeds, 'vals': vals, 'principal': principal})
    return lignes


def main():
    passages = json.load(open(sys.argv[1], encoding='utf-8'))
    dossier = sys.argv[2]
    for p in passages:
        p['wav'] = os.path.join(dossier, p['wav'])
    sortie = sys.argv[3]
    bruit = '--bruit' in sys.argv
    seul = sys.argv[sys.argv.index('--seul') + 1] if '--seul' in sys.argv else None
    res = {}
    for p in passages:
        if seul and p['id'] != seul:
            continue
        a0, a1 = p['t_on'] - 0.5, p['t1']
        jobs = []
        for mn, cfg in p['modes'].items():
            jobs.append((mn, cfg, None))
            if bruit:
                jobs += [(mn + '@20dB', cfg, 20), (mn + '@10dB', cfg, 10)]
        with ThreadPoolExecutor(8) as ex:
            imgs = dict(zip([j[0] for j in jobs], ex.map(lambda j: lancer(p['wav'], j[1], a0, a1, j[2]), jobs)))
        # fenetres de verite : celle du traqueur de la voix de base, au moins 1 s
        fen = set()
        for mn, L in imgs.items():
            for im in L:
                if im['t'] < p['t_on'] + 0.3:
                    continue
                v0 = next((v for v in im['v'] if v['W']), None)
                dur = max(1.0, v0['W'] / v0['srd']) if v0 else 1.0
                b = round(im['t'] / 0.05) * 0.05
                a = max(p['t_on'] + 0.05, round((im['t'] - dur) / 0.05) * 0.05)
                if b - a < 0.6:
                    continue
                im['_vk'] = f'{a:.2f}-{b:.2f}'
                fen.add((p['wav'], round(a, 2), round(b, 2)))
        fen = sorted(fen)
        with ProcessPoolExecutor(12) as ex:
            vs = list(ex.map(verite_fenetre, fen, chunksize=2))
        verites = {f'{a:.2f}-{b:.2f}': v for (_, a, b), v in zip(fen, vs)}
        res[p['id']] = {'p': p, 'modes': {mn: evaluer(p, mn, L, verites, p['t_on']) for mn, L in imgs.items()},
                        'images': imgs}
        print(p['id'], 'fait', len(fen), 'fenetres', flush=True)
    json.dump(res, open(sortie, 'w', encoding='utf-8'), ensure_ascii=False)


if __name__ == '__main__':
    main()

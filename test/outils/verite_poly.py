"""Verite terrain polyphonique, hors moteur.

    python verite_poly.py son.wav t0 t1 [--fmax 3000] [--json]

1. Spectre long du palier (Hann, zero-padding) : raies a moins de 50 dB de la plus forte.
2. Chaque amas de raies (a moins de 4 Hz l'une de l'autre) : bande de base
   (heterodynage, passe-bas Butterworth aller-retour, decimation), puis ESPRIT
   (sous-espaces, ordre choisi par l'ecart des valeurs singulieres, au plus 4).
3. Une anche est periodique : ses partiels k donnent la MEME hauteur f/k.
   On regroupe les composantes dont f/k concordent a TOL cent pres, avec au
   moins 2 partiels distincts et des rangs k premiers entre eux (sinon c'est
   un sous-multiple d'une autre anche).
4. Hauteur de l'anche : moyenne de f/k ponderee par (A k)^2 ; incertitude :
   ecart-type pondere entre partiels / sqrt(n-1) ; derive : meme mesure sur
   chaque moitie du palier (une anche bouge vraiment avec le soufflet).
Ref : Roy et Kailath (1989), ESPRIT, IEEE Trans. ASSP 37(7), doi:10.1109/29.32276.
"""
import sys, json, math
import numpy as np, scipy.io.wavfile as wv
from scipy.signal import find_peaks, butter, sosfiltfilt
from math import gcd
from functools import reduce


def lire(ch):
    sr, x = wv.read(ch)
    x = x.astype(float) / (32768 if x.dtype == np.int16 else 1)
    if x.ndim > 1:
        x = x.mean(1)
    return sr, x


def esprit(z, pmax=4, rel=3e-3):
    N = len(z); L = N // 2
    H = np.array([z[i:i + L] for i in range(N - L + 1)])
    U, s, _ = np.linalg.svd(H, full_matrices=False)
    floor = np.median(s[pmax + 2:]) if len(s) > pmax + 4 else 0
    p = int(max(1, min(pmax, np.sum((s > rel * s[0]) & (s > 4 * floor)))))
    lam = np.linalg.eigvals(np.linalg.pinv(U[:-1, :p]) @ U[1:, :p])
    V = np.vander(lam, N, increasing=True).T
    a = np.linalg.lstsq(V, z, rcond=None)[0]
    return lam, a


def bande(x, sr, fc, half):
    t = np.arange(len(x)) / sr
    z = x * np.exp(-2j * np.pi * fc * t)
    sos = butter(6, half / (sr / 2), output='sos')
    zf = sosfiltfilt(sos, z.real) + 1j * sosfiltfilt(sos, z.imag)
    D = max(1, int(sr / (4 * half)))
    return zf[::D], sr / D


def composantes(x, sr, fmax=3000, dbmin=-50):
    N = len(x); NF = 1 << int(np.ceil(np.log2(N * 8)))
    S = np.abs(np.fft.rfft(x * np.hanning(N), NF)); f = np.fft.rfftfreq(NF, 1 / sr)
    df = f[1] - f[0]
    sel = (f > 25) & (f < fmax)
    Sm, fm = S[sel], f[sel]
    pk, _ = find_peaks(Sm, height=Sm.max() * 10 ** (dbmin / 20), distance=max(1, int(0.3 / df)))
    keep = []
    for p in pk:
        a, b = max(0, p - int(15 / df)), min(len(Sm), p + int(15 / df))
        if Sm[p] > 4 * np.median(Sm[a:b]):
            keep.append(p)
    fr = fm[keep]
    amas = []
    for fq in fr:
        if amas and fq - amas[-1][-1] < 4:
            amas[-1].append(fq)
        else:
            amas.append([fq])
    out = []
    for am in amas:
        fc = 0.5 * (am[0] + am[-1]); half = max(5.0, 0.5 * (am[-1] - am[0]) + 4)
        zb, srd = bande(x, sr, fc, half)
        cut = int(0.15 * srd)
        zb = zb[cut:len(zb) - cut]
        if len(zb) < 24:
            continue
        lam, a = esprit(zb)
        for l, aa in zip(lam, a):
            fr_ = fc + np.angle(l) * srd / (2 * np.pi)
            damp = -np.log(abs(l)) * srd
            if abs(fr_ - fc) > half:
                continue
            out.append({'f': float(fr_), 'amp': float(abs(aa)), 'damp': float(damp)})
    if not out:
        return out
    amax = max(c['amp'] for c in out)
    return [c for c in out if c['amp'] > amax * 10 ** (-45 / 20) and abs(c['damp']) < 1.5]


def cents(f, ref):
    return 1200 * math.log2(f / ref)


def midi_de(f):
    return 69 + 12 * math.log2(f / 440)


NOMS = ['Do', 'Do#', 'Ré', 'Ré#', 'Mi', 'Fa', 'Fa#', 'Sol', 'Sol#', 'La', 'La#', 'Si']


def nom(m):
    return f"{NOMS[m % 12]}{m // 12 - 1}"


def anches(comps, TOL=0.35, fmin=18, EXPL=0.6, dbmin=-30):
    """Extraction gloutonne : a chaque tour, l'anche qui explique le plus
    d'amplitude parmi les composantes ENCORE INEXPLIQUEES ; une composante est
    expliquee par une anche F si elle tombe a EXPL cent pres d'un multiple
    entier de F (partiel de cette anche, ou pole dedouble par la derive)."""
    expl = [False] * len(comps)
    res = []
    amax = max((c['amp'] for c in comps), default=1)
    while True:
        cand = []
        for i, c in enumerate(comps):
            if expl[i]:
                continue
            for k in range(1, 40):
                F = c['f'] / k
                if F < fmin:
                    break
                cand.append((F, k, i))
        if not cand:
            break
        cand.sort()
        best = None
        j0 = 0
        for j in range(len(cand)):
            while cents(cand[j][0], cand[j0][0]) > TOL:
                j0 += 1
            g = cand[j0:j + 1]
            parK = {}
            for F, k, i in g:
                if k not in parK or comps[i]['amp'] > comps[parK[k][2]]['amp']:
                    parK[k] = (F, k, i)
            ids = set(i for _, _, i in parK.values())
            if len(ids) < len(parK):
                continue
            ks = sorted(parK)
            if len(ks) < 2 or reduce(gcd, ks) != 1 or min(ks) > 3:
                continue
            if not (len(ks) >= 3 or 1 in ks):
                continue
            score = sum(comps[i]['amp'] for _, _, i in parK.values())
            if best is None or score > best[0]:
                best = (score, list(parK.values()))
        if best is None or best[0] < amax * 10 ** (dbmin / 20):
            break
        score, g2 = best
        # presque tout le poids sur les k pairs : c'est l'anche a l'octave au-dessus
        # (ses partiels m sont les k = 2m), une raie impaire isolee n'y change rien
        wo = sum(comps[i]['amp'] for _, k, i in g2 if k % 2)
        if wo < 0.15 * score:
            g2 = [(F * 2, k // 2, i) for F, k, i in g2 if k % 2 == 0]
        w = np.array([(comps[i]['amp'] * k) ** 2 for _, k, i in g2]); Fs = np.array([F for F, _, _ in g2])
        Fm = float((w * Fs).sum() / w.sum())
        dc = np.array([cents(F, Fm) for F in Fs])
        sd = float(np.sqrt((w * dc ** 2).sum() / w.sum()))
        n = len(g2)
        # composantes expliquees par cette anche
        for i, c in enumerate(comps):
            k = round(c['f'] / Fm)
            if k >= 1 and abs(cents(c['f'], k * Fm)) < EXPL:
                expl[i] = True
        # anche « alias » : multiple entier (octave, douzieme) d'une anche plus forte, a 1 cent pres
        alias = None
        for r in res:
            p = Fm / r['F']
            if p > 1.5 and abs(cents(Fm, round(p) * r['F'])) < 1.0:
                alias = f"x{round(p)} de {r['F']:.3f} Hz"
        res.append({'F': Fm, 'n': n, 'ks': sorted(k for _, k, _ in g2), 'u': sd / math.sqrt(max(1, n - 1)),
                    'sd': sd, 'amp': max(comps[i]['amp'] for _, _, i in g2), 'score': score, 'alias': alias})
    return sorted(res, key=lambda r: r['F'])


def analyse(x, sr, fmax=3000):
    comps = composantes(x, sr, fmax)
    return comps, anches(comps)


def verite(x, sr, t0, t1, fmax=3000):
    seg = x[int(t0 * sr):int(t1 * sr)]
    comps, rs = analyse(seg, sr, fmax)
    h = len(seg) // 2
    _, r1 = analyse(seg[:h], sr, fmax)
    _, r2 = analyse(seg[h:], sr, fmax)
    out = []
    for r in rs:
        m = midi_de(r['F']); mi = int(round(m))

        def proche(rr):
            c = [q for q in rr if abs(cents(q['F'], r['F'])) < 3]
            return c[0]['F'] if c else None
        p1, p2 = proche(r1), proche(r2)
        der = cents(p2, p1) if p1 and p2 else None
        out.append({'note': nom(mi), 'midi': mi, 'F': round(r['F'], 5), 'cents': round(100 * (m - mi), 3),
                    'u_cents': round(r['u'], 3), 'n_partiels': r['n'], 'ks': r['ks'][:14],
                    'niveau_db': round(20 * math.log10(r['amp'] + 1e-12), 1),
                    'derive_moities_cents': None if der is None else round(der, 3), 'alias': r['alias']})
    return comps, out


if __name__ == '__main__':
    args = sys.argv[1:]
    fmax = 3000
    if '--fmax' in args:
        i = args.index('--fmax'); fmax = float(args[i + 1]); del args[i:i + 2]
    js = '--json' in args
    args = [a for a in args if a != '--json']
    ch, t0, t1 = args[0], float(args[1]), float(args[2])
    sr, x = lire(ch)
    comps, out = verite(x, sr, t0, t1, fmax)
    if js:
        print(json.dumps(out))
    else:
        print(f"{ch} {t0}-{t1} s : {len(comps)} composantes")
        for o in out:
            print(f"  {o['note']:5} {o['F']:10.4f} Hz {o['cents']:+8.3f} c +-{o['u_cents']:.3f}  n={o['n_partiels']:2d} "
                  f"k={o['ks']}  {o['niveau_db']:6.1f} dB  derive {o['derive_moities_cents']} {o['alias'] or ''}")

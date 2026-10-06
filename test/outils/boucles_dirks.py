"""Boucles d'ecoute pour comparer l'accordeur a un autre accordeur sur le MEME signal.

    python boucles_dirks.py passages_poly.json <dossier des WAV> <dossier de sortie> P15 P16 ... [--crete 0.2]

Pour chaque passage : la partie stable du palier (les 60 % finaux de t_on..t1), repetee
en boucle avec un fondu enchaine a puissance constante de 80 ms, 28 s de son entre
1,5 s de silence avant et 1 s apres. Crete normalisee (0,2 par defaut : Dirk's dit
« signal trop fort » a 0,5). Ecrit boucle-<id>.wav et segments.json (a, b du segment,
pour la verite : verite_poly.py <wav> a b). Le meme fichier est joue a l'autre accordeur
(joue_cable.ps1) et lu par l'accordeur (images.mjs).

Limite : le fondu coupe la phase a chaque tour (1,5 a 3 s) ; la valeur lue est une
moyenne sur la boucle, et la dispersion image par image monte (jusqu'a quelques cents
sur une quinte). C'est le meme signal pour les deux accordeurs : l'ecart entre eux reste
juste, pas leur dispersion absolue.
"""
import os, json, sys
import numpy as np, scipy.io.wavfile as wv

args = [a for a in sys.argv[1:]]
crete = 0.2
if '--crete' in args:
    k = args.index('--crete'); crete = float(args[k + 1]); del args[k:k + 2]
pj, dw, out, *ids = args
P = {p['id']: p for p in json.load(open(pj, encoding='utf-8'))}
os.makedirs(out, exist_ok=True)
seg = {}
for i in ids:
    p = P[i]
    sr, x = wv.read(os.path.join(dw, p['wav']))
    x = x.astype(float) / 32768
    if x.ndim > 1:
        x = x.mean(1)
    a = p['t_on'] + 0.4 * (p['t1'] - p['t_on']); b = p['t1']
    s = x[int(a * sr):int(b * sr)]
    nf = int(0.08 * sr)
    w = np.sin(np.linspace(0, np.pi / 2, nf)) ** 2
    y = s.copy()
    while len(y) < int(28 * sr):
        y = np.concatenate([y[:-nf], y[-nf:] * np.sqrt(1 - w) + s[:nf] * np.sqrt(w), s[nf:]])
    y = y[:int(28 * sr)]
    fo = int(0.05 * sr); y[:fo] *= np.linspace(0, 1, fo); y[-fo:] *= np.linspace(1, 0, fo)
    y = y / np.max(np.abs(y)) * crete
    z = np.concatenate([np.zeros(int(1.5 * sr)), y, np.zeros(sr)])
    wv.write(os.path.join(out, f'boucle-{i}.wav'), sr, (z * 32767).astype(np.int16))
    seg[i] = {'a': round(a, 3), 'b': round(b, 3), 'sr': sr, 'wav': p['wav']}
    print(i, seg[i])
json.dump(seg, open(os.path.join(out, 'segments.json'), 'w'), indent=1)

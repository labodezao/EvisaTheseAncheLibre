"""Vérité terrain : raies d'une bande de fréquences au cours du temps.

    python3 test/outils/bande.py session.wav t0 t1 f_bas f_haut [fenetre_s=0.5] [pas_s=0.5]

Pour chaque fenêtre : niveau (dB) et raies à moins de 25 dB de la plus forte
(fréquence en Hz, niveau relatif). À comparer à ce qu'affiche le moteur
(rejoue.mjs --images) : une valeur de la courbe qui ne correspond à aucune
raie est un artefact ; une valeur qui suit une raie qui bouge est la vraie
hauteur (le soufflet, l'attaque, le tiré/poussé font vraiment bouger l'anche).
Résolution ≈ 1/fenêtre : deux anches à moins de 2 Hz ne se séparent qu'en
fenêtre ≥ 0,7 s (sinon utiliser esprit.py).
"""
import sys, wave, numpy as np
from scipy.signal import find_peaks
w = wave.open(sys.argv[1]); sr = w.getframerate()
x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
if w.getnchannels() > 1: x = x[::w.getnchannels()]
t0, t1, flo, fhi = map(float, sys.argv[2:6])
win = float(sys.argv[6]) if len(sys.argv) > 6 else 0.5
hop = float(sys.argv[7]) if len(sys.argv) > 7 else 0.5
N = int(win * sr)
for t in np.arange(t0, t1, hop):
    s = x[int(t * sr):int(t * sr) + N]
    if len(s) < N // 2: break
    S = np.abs(np.fft.rfft(s * np.hanning(len(s)), 1 << 18)); fr = np.fft.rfftfreq(1 << 18, 1 / sr)
    idx = np.where((fr > flo) & (fr < fhi))[0]; B = S[idx]
    pk, _ = find_peaks(B, height=B.max() * 10 ** (-25 / 20))
    top = sorted(sorted(pk, key=lambda i: -B[i])[:4])
    print(f"{t:8.2f} {20 * np.log10(B.max() + 1e-12):6.1f} dB  " + '  '.join(f"{fr[idx[i]]:8.2f} ({20 * np.log10(B[i] / B.max()):+3.0f})" for i in top))

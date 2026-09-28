"""Analyse haute résolution (ESPRIT) des partiels d'une note : sépare deux ou
trois anches bien en dessous de la limite de Fourier (musette, trémolo).

    python3 test/outils/esprit.py note.wav [f0_Hz] [t0 t1]

Pour les partiels 1 à 3 : les composantes (Hz, cents par rapport à la note
tempérée la plus proche, niveau, amortissement). Une vraie anche donne la
MÊME hauteur en cents sur tous ses partiels ; un reste de partiel voisin, non.
"""
import sys, wave, numpy as np
from scipy.signal import firwin, lfilter
NOMS = ['Do', 'Do♯', 'Ré', 'Ré♯', 'Mi', 'Fa', 'Fa♯', 'Sol', 'Sol♯', 'La', 'La♯', 'Si']
w = wave.open(sys.argv[1]); sr = w.getframerate()
x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
if w.getnchannels() > 1: x = x[::w.getnchannels()]
if len(sys.argv) > 4: x = x[int(float(sys.argv[3]) * sr):int(float(sys.argv[4]) * sr)]
env = np.convolve(x ** 2, np.ones(441) / 441, 'same'); db = 10 * np.log10(env + 1e-12)
idx = np.where(db > db.max() - 15)[0]; seg = x[idx[0] + int(0.08 * sr):idx[-1] - int(0.02 * sr)]
if len(sys.argv) > 2 and float(sys.argv[2]) > 0: f0 = float(sys.argv[2])
else:
    ac = np.correlate(seg[:8192], seg[:8192], 'full')[8191:]; lo, hi = int(sr / 2000), int(sr / 60)
    f0 = sr / (lo + np.argmax(ac[lo:hi]))
def esprit(z, p):
    N = len(z); L = N // 2; H = np.array([z[i:i + L] for i in range(N - L + 1)])
    U, s, _ = np.linalg.svd(H, full_matrices=False)
    lam = np.linalg.eigvals(np.linalg.pinv(U[:-1, :p]) @ U[1:, :p])
    a = np.linalg.lstsq(np.vander(lam, N, increasing=True).T, z, rcond=None)[0]
    return lam, a
print(f"durée analysée {len(seg) / sr:.2f} s, f0 ≈ {f0:.2f} Hz")
for k in (1, 2, 3):
    fc = k * f0; t = np.arange(len(seg)) / sr; zb = seg * np.exp(-2j * np.pi * fc * t)
    dec = max(1, int(sr / (8 * fc * 0.06 + 40))); h = firwin(257, 0.8 / dec)
    zf = lfilter(h, 1, zb)[256:][::dec][:1500]; srd = sr / dec
    lam, a = esprit(zf, 3); fr = fc + np.angle(lam) * srd / (2 * np.pi)
    desc = []
    for i in np.argsort(-np.abs(a)):
        m = 69 + 12 * np.log2(fr[i] / k / 440); r = int(round(m))
        desc.append(f"{fr[i]:9.3f} Hz ({NOMS[r % 12]}{r // 12 - 1} {100 * (m - r):+5.1f} ¢, {20 * np.log10(abs(a[i]) + 1e-12):5.1f} dB, amort. {np.log(abs(lam[i])) * srd:+.2f}/s)")
    print(f"  H{k} : " + ' | '.join(desc))

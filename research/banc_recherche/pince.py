"""Le son d'une languette pincée : fréquence propre et amortissement.

Le geste : on pince le bout de la languette (anche sur sa plaque, sans souffle),
le téléphone enregistre à 10-20 cm. Trois à cinq pincements, une seconde d'écart.

Ce que fait l'outil, en mots
----------------------------
1. Il lit le fichier : wav directement ; m4a, mp3, ogg... par ffmpeg (déjà sur le PC).
2. Il trouve chaque pincement (le son monte d'un coup au-dessus du silence).
3. Pour chaque pincement : la fréquence du pic (spectre), puis un filtre étroit autour
   de ce pic, pour ne garder que le mode 1 (pas ses harmoniques, pas le bruit).
4. L'enveloppe du son filtré décroît comme exp(-alpha t) : la pente de son logarithme
   donne alpha (la méthode de `ringdown.estimate`, déjà dans le dépôt, avec son
   `analytic_envelope`, appliquée au son filtré).
   L'enveloppe est prise sur tout le son filtré (pas sur un morceau, pour éviter les
   effets de bord de la transformée de Hilbert), puis ajustée entre la fin de la montée
   du filtre et 35 dB sous le pic (ou le bruit). La fréquence fine vient de la pente de
   la phase (plus juste que le pic du spectre).
5. Il rend f (Hz), zeta = alpha / (2 pi f), Q = 1 / (2 zeta), et l'écart entre pincements.

Pièges, honnêtement
-------------------
- Un téléphone corrige le son (gain automatique, réduction de bruit). Le gain
  automatique peut FAUSSER l'amortissement (il remonte un son qui s'éteint). La
  fréquence, elle, n'est pas touchée. Contrôle : deux pincements, un faible et un fort,
  doivent donner le même zeta. S'ils diffèrent de plus de 20 %, se méfier du téléphone
  (mode « dictaphone » ou « son brut », ou le micro du banc sur la carte son).
- L'amortissement mesuré est celui de la languette DANS l'air et SUR sa plaque, sans
  souffle : matériau + air + encastrement. Ce n'est pas l'amortissement en jeu.
- La fréquence pincée est la fréquence propre amortie ; l'écart avec la fréquence
  propre vaut f.(1 - sqrt(1 - zeta^2)), soit moins de 0,001 cent ici : négligeable.
"""
from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile
import wave
from dataclasses import dataclass, field

import numpy as np

from .coupled_reeds import dominant_frequency
from .ringdown import analytic_envelope


@dataclass
class Pincement:
    t_debut_s: float
    f_hz: float
    zeta: float
    q: float
    duree_fit_s: float
    snr_db: float


@dataclass
class ResultatPince:
    fichier: str
    f_hz: float                  # médiane des pincements
    f_ecart_hz: float            # écart-type entre pincements
    zeta: float
    zeta_ecart: float
    q: float
    pincements: list = field(default_factory=list)
    alerte: str = ""

    def resume(self):
        return (f"{os.path.basename(self.fichier)} : f = {self.f_hz:.2f} Hz (± {self.f_ecart_hz:.2f}), "
                f"zeta = {self.zeta:.2e} (± {self.zeta_ecart:.1e}), Q = {self.q:.0f}, "
                f"{len(self.pincements)} pincement(s){'. ' + self.alerte if self.alerte else ''}")


# --- Lecture ---------------------------------------------------------------------------------
def _ffmpeg():
    return os.environ.get("FFMPEG") or shutil.which("ffmpeg") or r"C:\ProgramData\chocolatey\bin\ffmpeg.exe"


def _lire_wav(chemin):
    """wav PCM 16/24/32 bits (module standard `wave`), sinon scipy (wav flottant)."""
    try:
        with wave.open(chemin, "rb") as w:
            n, fs, k, ch = w.getnframes(), w.getframerate(), w.getsampwidth(), w.getnchannels()
            brut = w.readframes(n)
        if k == 3:
            b = np.frombuffer(brut, np.uint8).reshape(-1, 3)
            x = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16))
            x = np.where(x >= 1 << 23, x - (1 << 24), x) / float(1 << 23)
        else:
            dt = {1: np.uint8, 2: np.int16, 4: np.int32}[k]
            x = np.frombuffer(brut, dt).astype(float)
            x = (x - 128) / 128 if k == 1 else x / float(np.iinfo(dt).max)
        x = x.reshape(-1, ch).mean(axis=1)
        return x, float(fs)
    except wave.Error:
        from scipy.io import wavfile
        fs, x = wavfile.read(chemin)
        x = np.asarray(x, float)
        if x.ndim > 1:
            x = x.mean(axis=1)
        return x, float(fs)


def lire_audio(chemin):
    """(signal mono en float, fréquence d'échantillonnage). m4a & co. passent par ffmpeg."""
    if chemin.lower().endswith(".wav"):
        return _lire_wav(chemin)
    exe = _ffmpeg()
    if not os.path.exists(exe) and not shutil.which(exe):
        raise RuntimeError("ffmpeg introuvable : convertir le fichier en wav, ou définir FFMPEG")
    with tempfile.TemporaryDirectory() as d:
        sortie = os.path.join(d, "son.wav")
        r = subprocess.run([exe, "-y", "-loglevel", "error", "-i", chemin, "-ac", "1", "-c:a", "pcm_s16le",
                            sortie], capture_output=True, text=True, errors="replace")
        if r.returncode != 0:
            raise RuntimeError(f"ffmpeg n'a pas pu lire {chemin} : {r.stderr.strip()[:300]}")
        return _lire_wav(sortie)


# --- Analyse ---------------------------------------------------------------------------------
def trouver_pincements(x, fs, ecart_min_s=0.3, saut_db=10.0, marge_db=15.0):
    """Indices des débuts de pincement : le niveau (enveloppe de 5 ms) monte de plus de
    `saut_db` en 20 ms, à plus de `marge_db` au-dessus du fond. Un nouveau pincement est
    vu même si le précédent sonne encore (une languette grave sonne plusieurs secondes)."""
    x = np.asarray(x, float) - np.mean(x)
    n = max(1, int(0.005 * fs))
    env = np.sqrt(np.convolve(x ** 2, np.ones(n) / n, mode="same")) + 1e-12
    db = 20 * np.log10(env)
    fond = float(np.percentile(db, 10))
    k = max(1, int(0.02 * fs))
    saut = np.full(db.shape, -np.inf)
    saut[k:] = db[k:] - db[:-k]
    cand = np.nonzero((saut > saut_db) & (db > fond + marge_db))[0]
    debuts = []
    for i in cand:
        if not debuts or i - debuts[-1] > ecart_min_s * fs:
            debuts.append(int(max(0, i - k)))
    return debuts, fond


def filtre_bande(x, fs, f0, demi_largeur):
    """Filtre passe-bande à phase nulle (FFT, gaussien), centré sur f0."""
    n = len(x)
    N = 1 << int(np.ceil(np.log2(n)))
    X = np.fft.rfft(x, N)
    f = np.fft.rfftfreq(N, 1 / fs)
    X *= np.exp(-0.5 * ((f - f0) / demi_largeur) ** 2)
    return np.fft.irfft(X, N)[:n]


def analyser_pincement(seg, fs, f_attendue=None, plage=0.3, fond_db=None):
    """Un pincement (le signal depuis son début) -> `Pincement`, ou None si trop faible."""
    seg = np.asarray(seg, float) - np.mean(seg)
    debut = int(0.01 * fs)                                     # l'impact du doigt
    tete = seg[debut:debut + int(min(0.5, len(seg) / fs) * fs)]
    if len(tete) < 256:
        return None
    if f_attendue:
        # pic cherché autour de la fréquence attendue (± plage)
        N = 1 << int(np.ceil(np.log2(len(tete))) + 3)
        S = np.abs(np.fft.rfft(tete * np.hanning(len(tete)), N))
        fr = np.fft.rfftfreq(N, 1 / fs)
        m = (fr > f_attendue * (1 - plage)) & (fr < f_attendue * (1 + plage))
        f0 = float(fr[m][np.argmax(S[m])])
    else:
        f0 = dominant_frequency(tete, fs)
    bw = max(3.0, 0.04 * f0)
    y = filtre_bande(seg, fs, f0, bw)
    env = analytic_envelope(y)
    pic = int(np.argmax(env[: int(0.2 * fs)]))
    e_db = 20 * np.log10(env / env[pic] + 1e-12)
    # fin de l'ajustement : 35 dB sous le pic, ou le fond (bruit filtré + 6 dB)
    bruit = 20 * np.log10(np.median(env[-int(0.05 * fs):]) / env[pic] + 1e-12) if len(env) > 0.1 * fs else -80
    seuil = max(-35.0, bruit + 6.0)
    a = pic + int(max(0.02, 3.0 / bw) * fs)                    # le filtre a fini de monter
    sous = np.nonzero(e_db[a:] < seuil)[0]
    b = a + (int(sous[0]) if sous.size else len(e_db) - a)
    if b - a < int(0.02 * fs) or b - a < 4 * fs / f0:
        return None
    t = np.arange(a, b) / fs
    pente, _ = np.polyfit(t, np.log(env[a:b] + 1e-30), 1)
    alpha = -float(pente)
    # fréquence fine : pente de la phase du signal analytique
    ph = np.unwrap(np.angle(_analytique(y)[a:b]))
    f_fin = float(np.polyfit(t, ph, 1)[0] / (2 * np.pi))
    zeta = alpha / (2 * np.pi * f_fin)
    return Pincement(t_debut_s=0.0, f_hz=f_fin, zeta=zeta, q=1 / (2 * zeta) if zeta > 0 else float("inf"),
                     duree_fit_s=(b - a) / fs, snr_db=-bruit)


def _analytique(x):
    x = np.asarray(x, float)
    n = x.size
    X = np.fft.fft(x)
    h = np.zeros(n)
    h[0] = 1
    if n % 2 == 0:
        h[n // 2] = 1
        h[1:n // 2] = 2
    else:
        h[1:(n + 1) // 2] = 2
    return np.fft.ifft(X * h)


def analyser(x, fs, f_attendue=None, fichier=""):
    """Tous les pincements d'un enregistrement -> `ResultatPince`."""
    debuts, fond = trouver_pincements(x, fs)
    pins = []
    bornes = debuts + [len(x)]
    for i, d in enumerate(debuts):
        fin = min(bornes[i + 1], d + int(4.0 * fs))
        p = analyser_pincement(x[d:fin], fs, f_attendue)
        if p is not None:
            p.t_debut_s = d / fs
            pins.append(p)
    if not pins:
        raise ValueError("aucun pincement exploitable (son trop faible, ou trop court)")
    f = np.array([p.f_hz for p in pins]); z = np.array([p.zeta for p in pins])
    alerte = ""
    if len(pins) >= 2 and (z.max() - z.min()) / np.median(z) > 0.2:
        alerte = ("les amortissements des pincements diffèrent de plus de 20 % : gain automatique "
                  "du téléphone ? (la fréquence reste juste)")
    zm = float(np.median(z))
    return ResultatPince(fichier=fichier, f_hz=float(np.median(f)), f_ecart_hz=float(np.std(f)),
                         zeta=zm, zeta_ecart=float(np.std(z)), q=1 / (2 * zm), pincements=pins, alerte=alerte)


def analyser_fichier(chemin, f_attendue=None):
    x, fs = lire_audio(chemin)
    return analyser(x, fs, f_attendue, fichier=chemin)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Fréquence propre et amortissement d'une languette pincée.")
    ap.add_argument("fichiers", nargs="+", help="wav, m4a, mp3...")
    ap.add_argument("--f", type=float, help="fréquence attendue (Hz), si le son a des harmoniques forts")
    a = ap.parse_args(argv)
    for ch in a.fichiers:
        r = analyser_fichier(ch, a.f)
        print(r.resume())
        for p in r.pincements:
            print(f"   à {p.t_debut_s:6.2f} s : f = {p.f_hz:.3f} Hz, zeta = {p.zeta:.2e}, Q = {p.q:.0f}, "
                  f"sur {p.duree_fit_s:.2f} s, {p.snr_db:.0f} dB au-dessus du bruit")


if __name__ == "__main__":
    main()

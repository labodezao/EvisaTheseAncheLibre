"""Les premiers modes d'une anche pincée : fréquence et amortissement de chacun.

`pince.py` donne le mode 1. Ce module donne les suivants (flexion 2 et 3, torsion, et,
quand l'anche est montée sur sa chambre, le résonateur d'air de la chambre).

Ce que fait l'outil, en mots
----------------------------
1. Il lit le fichier (wav, ou m4a et autres par ffmpeg, voir `pince.lire_audio`) et trouve
   chaque pincement (`pince.trouver_pincements`).
2. Pour chaque pincement, il cherche les pics du spectre de la première seconde : ce sont
   les candidats (on peut lui donner aussi les fréquences attendues du modèle).
3. Pour chaque candidat, il isole une bande étroite autour du pic (filtre gaussien), la
   ramène en bande de base (démodulation), la sous-échantillonne, puis ajuste une somme
   de 4 sinusoïdes amorties par ESPRIT (Roy et Kailath, 1989). Il garde la composante la
   plus forte près du centre : sa fréquence f et son taux de décroissance alpha (1/s).
   Pourquoi ce chemin : après la montée du filtre, une sinusoïde amortie filtrée reste
   EXACTEMENT une sinusoïde amortie de mêmes f et alpha ; le filtre ne biaise donc pas
   l'amortissement, il enlève seulement les autres modes et le bruit hors bande.
4. Il regroupe les mêmes modes d'un pincement à l'autre (médiane, écart), et marque ceux
   qui sont des HARMONIQUES d'un mode plus grave (fréquence k.f1 à 0,3 % près). Une anche
   qui passe dans sa fente rayonne de façon non linéaire : ses harmoniques sont dans le
   son, mais ce ne sont pas des modes de la languette. Signe de reconnaissance : un
   harmonique k s'éteint environ k fois plus vite que le mode 1 ; un vrai mode a son
   propre amortissement.
5. Il rend, par mode : f (Hz), zeta = alpha / (2 pi f_n), Q = 1 / (2 zeta), le nombre de
   pincements où il est vu, l'écart entre pincements, le niveau.

Ce qui peut tromper (et comment le voir)
----------------------------------------
- Le ronflement du secteur (50 Hz et ses multiples) ne décroît pas : il est écarté
  (alpha quasi nul) et signalé s'il tombe près d'un mode.
- Le gain automatique d'un téléphone fausse les amortissements (voir `pince.py`). Pour
  cette mesure, préférer la carte son et un micro, gain fixe.
- Un mode très amorti (le résonateur d'air de la chambre, Q de 10 à 50) s'éteint en
  quelques dizaines de millisecondes : peu d'échantillons, incertitude plus grande.
- Un mode non vu n'est pas un mode absent : le micro et le point de pincement peuvent
  tomber près d'un nœud. Pincer au bout ET au milieu de la languette.

Usage (depuis `research\\`) :
  J:\\claude\\venv\\Scripts\\python.exe -m banc_recherche.pince_modes son.wav [--fmax 4000]
      [--attendues 67.5 846 2721] [--csv sortie.csv]
"""
from __future__ import annotations

import csv
import math
import os
from dataclasses import asdict, dataclass, field

import numpy as np

from .pince import lire_audio, trouver_pincements

SECTEUR_HZ = 50.0


@dataclass
class Composante:
    """Un mode vu dans UN pincement."""
    f_hz: float
    alpha_s: float
    zeta: float
    niveau_db: float
    n_points: int


@dataclass
class ModeMesure:
    """Un mode regroupé sur tous les pincements."""
    f_hz: float
    f_ecart_hz: float
    zeta: float
    zeta_ecart: float
    q: float
    alpha_s: float
    niveau_db: float
    n_pincements: int
    nature: str = "mode"          # « mode », ou « harmonique k de f Hz »


@dataclass
class ResultatModes:
    fichier: str
    n_pincements: int
    modes: list = field(default_factory=list)
    brut: list = field(default_factory=list)      # liste (par pincement) de listes de Composante
    alertes: list = field(default_factory=list)

    def vrais_modes(self):
        return [m for m in self.modes if m.nature == "mode"]

    def resume(self):
        lignes = [f"{os.path.basename(self.fichier) or 'signal'} : {self.n_pincements} pincement(s), "
                  f"{len(self.vrais_modes())} mode(s)"]
        for m in self.modes:
            lignes.append(f"  {m.f_hz:9.2f} Hz (± {m.f_ecart_hz:.2f})  zeta = {m.zeta:.2e} (± {m.zeta_ecart:.1e})"
                          f"  Q = {m.q:6.0f}  {m.niveau_db:6.1f} dB  vu {m.n_pincements} fois  [{m.nature}]")
        lignes += [f"  attention : {a}" for a in self.alertes]
        return "\n".join(lignes)


# --- Briques de traitement du signal ---------------------------------------------------------
def esprit(z, p):
    """ESPRIT (moindres carrés) sur un signal complexe z : pôles lambda et amplitudes a,
    z[n] ~ somme a_i lambda_i^n. Référence : Roy et Kailath (1989), IEEE Trans. ASSP 37(7),
    984-995, doi:10.1109/29.32276 (même famille que le Matrix Pencil de Hua et Sarkar, 1990)."""
    z = np.asarray(z, complex)
    N = z.size
    L = N // 2
    H = np.lib.stride_tricks.sliding_window_view(z, L)          # (N - L + 1) x L, Hankel
    U, s, _ = np.linalg.svd(H.T, full_matrices=False)           # sous-espace signal : colonnes de U
    p = int(min(p, U.shape[1] - 1))
    Us = U[:, :p]
    lam = np.linalg.eigvals(np.linalg.pinv(Us[:-1]) @ Us[1:])
    V = np.vander(lam, N, increasing=True).T                    # N x p
    # colonnes normalisées : un pôle de bruit qui croît (|lambda| > 1) aurait sinon une
    # colonne énorme, et les moindres carrés écraseraient les vrais modes
    nv = np.linalg.norm(V, axis=0)
    nv[nv == 0] = 1.0
    a = np.linalg.lstsq(V / nv, z, rcond=None)[0] / nv
    return lam, a


def bande_de_base(x, fs, fc, sigma_hz):
    """Signal analytique filtré par une gaussienne (écart-type sigma_hz) centrée sur fc, puis
    ramené en bande de base (multiplié par exp(-2 i pi fc t)). Filtre à phase nulle."""
    x = np.asarray(x, float)
    n = x.size
    N = 1 << int(np.ceil(np.log2(n)))
    X = np.fft.fft(x, N)
    f = np.fft.fftfreq(N, 1 / fs)
    G = np.exp(-0.5 * ((f - fc) / sigma_hz) ** 2)
    G[f < 0] = 0.0                                               # analytique : fréquences positives
    y = np.fft.ifft(2 * X * G)[:n]
    t = np.arange(n) / fs
    return y * np.exp(-2j * np.pi * fc * t)


def _blackman_harris(n):
    """Fenêtre de Blackman-Harris à 4 termes : lobes secondaires à -92 dB. Avec une fenêtre de
    Hann (-31 dB), les lobes du mode 1, 60 dB plus fort, passeraient pour des modes."""
    k = 2 * np.pi * np.arange(n) / max(1, n - 1)
    return 0.35875 - 0.48829 * np.cos(k) + 0.14128 * np.cos(2 * k) - 0.01168 * np.cos(3 * k)


def _proeminence(S, i):
    """Hauteur du pic i au-dessus du plus haut des deux creux qui le séparent d'un pic plus
    haut (ou du bord) : la proéminence topographique, en dB."""
    plus_haut_g = np.nonzero(S[:i] > S[i])[0]
    plus_haut_d = np.nonzero(S[i + 1:] > S[i])[0]
    g = int(plus_haut_g[-1]) if plus_haut_g.size else 0
    d = i + 1 + int(plus_haut_d[0]) if plus_haut_d.size else S.size - 1
    return float(S[i] - max(S[g:i + 1].min(), S[i:d + 1].min()))


def pics_candidats(seg, fs, f_min=20.0, f_max=5000.0, emergence_db=15.0, dynamique_db=60.0,
                   n_max=10, duree_s=1.0):
    """Pics du spectre de la tête du pincement : (fréquence, niveau dB), du plus fort au moins fort."""
    tete = np.asarray(seg[: int(min(duree_s, len(seg) / fs) * fs)], float)
    tete = tete - tete.mean()
    if tete.size < 64:
        return []
    N = 1 << int(np.ceil(np.log2(tete.size)) + 2)
    S = 20 * np.log10(np.abs(np.fft.rfft(tete * _blackman_harris(tete.size), N)) + 1e-15)
    fr = np.fft.rfftfreq(N, 1 / fs)
    m = (fr >= f_min) & (fr <= min(f_max, 0.45 * fs))
    if not m.any():
        return []
    Sb, fb = S[m], fr[m]
    fond = float(np.median(Sb))
    haut = float(Sb.max())
    loc = np.nonzero((Sb[1:-1] > Sb[:-2]) & (Sb[1:-1] >= Sb[2:]))[0] + 1
    loc = [i for i in loc if Sb[i] > fond + emergence_db and Sb[i] > haut - dynamique_db
           and _proeminence(Sb, i) > 10.0]
    loc.sort(key=lambda i: -Sb[i])
    gardes = []
    for i in loc:                                                # fusionner les pics à moins de 2 %
        if all(abs(fb[i] - fb[j]) > 0.02 * fb[j] for j in gardes):
            gardes.append(i)
        if len(gardes) >= n_max:
            break
    return [(float(fb[i]), float(Sb[i])) for i in gardes]


def ajuster_mode(seg, fs, fc, ordre=4, chute_db=40.0, n_max_points=1200, largeur_rel=0.06,
                 largeur_min_hz=6.0, debut_s=0.0):
    """Le mode le plus fort près de fc dans `seg` (commençant au pincement) -> Composante ou None.

    `debut_s` : temps à sauter après le début (le choc du doigt)."""
    sigma = max(largeur_min_hz, largeur_rel * fc)
    z = bande_de_base(seg, fs, fc, sigma)
    sigma_t = 1.0 / (2 * np.pi * sigma)                          # durée de la réponse du filtre
    a = int((debut_s + 4 * sigma_t) * fs)
    if a >= z.size - 16:
        return None
    D = max(1, int(fs / (10 * sigma)))                           # garde +-5 sigma, sans repliement
    zd = z[a::D]
    fsd = fs / D
    env = np.abs(zd)
    pic = int(np.argmax(env[: max(2, int(0.2 * fsd))]))
    zd, env = zd[pic:], env[pic:]
    if env.size < 16 or env[0] <= 0:
        return None
    # fin : chute_db sous le pic ou 6 dB au-dessus du fond (le dernier dixième du segment)
    fond = float(np.median(env[-max(4, env.size // 10):]))
    seuil = max(env[0] * 10 ** (-chute_db / 20), 2.0 * fond)
    sous = np.nonzero(env < seuil)[0]
    b = int(sous[0]) if sous.size else env.size
    if b < 16:
        return None
    if b > n_max_points:                                        # trop long : sous-échantillonner encore
        k = int(np.ceil(b / n_max_points))
        zd, fsd, b = zd[::k], fsd / k, b // k
    lam, amp = esprit(zd[:b], ordre)
    df = np.angle(lam) * fsd / (2 * np.pi)
    alpha = -np.log(np.abs(lam) + 1e-300) * fsd
    # énergie de chaque composante sur la fenêtre : un pôle de bruit très amorti peut avoir
    # une grande amplitude initiale, pas une grande énergie
    r2 = np.minimum(np.abs(lam) ** 2, 1 - 1e-12)
    energie = np.abs(amp) ** 2 * (1 - r2 ** b) / (1 - r2)
    ok = (np.abs(df) < 2.5 * sigma) & (alpha > -1e-3 * fsd)
    if not ok.any():
        return None
    i = int(np.argmax(np.where(ok, energie, -1)))
    wd = 2 * np.pi * (fc + df[i])
    al = float(alpha[i])
    wn = math.sqrt(wd ** 2 + al ** 2)
    return Composante(f_hz=float(fc + df[i]), alpha_s=al, zeta=al / wn if wn > 0 else float("nan"),
                      niveau_db=float(20 * np.log10(np.abs(amp[i]) + 1e-15)), n_points=int(b))


def candidats_multi(tete, fs, f_min, f_max, n_max=10, durees=(0.03, 0.1, 0.3, 1.0)):
    """Candidats sur des fenêtres de plus en plus longues, toutes au début du pincement : un
    mode très amorti (la chambre, la torsion) n'est visible que dans les premières dizaines de
    millisecondes, un mode peu amorti se sépare de ses voisins sur la seconde."""
    cands = []
    for T in durees:
        if T * fs < 64:
            continue
        fmin_T = max(f_min, 6.0 / T)                             # au moins 6 périodes dans la fenêtre
        for f, _ in pics_candidats(tete, fs, fmin_T, f_max, n_max=n_max, duree_s=T):
            if all(abs(f - c) > 0.03 * c for c in cands):
                cands.append(f)
    return cands


def modes_pincement(seg, fs, f_max=5000.0, f_min=20.0, attendues=(), ordre=4, n_max=10):
    """Toutes les composantes amorties d'un pincement (le signal depuis son début)."""
    seg = np.asarray(seg, float) - np.mean(seg)
    debut = 0.01                                                 # le choc du doigt
    tete = seg[int(debut * fs):]
    cands = candidats_multi(tete, fs, f_min, f_max, n_max=n_max)
    for fa in attendues:                                         # chercher aussi autour du modèle
        if f_min <= fa <= f_max and all(abs(fa - c) > 0.05 * fa for c in cands):
            loc = pics_candidats(tete, fs, fa * 0.85, fa * 1.15, emergence_db=6.0, n_max=1)
            if loc:
                cands.append(loc[0][0])
    comps = []
    for fc in sorted(cands):
        c = ajuster_mode(seg, fs, fc, ordre=ordre, debut_s=debut)
        if c is None or not (c.alpha_s > 0.05):                  # ne décroît pas : secteur, sifflement
            continue
        if any(abs(c.f_hz - d.f_hz) < 0.005 * c.f_hz for d in comps):
            continue                                             # même composante vue deux fois
        comps.append(c)
    return comps


# --- Regroupement sur les pincements ----------------------------------------------------------
def regrouper(listes, tol_rel=0.01, part_min=0.5):
    """Regroupe les composantes de plusieurs pincements par fréquence (tolérance relative)."""
    toutes = sorted((c for l in listes for c in l), key=lambda c: c.f_hz)
    groupes = []
    for c in toutes:
        if groupes and abs(c.f_hz - np.median([d.f_hz for d in groupes[-1]])) < tol_rel * c.f_hz:
            groupes[-1].append(c)
        else:
            groupes.append([c])
    n = max(1, len(listes))
    modes = []
    for g in groupes:
        if len(g) < max(1, math.ceil(part_min * n)):
            continue
        f = np.array([c.f_hz for c in g]); z = np.array([c.zeta for c in g])
        a = np.array([c.alpha_s for c in g]); lv = np.array([c.niveau_db for c in g])
        zm = float(np.median(z))
        modes.append(ModeMesure(f_hz=float(np.median(f)), f_ecart_hz=float(np.std(f)), zeta=zm,
                                zeta_ecart=float(np.std(z)), q=1 / (2 * zm) if zm > 0 else float("inf"),
                                alpha_s=float(np.median(a)), niveau_db=float(np.median(lv)), n_pincements=len(g)))
    return modes


def marquer_harmoniques(modes, tol=0.003, k_max=12):
    """Un mode à k.f_j (0,3 %) d'un mode plus grave et plus fort est marqué harmonique."""
    for i, m in enumerate(modes):
        for j in range(i):
            b = modes[j]
            if b.nature != "mode":
                continue
            k = round(m.f_hz / b.f_hz)
            if 2 <= k <= k_max and abs(m.f_hz / (k * b.f_hz) - 1) < tol:
                ratio = m.alpha_s / b.alpha_s if b.alpha_s > 0 else float("nan")
                m.nature = f"harmonique {k} de {b.f_hz:.2f} Hz (décroît {ratio:.1f} fois plus vite)"
                break
    return modes


def analyser(x, fs, f_max=5000.0, attendues=(), fichier="", ordre=4, duree_max_s=4.0):
    debuts, _ = trouver_pincements(x, fs)
    if not debuts:
        raise ValueError("aucun pincement trouvé (son trop faible ?)")
    bornes = list(debuts) + [len(x)]
    brut = []
    for i, d in enumerate(debuts):
        fin = min(bornes[i + 1], d + int(duree_max_s * fs))
        if fin - d < int(0.1 * fs):
            continue
        brut.append(modes_pincement(x[d:fin], fs, f_max=f_max, attendues=attendues, ordre=ordre))
    modes = marquer_harmoniques(regrouper(brut))
    r = ResultatModes(fichier=fichier, n_pincements=len(brut), modes=modes, brut=brut)
    for m in modes:
        k = round(m.f_hz / SECTEUR_HZ)
        if k >= 1 and abs(m.f_hz - k * SECTEUR_HZ) < 1.0:
            r.alertes.append(f"{m.f_hz:.2f} Hz est près de {k} x 50 Hz (secteur) : vérifier qu'il décroît")
        if m.zeta_ecart > 0.2 * m.zeta and m.n_pincements >= 2 and m.nature == "mode":
            r.alertes.append(f"amortissement de {m.f_hz:.1f} Hz dispersé de plus de 20 % (gain automatique ? "
                             "pincements trop différents ?)")
    if len(brut) < 3:
        r.alertes.append("moins de 3 pincements : pas d'écart-type fiable")
    return r


def analyser_fichier(chemin, f_max=5000.0, attendues=(), ordre=4):
    x, fs = lire_audio(chemin)
    return analyser(x, fs, f_max=f_max, attendues=attendues, fichier=chemin, ordre=ordre)


def ecrire_csv(r: ResultatModes, chemin):
    os.makedirs(os.path.dirname(os.path.abspath(chemin)), exist_ok=True)
    with open(chemin, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["fichier"] + list(asdict(r.modes[0]).keys()) if r.modes else ["fichier"],
                           delimiter=";")
        w.writeheader()
        for m in r.modes:
            w.writerow({"fichier": os.path.basename(r.fichier), **asdict(m)})


def main(argv=None):
    import argparse
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description="Fréquences et amortissements des premiers modes d'une anche pincée.")
    ap.add_argument("fichiers", nargs="+")
    ap.add_argument("--fmax", type=float, default=5000.0, help="fréquence maximale cherchée (Hz)")
    ap.add_argument("--attendues", type=float, nargs="*", default=[], help="fréquences du modèle (Hz)")
    ap.add_argument("--csv", help="écrire les modes dans ce CSV (un fichier : ce nom ; plusieurs : suffixe)")
    a = ap.parse_args(argv)
    for i, ch in enumerate(a.fichiers):
        r = analyser_fichier(ch, a.fmax, a.attendues)
        print(r.resume())
        if a.csv and r.modes:
            sortie = a.csv if len(a.fichiers) == 1 else a.csv.replace(".csv", f"_{i + 1}.csv")
            ecrire_csv(r, sortie)
            print("->", sortie)


if __name__ == "__main__":
    main()

"""Figures du manuscrit (design_theory.lyx), chapitre « Static and modal analysis ».

Elles sont produites à partir des résultats déjà versés (aucun calcul Elmer ici) :
- `docs/figures/elmer_maillage_languette.png` : (a) convergence du maillage de la languette
  de matrix.txt (hexaèdres quadratiques), écart à Euler-Bernoulli ; (b) la lame de la CAO
  2019 : Euler-Bernoulli, Elmer (hexaèdres quadratiques) et Code_Aster 2019 (tétraèdres
  linéaires, une couche dans l'épaisseur) : le verrouillage.
- `docs/figures/pince_modes_synthese.png` : ce que rend l'analyse du son pincé
  (`banc_recherche/pince_modes.py`) sur un pincement de synthèse construit avec les modes
  d'Elmer de l'anche R12-grave et le résonateur de sa chambre (Q = 20, valeur supposée).

Usage (depuis `research\\fem\\`) : J:\\claude\\venv\\Scripts\\python.exe figures_these.py
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(ICI, "..")))
FIG = os.path.abspath(os.path.join(ICI, "..", "docs", "figures"))


def _csv(ch):
    with open(ch, encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def figure_maillage():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    conv = _csv(os.path.join(ICI, "anche", "resultats", "convergence_languette.csv"))
    verif = _csv(os.path.join(ICI, "anche", "resultats", "verification_languette.csv"))
    f_eb = float(next(r for r in verif if r["cas"] == "matrix_txt_pied" and r["mode_flexion"] == "1")["EB_exact_Hz"])
    rk4 = _csv(os.path.join(ICI, "resultats", "recalage_rk4_languette.csv"))
    cao = {r["grandeur"]: r for r in rk4 if r["languette"].startswith("CAO 2019")}

    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    n = np.array([float(r["noeuds"]) for r in conv])
    f1 = np.array([float(r["f1_Hz"]) for r in conv])
    h = [r["hx_mm"] for r in conv]
    a = ax[0]
    a.semilogx(n, 100 * (f1 / f_eb - 1), "ko-")
    for ni, fi, hi in zip(n, f1, h):
        a.annotate(f"{hi} mm\n{fi:.2f} Hz", (ni, 100 * (fi / f_eb - 1)), textcoords="offset points",
                   xytext=(6, 4), fontsize=8)
    a.axhline(0, color="0.5", lw=0.8)
    a.set_xlabel("nombre de nœuds (hexaèdres à 20 nœuds)")
    a.set_ylabel("f1 Elmer / f1 Euler-Bernoulli - 1 (%)")
    a.set_title(f"(a) anche de matrix.txt : f1 EB exact = {f_eb:.2f} Hz", fontsize=10)
    a.set_ylim(0, 0.7)
    a.text(0.03, 0.06, "le reste (+0,3 %) est l'effet de plaque :\nsection carrée 0,3 x 0,3 mm : +0,13 %",
           transform=a.transAxes, fontsize=8)

    b = ax[1]
    modes = ["f1 (Hz)", "f2 (Hz)"]
    eb = [float(cao[m]["euler_bernoulli"]) for m in modes]
    el = [float(cao[m]["elmer_recale"]) for m in modes]
    ca = [float(cao["f1 Code_Aster 2019, tétraèdres linéaires (Hz)"]["elmer_recale"]),
          float(cao["f2 Code_Aster 2019, tétraèdres linéaires (Hz)"]["elmer_recale"])]
    x = np.arange(2)
    w = 0.26
    for k, (v, lab, c) in enumerate([(eb, "Euler-Bernoulli exact", "0.6"),
                                     (el, "Elmer, hexaèdres quadratiques", "k"),
                                     (ca, "Code_Aster 2019, tétraèdres linéaires", "r")]):
        bars = b.bar(x + (k - 1) * w, v, w, label=lab, color=c)
        for r_, val in zip(bars, v):
            b.annotate(f"{val:.1f}", (r_.get_x() + r_.get_width() / 2, val), ha="center", va="bottom", fontsize=7)
    b.set_yscale("log")
    b.set_xticks(x, ["mode 1", "mode 2"])
    b.set_ylabel("fréquence (Hz)")
    b.set_title("(b) lame de la CAO 2019 : le maillage verrouillé (x 5,7 sur f1)", fontsize=10)
    b.legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    os.makedirs(FIG, exist_ok=True)
    ch = os.path.join(FIG, "elmer_maillage_languette.png")
    fig.savefig(ch, dpi=130)
    plt.close(fig)
    return ch


def figure_pince():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from banc_recherche import pince_modes as pm
    d = json.load(open(os.path.join(ICI, "anche", "resultats", "modal_R12-grave.json"), encoding="utf-8"))
    f_H = json.load(open(os.path.join(ICI, "sommier", "resultats", "impedance_R12-grave.json"),
                         encoding="utf-8"))["reseau"]["f1_Hz"]
    fs = 48000
    # supposés (à mesurer) : zeta des modes de la languette ; résonateur de chambre à Q = 20
    vrais = [(d["frequences_Hz"][0], 2e-3, 1.0), (d["frequences_Hz"][1], 4e-3, 0.3),
             (d["frequences_Hz"][3], 6e-3, 0.06), (f_H, 0.025, 0.3)]
    rng = np.random.default_rng(3)
    morceaux = []
    for k in range(3):
        t = np.arange(int(2.0 * fs)) / fs
        y = sum(a * np.exp(-z * 2 * np.pi * f * t) * np.sin(2 * np.pi * f * t + k) for f, z, a in vrais)
        y = y + 0.04 * np.exp(-2 * 2e-3 * 2 * np.pi * vrais[0][0] * t) * np.sin(2 * 2 * np.pi * vrais[0][0] * t)
        morceaux.append(np.concatenate([np.zeros(int(0.3 * fs)), y]))
    x = np.concatenate(morceaux) + 2e-4 * rng.standard_normal(sum(m.size for m in morceaux))
    r = pm.analyser(x, fs, f_max=3000)

    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    seg = x[int(0.31 * fs):int(1.31 * fs)]
    N = 1 << 18
    S = 20 * np.log10(np.abs(np.fft.rfft(seg * pm._blackman_harris(seg.size), N)) + 1e-12)
    fr = np.fft.rfftfreq(N, 1 / fs)
    m = (fr > 20) & (fr < 3000)
    court = x[int(0.31 * fs):int(0.36 * fs)]                      # les 50 premières ms
    Sc = 20 * np.log10(np.abs(np.fft.rfft(court * pm._blackman_harris(court.size), N)) + 1e-12)
    a = ax[0]
    a.semilogx(fr[m], S[m] - S[m].max(), "k-", lw=0.7, label="fenêtre de 1 s")
    a.semilogx(fr[m], Sc[m] - Sc[m].max(), color="orange", lw=0.9, label="fenêtre de 50 ms")
    for mo in r.modes:
        c = "b" if mo.nature == "mode" else "0.5"
        a.axvline(mo.f_hz, color=c, ls="--", lw=0.8)
        a.annotate(f"{mo.f_hz:.1f} Hz\nQ = {mo.q:.0f}", (mo.f_hz, -8), fontsize=7, color=c, rotation=90,
                   va="top", ha="right")
    a.set_xlabel("f (Hz)")
    a.set_ylabel("dB (relatif)")
    a.set_ylim(-110, 5)
    a.set_title("(a) spectres ; tirets bleus : modes trouvés, gris : harmonique", fontsize=10)
    a.legend(fontsize=8, loc="lower left")
    b = ax[1]
    t = np.arange(int(0.9 * fs)) / fs
    for mo in r.vrais_modes():
        z = pm.bande_de_base(x[int(0.3 * fs):int(1.3 * fs)], fs, mo.f_hz, max(6.0, 0.06 * mo.f_hz))
        e = 20 * np.log10(np.abs(z[:t.size]) + 1e-12)
        b.plot(t[::40], e[::40] - e[: int(0.05 * fs)].max(), lw=0.8, label=f"{mo.f_hz:.0f} Hz")
        b.plot(t, -8.686 * mo.alpha_s * t, "k:", lw=0.6)
    b.set_ylim(-80, 5)
    b.set_xlabel("t (s)")
    b.set_ylabel("enveloppe de la bande (dB)")
    b.set_title("(b) décroissances ; pointillés : exp(-alpha t) ajusté par ESPRIT", fontsize=10)
    b.legend(fontsize=8)
    fig.tight_layout()
    ch = os.path.join(FIG, "pince_modes_synthese.png")
    fig.savefig(ch, dpi=130)
    plt.close(fig)
    ecarts = [(round(mo.f_hz, 3), round(f, 3), round(mo.zeta / z - 1, 4)) for mo, (f, z, _) in zip(r.vrais_modes(), sorted(vrais))]
    return ch, ecarts


if __name__ == "__main__":
    print("->", figure_maillage())
    ch, e = figure_pince()
    print("->", ch, e)

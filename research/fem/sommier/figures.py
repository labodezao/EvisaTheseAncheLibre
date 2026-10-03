"""Figures des calculs de chambre (lit resultats/*.csv, écrit resultats/*.png).

  J:\\claude\\venv\\Scripts\\python.exe figures.py
"""
import csv
import math
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ICI = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(ICI, "resultats")


def lire(nom):
    chemin = os.path.join(RES, nom)
    if not os.path.exists(chemin):
        return []
    return list(csv.DictReader(open(chemin, encoding="utf-8"), delimiter=";"))


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def fig_modes():
    r = lire("modes_chambres_R12.csv")
    if not r:
        return
    k = [int(x["chambre"]) for x in r]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(k, [num(x["f1_Hz"]) for x in r], "o-", label="mode 1 (Elmer) : cases A et B ensemble, par le trou")
    ax.plot(k, [num(x["f2_Hz"]) for x in r], "s--", label="mode 2 (Elmer) : case A contre case B")
    ax.plot(k, [num(x["f_helmholtz_Hz"]) for x in r], "x:", label="formule de Helmholtz (constantes localisées)")
    ax.set_xlabel("chambre du sommier R12 (1 = grave)")
    ax.set_ylabel("fréquence (Hz)")
    ax.set_title("Résonances de l'air des chambres du R12\n(trou de table supposé 8 x 25 mm, table 8 mm)",
                 fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(RES, "modes_chambres_R12.png"), dpi=130)


def fig_seuils():
    r = lire("seuils_rapport.csv")
    if not r:
        return
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4.2))
    for f in sorted({x["f_lame_Hz"] for x in r}, key=float):
        rr = [x for x in r if x["f_lame_Hz"] == f]
        rap = [num(x["fH_sur_flame"]) for x in rr]
        pon = [num(x["p_on_Pa"]) for x in rr]
        cts = [num(x["f_on_cents"]) for x in rr]
        a1.semilogy(rap, pon, "o-", label=f"lame {float(f):.0f} Hz")
        a2.plot(rap, cts, "o-", label=f"lame {float(f):.0f} Hz")
        for x, p in zip(rap, pon):
            if math.isnan(p):
                a1.plot([x], [8000], "kx")
    a1.axhline(8000, color="k", lw=0.5, ls=":")
    a1.text(0.52, 8500, "x : ne démarre pas sous 8000 Pa", fontsize=7)
    a1.set_xlabel("résonance de la chambre / fréquence de la lame")
    a1.set_ylabel("seuil de démarrage p_on (Pa)")
    a1.grid(alpha=0.3, which="both")
    a1.legend(fontsize=8)
    a2.set_xlabel("résonance de la chambre / fréquence de la lame")
    a2.set_ylabel("justesse au seuil (cents, par rapport à la lame)")
    a2.grid(alpha=0.3)
    fig.suptitle("Petit modèle (coupled_reeds, une anche) : le seuil dépend de la résonance de la chambre", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(RES, "seuils_rapport.png"), dpi=130)


if __name__ == "__main__":
    fig_modes()
    fig_seuils()
    print("figures dans", RES)

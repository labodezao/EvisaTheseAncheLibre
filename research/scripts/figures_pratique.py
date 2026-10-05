#!/usr/bin/env python3
"""Figures de design_practical (hors mécanique main gauche, voir figures_mecanique.py).

    python research/scripts/figures_pratique.py          # FR et EN dans research/docs/figures/

- pratique_levee_<fr|en> : la levée utile d'une soupape. En coupe, l'air sort par le
  « rideau » qui fait le tour du trou (périmètre P x levée h) ; le passage vaut
  min(P h, A) et plafonne à h = A / P.
- pratique_joint_<fr|en> : fuite d'un joint plat contre son jeu (loi de Poiseuille en h³),
  avec les critères proposés de l'atelier.
- pratique_soufflet_<fr|en> : la fenêtre de section du soufflet. Au-dessus de F / p le bras
  ne fait plus la pression ; au-dessous de Q t / course, l'air manque avant la fin de la
  phrase. Chiffres ronds d'exemple (bras 30 à 60 N, course 0,4 m, phrase 4 s), à remplacer
  par les mesures.
Les calculs viennent de outils_atelier.py (mêmes fonctions que le texte).
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, Rectangle

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import outils_atelier as oa  # noqa: E402

SORTIE = os.path.join(ICI, "..", "docs", "figures")
BLEU, ROUGE, GRIS, BOIS = "#1f5fa8", "#c0392b", "#7f8c8d", "#c8a26b"

T = {
    "fr": {
        "coupe": "(a) En coupe : l'air sort par le rideau",
        "table": "table d'harmonie", "cuir": "soupape (cuir)", "trou": "trou : aire A",
        "rideau": "rideau : P × h", "h": "h",
        "courbe": "(b) Passage d'air contre levée",
        "x": "levée h (mm)", "y": "passage d'air (mm²)",
        "lim_rideau": "rideau P × h", "lim_trou": "trou A",
        "utile": "levée utile h = A / P",
        "cas": "trou {}", "joint": "Fuite d'un joint plat (500 Pa, 100 mm de tour, 5 mm de portée)",
        "jx": "jeu du joint (mm)", "jy": "fuite (L/min)",
        "c1": "soupape : 0,02 L/min", "c2": "sommier : 0,05 L/min", "c3": "caisse : 0,5 L/min",
        "pente": "jeu × 2  →  fuite × 8", "dec": ",",
        "sf_titre": "Section du soufflet : la fenêtre (chiffres ronds d'exemple)",
        "sf_x": "pression de jeu demandée (Pa)", "sf_y": "section efficace (cm²)",
        "sf_bras": "bras {} N : S = F / p", "sf_air": "air : {} anches à {} L/min, 4 s, course 0,4 m",
        "sf_trop_grand": "trop grand :\nle bras ne fait plus la pression",
        "sf_trop_petit": "trop petit : l'air manque", "sf_ok": "fenêtre\n(bras 40 N, forte)",
    },
    "en": {
        "coupe": "(a) In section: the air leaves through the curtain",
        "table": "soundboard", "cuir": "pallet (leather)", "trou": "hole: area A",
        "rideau": "curtain: P × h", "h": "h",
        "courbe": "(b) Air passage against lift",
        "x": "lift h (mm)", "y": "air passage (mm²)",
        "lim_rideau": "curtain P × h", "lim_trou": "hole A",
        "utile": "useful lift h = A / P",
        "cas": "hole {}", "joint": "Leak of a flat joint (500 Pa, 100 mm around, 5 mm land)",
        "jx": "gap of the joint (mm)", "jy": "leak (L/min)",
        "c1": "pallet: 0.02 L/min", "c2": "reed block: 0.05 L/min", "c3": "case: 0.5 L/min",
        "pente": "gap × 2  →  leak × 8", "dec": ".",
        "sf_titre": "Bellows section: the window (round example numbers)",
        "sf_x": "playing pressure asked for (Pa)", "sf_y": "effective area (cm²)",
        "sf_bras": "arm {} N: S = F / p", "sf_air": "air: {} reeds at {} L/min, 4 s, stroke 0.4 m",
        "sf_trop_grand": "too large:\nthe arm no longer makes the pressure",
        "sf_trop_petit": "too small: the air runs out", "sf_ok": "window\n(arm 40 N, forte)",
    },
}


def fleche(ax, x0, y0, x1, y1, c=BLEU, lw=2.0):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=14, color=c, lw=lw))


def figure_levee(langue):
    t = T[langue]
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1.1, 1]})
    # (a) coupe
    ax.set_xlim(0, 10); ax.set_ylim(0, 6); ax.axis("off"); ax.set_title(t["coupe"], fontsize=11)
    ax.add_patch(Rectangle((0.3, 1.5), 3.0, 1.0, color=BOIS))
    ax.add_patch(Rectangle((6.7, 1.5), 3.0, 1.0, color=BOIS))
    ax.text(3.6, 0.6, t["trou"], ha="right", fontsize=9)
    ax.text(1.0, 1.15, t["table"], fontsize=8.5, color="#6b4f2a")
    ax.add_patch(Rectangle((2.3, 3.5), 5.4, 0.35, color="#8e5b3a"))
    ax.text(5, 4.05, t["cuir"], ha="center", fontsize=9)
    ax.annotate("", xy=(8.2, 2.5), xytext=(8.2, 3.5), arrowprops=dict(arrowstyle="<->", color=ROUGE))
    ax.text(8.35, 2.9, t["h"], color=ROUGE, fontsize=11)
    for x0 in (4.0, 5.0, 6.0):
        fleche(ax, x0, 0.3, x0, 2.9)
    fleche(ax, 3.4, 3.0, 1.3, 3.6); fleche(ax, 6.6, 3.0, 8.8, 3.6)
    ax.add_patch(Rectangle((3.3, 2.5), 0.06, 1.0, color=ROUGE, alpha=0.6))
    ax.add_patch(Rectangle((6.64, 2.5), 0.06, 1.0, color=ROUGE, alpha=0.6))
    ax.text(5, 5.1, t["rideau"], ha="center", color=ROUGE, fontsize=10)
    # (b) courbe, trou 20 x 15 (basses du Lib RT) et 8 x 25
    h = np.linspace(0, 8, 400)
    for trou, c in (("20x15", BLEU), ("15x15", "#e67e22"), ("8x12", "#16a085")):
        a, p = oa.lire_trou(trou)
        hu = oa.levee_utile_mm(a, p)
        bx.plot(h, np.minimum(p * h, a), color=c, lw=2.2, label=t["cas"].format(trou.replace("x", " × ") + " mm"))
        bx.plot(h, p * h, color=c, lw=1, ls=":")
        bx.axvline(hu, color=c, lw=1, ls="--")
        bx.text(hu + 0.08, {"20x15": 60, "15x15": 35, "8x12": 10}[trou], f"{hu:.2f} mm".replace(".", t["dec"]), color=c, fontsize=9)
    bx.set_ylim(0, 380); bx.set_xlim(0, 8)
    bx.set_xlabel(t["x"]); bx.set_ylabel(t["y"]); bx.set_title(t["courbe"], fontsize=11)
    bx.text(0.4, 340, t["lim_rideau"] + "  (· · ·)", fontsize=8.5, color=GRIS)
    bx.legend(loc="upper left", bbox_to_anchor=(0.0, 0.9), fontsize=9, title=t["utile"], title_fontsize=9)
    bx.grid(alpha=0.3)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(SORTIE, f"pratique_levee_{langue}.{ext}"), dpi=200, bbox_inches="tight")
    plt.close(fig)


def figure_joint(langue):
    t = T[langue]
    fig, ax = plt.subplots(figsize=(7.5, 4.3))
    jeu = np.logspace(np.log10(0.005), np.log10(0.2), 200)
    ax.loglog(jeu, oa.fuite_fente_lpm(jeu, 100, 5, 500), color=BLEU, lw=2.4)
    for q, lab, c in ((0.02, t["c1"], "#16a085"), (0.05, t["c2"], "#e67e22"), (0.5, t["c3"], ROUGE)):
        h = oa.jeu_max_mm(q, 100, 5, 500)
        ax.axhline(q, color=c, lw=1, ls="--")
        ax.plot([h], [q], "o", color=c)
        ax.text(0.0052, q * 1.15, f"{lab}  →  {h:.3f} mm".replace("0.", "0" + t["dec"]), color=c, fontsize=9)
    ax.text(0.06, 0.004, t["pente"], fontsize=10, color=BLEU)
    ax.set_xlabel(t["jx"]); ax.set_ylabel(t["jy"]); ax.set_title(t["joint"], fontsize=10.5)
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(SORTIE, f"pratique_joint_{langue}.{ext}"), dpi=200, bbox_inches="tight")
    plt.close(fig)


def figure_soufflet(langue):
    t = T[langue]
    fig, ax = plt.subplots(figsize=(7.8, 4.6))
    p = np.linspace(400, 3000, 200)
    for f_bras, c, lw in ((30, GRIS, 1.2), (40, BLEU, 2.4), (60, GRIS, 1.2)):
        ax.plot(p, f_bras / p * 1e4, color=c, lw=lw, label=t["sf_bras"].format(f_bras))
    for voix, debit, c, ls in ((9, 10, ROUGE, "-"), (2, 2, "#16a085", "--")):
        smin = oa.fenetre_soufflet(40, 1000, voix, debit, 0.4, 4)[0] * 1e4
        ax.axhline(smin, color=c, ls=ls, lw=1.6, label=t["sf_air"].format(voix, debit))
    smin = oa.fenetre_soufflet(40, 1000, 9, 10, 0.4, 4)[0] * 1e4
    pp = p[40 / p * 1e4 >= smin]
    ax.fill_between(pp, smin, 40 / pp * 1e4, color=BLEU, alpha=0.15)
    ax.text(700, 260, t["sf_ok"], color=BLEU, fontsize=9.5)
    ax.text(1500, 560, t["sf_trop_grand"], fontsize=9, color=GRIS)
    ax.text(2000, 95, t["sf_trop_petit"], fontsize=9, color=ROUGE)
    ax.set_ylim(0, 800); ax.set_xlim(400, 3000)
    ax.set_xlabel(t["sf_x"]); ax.set_ylabel(t["sf_y"]); ax.set_title(t["sf_titre"], fontsize=10.5)
    ax.legend(fontsize=8, loc="upper right"); ax.grid(alpha=0.3)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(SORTIE, f"pratique_soufflet_{langue}.{ext}"), dpi=200, bbox_inches="tight")
    plt.close(fig)


def main():
    os.makedirs(SORTIE, exist_ok=True)
    for langue in ("fr", "en"):
        figure_levee(langue)
        figure_joint(langue)
        figure_soufflet(langue)
    print("Figures écrites dans", os.path.normpath(SORTIE))


if __name__ == "__main__":
    main()

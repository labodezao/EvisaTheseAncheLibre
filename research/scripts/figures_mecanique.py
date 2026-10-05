#!/usr/bin/env python3
"""Figures du chapitre « mécanique main gauche » (soupapes, leviers, compensations).

    python research/scripts/figures_mecanique.py            # FR et EN dans research/docs/figures/

Dessins de principe en coupe (pas à l'échelle), et efforts au bouton calculés avec les
hypothèses du rapport d'ingénierie (J:/zw3d_travail/librt/theorie, calcul_mecanique.py) :
trou 20 x 15 mm (300 mm²), jeu 2 kPa, pointe 3 kPa, ressort F0 = 1,38 N, k = 0,069 N/mm,
levée 5 mm, course 5 mm (r = 1), rendement 0,9, 1 N = 102 g.

Sorties : mecanique_<nom>_<fr|en>.png (et .pdf) ; mêmes noms dans les deux documents LyX.
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Polygon, Rectangle

ICI = os.path.dirname(os.path.abspath(__file__))
SORTIE = os.path.join(ICI, "..", "docs", "figures")

# ---------------------------------------------------------------- calcul ---
A = 300e-6            # m², trou 20 x 15
DP_JEU, DP_POINTE = 2000.0, 3000.0
F0, K, LEVEE, R, ETA = 1.38, 0.069, 5.0, 1.0, 0.9
G = 102.0             # g par N


def bouton(f_soupape):
    return f_soupape * R / ETA * G


def efforts():
    """(décollement au tiré, mi-course, retour au poussé max) en grammes au bouton."""
    mi = F0 + K * LEVEE / 2
    ref = (bouton(F0 + DP_JEU * A), bouton(mi), (F0 - DP_POINTE * A) * ETA * G)
    pilote_aire = 36e-6                                  # petite soupape 6 x 6 mm
    pilote = (bouton(F0 + DP_JEU * pilote_aire), bouton(mi), ref[2])
    deux = ref                                           # même aire, même F0 totale
    f_etanch = 0.4                                       # équilibrée : reste l'étanchéité
    equil = (bouton(f_etanch), bouton(f_etanch * (1 + 0.25 / 2)), f_etanch * ETA * G)
    aide = 0.075 * G                                     # ressort d'aide 7,5 g au bouton
    ressort_aide = (ref[0] - aide, ref[1] - aide, ref[2] - aide)
    return [ref, pilote, deux, equil, ressort_aide]


# --------------------------------------------------------------- textes ---
T = {
    "fr": {
        "ref": "Référence : une soupape", "pil": "(a) Pilote : petite soupape d'abord",
        "deux": "(b) Deux soupapes côte à côte", "equ": "(c) Soupape équilibrée",
        "aide": "(d) Ressort d'aide au bouton", "bar": "(e) Effort au bouton (g)",
        "soufflet": "air du soufflet (p)", "atm": "air extérieur", "table": "table d'harmonie",
        "ressort": "ressort", "bouton": "bouton", "axe": "axe",
        "ref_txt": "Au tiré, la pression plaque la soupape :\nbouton = (F0 + p·A) × r / η",
        "pil_txt": "Le levier lève d'abord la petite soupape\n(6 × 6 mm) : la chambre s'égalise,\npuis il prend la grande. L'à-coup du\ntiré disparaît, F0 reste.",
        "deux_txt": "2 trous de 150 mm² : même aire,\nmême ressort total. Aucun gain.",
        "equ_txt": "Deux portées sur la même tige, aires égales :\nla pression ouvre l'une et ferme l'autre.\nLes poussées s'annulent ; il reste\nle ressort d'étanchéité (0,3 à 0,5 N).",
        "aide_txt": "Une force constante tire le bouton\nvers le bas : elle retire autant\nà l'appui qu'au retour.",
        "ouvre": "ouvre", "ferme": "ferme", "plaque": "p·A plaque",
        "aide_f": "aide", "retour_f": "retour",
        "cats": ["référence", "pilote", "deux\nsoupapes", "équilibrée", "ressort\nd'aide"],
        "s1": "décollement (tiré)", "s2": "mi-course", "s3": "retour au poussé 3 kPa",
        "but": "but 80-100 g", "min_retour": "retour mini ~35 g",
        "titre": "Les compensations de la section « effort au bouton » (trou 20 × 15 mm, r = 1)",
    },
    "en": {
        "ref": "Reference: one pallet", "pil": "(a) Pilot: small pallet first",
        "deux": "(b) Two pallets side by side", "equ": "(c) Balanced pallet",
        "aide": "(d) Helper spring at the button", "bar": "(e) Force at the button (g)",
        "soufflet": "bellows air (p)", "atm": "outside air", "table": "soundboard",
        "ressort": "spring", "bouton": "button", "axe": "pivot",
        "ref_txt": "On the draw, pressure clamps the pallet:\nbutton = (F0 + p·A) × r / η",
        "pil_txt": "The lever first lifts the small pallet\n(6 × 6 mm): the chamber equalises,\nthen it takes the big one. The draw\n'pluck' disappears, F0 remains.",
        "deux_txt": "2 holes of 150 mm²: same area,\nsame total spring. No gain.",
        "equ_txt": "Two seats on the same stem, equal areas:\npressure opens one and closes the other.\nThe thrusts cancel; only the sealing\nspring remains (0.3 to 0.5 N).",
        "aide_txt": "A constant force pulls the button\ndown: it removes as much on the\nstroke as on the return.",
        "ouvre": "opens", "ferme": "closes", "plaque": "p·A clamps",
        "aide_f": "helper", "retour_f": "return",
        "cats": ["reference", "pilot", "two\npallets", "balanced", "helper\nspring"],
        "s1": "lift-off (draw)", "s2": "mid-stroke", "s3": "return at 3 kPa push",
        "but": "target 80-100 g", "min_retour": "min. return ~35 g",
        "titre": "Compensations for the button force (hole 20 × 15 mm, r = 1)",
    },
}

GRIS, BOIS, PEAU, AIR, ROUGE, BLEU, VERT = "#9aa0a6", "#c8a26b", "#5b4636", "#dcecf7", "#c0392b", "#1f6fb2", "#2e7d32"


def fleche(ax, x0, y0, x1, y1, c, lw=2.2):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=14, color=c, lw=lw))


def ressort(ax, x, y0, y1, n=6, w=0.35):
    ys = [y0 + (y1 - y0) * i / (2 * n) for i in range(2 * n + 1)]
    xs = [x + (w if i % 2 else -w) * (0 < i < 2 * n) for i in range(2 * n + 1)]
    ax.plot(xs, ys, color="#555", lw=1.3)


def socle(ax, t, trous):
    """Chambre du soufflet en bas, table d'harmonie percée de trous, air au-dessus."""
    ax.add_patch(Rectangle((0, 0), 10, 2.4, color=AIR, zorder=0))
    ax.text(0.2, 0.3, t["soufflet"], fontsize=7, color=BLEU)
    ax.text(0.2, 7.5, t["atm"], fontsize=7, color="#666")
    x = 0
    for (a, b) in trous:
        ax.add_patch(Rectangle((x, 2.4), a - x, 0.6, color=BOIS))
        x = b
    ax.add_patch(Rectangle((x, 2.4), 10 - x, 0.6, color=BOIS))
    ax.text(9.8, 2.55, t["table"], fontsize=6.5, ha="right", color="#5a3d1a")


def levier(ax, x_soup, y, t, x_axe=6.3, x_bout=9.4):
    ax.plot([x_soup, x_bout], [y, y], color="#333", lw=2.5)
    ax.add_patch(Polygon([[x_axe, y - 0.05], [x_axe - 0.25, y - 0.55], [x_axe + 0.25, y - 0.55]], color="#333"))
    ax.text(x_axe, y - 0.95, t["axe"], fontsize=6.5, ha="center")
    ax.add_patch(Rectangle((x_bout - 0.25, y), 0.5, 0.9, color="#777"))
    ax.text(x_bout, y + 1.05, t["bouton"], fontsize=6.5, ha="center")


def soupape(ax, x0, x1, y=3.0, h=0.45):
    ax.add_patch(Rectangle((x0, y), x1 - x0, 0.12, color=PEAU))
    ax.add_patch(Rectangle((x0, y + 0.12), x1 - x0, h, color="#3b3b3b"))


def panneau(ax, titre, texte):
    ax.set_xlim(0, 10); ax.set_ylim(0, 8.2); ax.axis("off")
    ax.set_title(titre, fontsize=9, loc="left", fontweight="bold")
    ax.text(0.15, -1.55, texte, fontsize=7, va="top")


def figure(langue):
    t = T[langue]
    fig = plt.figure(figsize=(12, 8.6))
    gs = fig.add_gridspec(2, 3, hspace=0.75, wspace=0.18)
    axs = [fig.add_subplot(gs[i // 3, i % 3]) for i in range(6)]

    # Référence
    ax = axs[0]; panneau(ax, t["ref"], t["ref_txt"]); socle(ax, t, [(2.0, 4.5)])
    soupape(ax, 1.6, 4.9); levier(ax, 3.25, 5.2, t)
    ax.plot([3.25, 3.25], [3.57, 5.2], color="#333", lw=1.5)
    ressort(ax, 2.2, 6.6, 3.57); ax.text(1.0, 6.7, t["ressort"] + " F0", fontsize=6.5)
    fleche(ax, 3.9, 4.4, 3.9, 3.6, ROUGE); ax.text(4.05, 4.1, t["plaque"], fontsize=6.5, color=ROUGE)

    # (a) pilote
    ax = axs[1]; panneau(ax, t["pil"], t["pil_txt"]); socle(ax, t, [(2.0, 4.5)])
    soupape(ax, 1.6, 4.9)
    ax.add_patch(Rectangle((3.0, 3.57), 0.6, 0.12, color="white"))       # petit trou dans la grande soupape
    soupape(ax, 2.85, 3.75, y=3.69, h=0.25)                              # petite soupape
    levier(ax, 3.3, 5.6, t)
    ax.plot([3.3, 3.3], [3.94, 5.6], color="#333", lw=1.5)               # tige vers la petite soupape
    ax.plot([2.3, 2.3, 4.3, 4.3], [4.5, 4.75, 4.75, 4.5], color=VERT, lw=1.6)   # crochet à jeu (lost motion)
    ax.text(4.45, 4.65, "1", fontsize=8, color=VERT, fontweight="bold")
    ax.text(3.45, 4.15, "2", fontsize=8, color=VERT, fontweight="bold")
    fleche(ax, 3.3, 2.0, 3.3, 3.5, BLEU, lw=1.6)

    # (b) deux soupapes
    ax = axs[2]; panneau(ax, t["deux"], t["deux_txt"]); socle(ax, t, [(1.0, 2.6), (3.4, 5.0)])
    soupape(ax, 0.7, 2.9); soupape(ax, 3.1, 5.3); levier(ax, 1.8, 5.2, t)
    ax.plot([1.8, 1.8], [3.57, 5.2], color="#333", lw=1.5); ax.plot([4.2, 4.2], [3.57, 5.2], color="#333", lw=1.5)
    ressort(ax, 3.0, 6.6, 5.2); fleche(ax, 1.4, 4.4, 1.4, 3.6, ROUGE); fleche(ax, 3.8, 4.4, 3.8, 3.6, ROUGE)

    # (c) équilibrée : cavité au soufflet entre deux plaques, deux disques sur une tige
    ax = axs[3]; panneau(ax, t["equ"], t["equ_txt"])
    ax.set_xlim(0, 10); ax.set_ylim(0, 8.2)
    ax.add_patch(Rectangle((0.8, 1.6), 5.6, 2.6, color=AIR))
    ax.text(0.95, 1.75, t["soufflet"], fontsize=7, color=BLEU)
    ax.text(0.2, 7.5, t["atm"], fontsize=7, color="#666")
    for y in (4.2, 1.0):                                                   # plaques supérieure et inférieure
        ax.add_patch(Rectangle((0.8, y), 2.1, 0.6, color=BOIS)); ax.add_patch(Rectangle((4.1, y), 2.3, 0.6, color=BOIS))
    ax.plot([3.5, 3.5], [1.9, 6.0], color="#333", lw=2)                    # tige
    soupape(ax, 2.5, 4.5, y=4.8, h=0.35)                                   # disque haut, sur la plaque haute
    soupape(ax, 2.5, 4.5, y=1.6, h=0.35)                                   # disque bas, dans la cavité, sur la plaque basse
    fleche(ax, 2.2, 3.4, 2.2, 4.9, VERT); ax.text(1.0, 3.8, t["ouvre"], fontsize=7, color=VERT)
    fleche(ax, 4.9, 3.8, 4.9, 2.1, ROUGE); ax.text(5.05, 3.0, t["ferme"], fontsize=7, color=ROUGE)
    levier(ax, 3.5, 6.0, t, x_axe=6.6, x_bout=9.4)
    ax.text(0.9, 0.35, "A haut = A bas", fontsize=7)

    # (d) ressort d'aide au bouton
    ax = axs[4]; panneau(ax, t["aide"], t["aide_txt"]); socle(ax, t, [(2.0, 4.5)])
    soupape(ax, 1.6, 4.9); levier(ax, 3.25, 5.2, t)
    ax.plot([3.25, 3.25], [3.57, 5.2], color="#333", lw=1.5); ressort(ax, 2.2, 6.6, 3.57)
    ressort(ax, 9.4, 5.2, 3.4, n=4, w=0.25); ax.plot([8.9, 9.9], [3.4, 3.4], color="#333", lw=2)
    fleche(ax, 8.7, 5.9, 8.7, 4.9, VERT); ax.text(7.5, 6.0, t["aide_f"], fontsize=7, color=VERT)

    # (e) comparaison chiffrée
    ax = axs[5]; ax.set_title(t["bar"], fontsize=9, loc="left", fontweight="bold")
    vals = efforts(); n = len(vals); w = 0.26
    for j, (lab, col) in enumerate(((t["s1"], ROUGE), (t["s2"], BLEU), (t["s3"], VERT))):
        xs = [i + (j - 1) * w for i in range(n)]
        ys = [v[j] for v in vals]
        ax.bar(xs, ys, w, color=col, label=lab)
        for x, y in zip(xs, ys):
            ax.text(x, y + 4, f"{y:.0f}", ha="center", fontsize=6)
    ax.axhspan(80, 100, color="#f1c40f", alpha=0.25, label=t["but"])
    ax.axhline(35, color=VERT, ls="--", lw=1, label=t["min_retour"])
    ax.set_xticks(range(n)); ax.set_xticklabels(t["cats"], fontsize=7)
    ax.set_ylim(0, 330); ax.tick_params(axis="y", labelsize=7)
    ax.legend(fontsize=6, loc="upper center", ncol=2, frameon=False)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    fig.suptitle(t["titre"], fontsize=11, fontweight="bold")
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(SORTIE, f"mecanique_compensations_{langue}.{ext}"), dpi=200, bbox_inches="tight")
    plt.close(fig)


TIROIR = {
    "fr": {"t1": "Effet tiroir : une tige poussée de travers dans son guide", "t2": "Facteur d'effort",
           "guide": "guide (L)", "tige": "tige", "f": "F (pion)", "e": "e", "n": "N", "mu": "frottement µN",
           "x": "excentrement / longueur guidée  (e / L)", "y": "effort à fournir / effort utile",
           "coince": "coince", "v5": "v5 : PLA, e = 5 mm, L = 8 mm",
           "txt": "F décalée de e : la tige se met en biais et s'appuie aux deux bouts du guide\n(N = F·e/L). Le frottement 2µN s'oppose : effort × 1/(1 − 2µe/L)."},
    "en": {"t1": "Drawer effect: a rod pushed off-axis in its guide", "t2": "Force factor",
           "guide": "guide (L)", "tige": "rod", "f": "F (pin)", "e": "e", "n": "N", "mu": "friction µN",
           "x": "offset / guided length  (e / L)", "y": "force needed / useful force",
           "coince": "jams", "v5": "v5: PLA, e = 5 mm, L = 8 mm",
           "txt": "F offset by e: the rod tilts and bears at both ends of the guide\n(N = F·e/L). Friction 2µN opposes it: force × 1/(1 − 2µe/L)."},
}


def figure_tiroir(langue):
    t = TIROIR[langue]
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1, 1.2]})
    a.set_xlim(0, 10); a.set_ylim(0, 8); a.axis("off"); a.set_title(t["t1"], fontsize=9, loc="left", fontweight="bold")
    a.add_patch(Rectangle((3.2, 2.0), 0.9, 4.0, color=BOIS)); a.add_patch(Rectangle((5.0, 2.0), 0.9, 4.0, color=BOIS))
    a.text(6.1, 4.0, t["guide"], fontsize=7)
    a.add_patch(Polygon([[4.15, 0.5], [4.55, 0.5], [4.95, 7.5], [4.55, 7.5]], color="#555"))   # tige légèrement en biais
    a.text(4.6, 7.65, t["tige"], fontsize=7, ha="center")
    a.plot([4.75, 6.8], [6.9, 6.9], color="#333", lw=2)                                       # pion excentré
    fleche(a, 6.8, 7.9, 6.8, 6.95, ROUGE); a.text(6.95, 7.5, t["f"], fontsize=7, color=ROUGE)
    a.annotate("", (4.75, 6.6), (6.8, 6.6), arrowprops=dict(arrowstyle="<->", lw=1)); a.text(5.7, 6.15, t["e"], fontsize=7)
    fleche(a, 3.0, 5.6, 4.0, 5.6, BLEU); fleche(a, 6.6, 2.4, 5.1, 2.4, BLEU)
    a.text(1.9, 5.5, t["n"], fontsize=8, color=BLEU); a.text(6.7, 2.3, t["n"], fontsize=8, color=BLEU)
    a.text(0.2, 0.0, t["txt"], fontsize=7, va="top")
    import numpy as np
    x = np.linspace(0, 1.4, 300)
    for mu, c in ((0.1, VERT), (0.2, "#7fb069"), (0.3, "#e67e22"), (0.4, ROUGE), (0.5, "#8e44ad")):
        d = 1 - 2 * mu * x
        y = np.where(d > 0.05, 1 / np.clip(d, 0.05, None), np.nan)
        b.plot(x, y, color=c, lw=1.8, label=f"µ = {mu}")
    b.axvline(5 / 8, color="#333", ls=":", lw=1); b.text(5 / 8 + 0.02, 4.6, t["v5"], fontsize=7)
    b.set_ylim(1, 5); b.set_xlim(0, 1.4); b.set_xlabel(t["x"], fontsize=8); b.set_ylabel(t["y"], fontsize=8)
    b.set_title(t["t2"], fontsize=9, loc="left", fontweight="bold"); b.legend(fontsize=7, frameon=False)
    b.tick_params(labelsize=7)
    for s_ in ("top", "right"):
        b.spines[s_].set_visible(False)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(SORTIE, f"mecanique_tiroir_{langue}.{ext}"), dpi=200, bbox_inches="tight")
    plt.close(fig)


def main():
    os.makedirs(SORTIE, exist_ok=True)
    for langue in ("fr", "en"):
        figure(langue)
        figure_tiroir(langue)
    v = efforts()
    print("Efforts au bouton (g) : décollement / mi-course / retour")
    for nom, e in zip(T["fr"]["cats"], v):
        print(f"  {nom.replace(chr(10), ' '):12s} {e[0]:5.0f} {e[1]:5.0f} {e[2]:5.0f}")
    print("Figures :", os.path.abspath(SORTIE))


if __name__ == "__main__":
    sys.exit(main())

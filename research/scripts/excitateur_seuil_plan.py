"""Seuil de démarrage selon la note, nouvel excitateur (air_mass_reed) : plan 2^6.

Question de l'audit (11/11/2026) : de 100 à 900 Hz, le seuil s'étale-t-il sur
une décade (comme un accordéon réel, ~100 à 1000 Pa) ou sur trois (ancien
modèle : 1,8 Pa à 102 Hz, 1781 Pa à 880 Hz) ?

Aucune valeur de réglage n'est mesurée sur une anche d'Ewen : on ne cale rien,
on BALAYE. Lames d'acier uniformes accordées par leur longueur (`languette`,
Euler-Bernoulli exact), quatre notes (100, 200, 440, 900 Hz), six facteurs à
deux niveaux en plan complet (64 réglages x 4 notes) :

  A levée à 440 Hz        0,2 / 0,5 mm
  B loi de levée          levée ∝ (L/L440)^n, n = 0 / 1
  C jeu a                 0,03 / 0,14 mm
  D amortissement ζ       0,002 / 0,006
  E perte au clapet K_p   35 / 150
  F épaisseur de lame     0,2 / 0,4 mm
  (fixes : largeur 3,5 mm, K_r = 8, d = 0,5 √(S/π), S_c de l'article)

Réponses : décades d'étalement log10(p_th(900)/p_th(100)) et log10 p_th(440).
Seuil = stabilité linéaire de l'équilibre (bifurcation de Hopf).

    python research/scripts/excitateur_seuil_plan.py [sortie.csv]
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from banc_recherche.air_mass_reed import steel_family  # noqa: E402
from banc_recherche.doe_analysis import design, model as doe_model, summary  # noqa: E402

NOTES = (100.0, 200.0, 440.0, 900.0)
FACTEURS = dict(levee440=(0.2e-3, 0.5e-3), n_levee=(0.0, 1.0), jeu=(0.03e-3, 0.14e-3),
                zeta=(0.002, 0.006), K_p=(35.0, 150.0), epaisseur=(0.2e-3, 0.4e-3))


def anche(f, levee440, n_levee, jeu, zeta, K_p, epaisseur):
    return steel_family(f, lift_440_m=levee440, lift_exponent=n_levee, gap_m=jeu,
                        zeta=zeta, K_p=K_p, thickness_m=epaisseur)


def plan():
    codes = design.full_factorial(len(FACTEURS))
    lignes = []
    for c in codes:
        reg = {k: (v[0] if ci < 0 else v[1]) for (k, v), ci in zip(FACTEURS.items(), c)}
        seuils = []
        for f in NOTES:
            pth = anche(f, **reg).hopf_threshold(p_lo=0.1, p_hi=1e5, n_scan=70)
            seuils.append(float('nan') if pth is None else pth)
        lignes.append(dict(**reg, **{f"p_{int(f)}": s for f, s in zip(NOTES, seuils)}))
    return lignes


def main(out=None):
    lignes = plan()
    if out:
        with open(out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(lignes[0]))
            w.writeheader()
            w.writerows(lignes)
    p100 = np.array([r["p_100"] for r in lignes])
    p900 = np.array([r["p_900"] for r in lignes])
    p440 = np.array([r["p_440"] for r in lignes])
    ok = np.isfinite(p100) & np.isfinite(p900)
    dec = np.log10(p900[ok] / p100[ok])
    print(f"réglages : {len(lignes)} ; seuil trouvé aux deux bouts : {ok.sum()}")
    print(f"décades 100->900 Hz : min {dec.min():.2f}  médiane {np.median(dec):.2f}  max {dec.max():.2f}")
    print(f"p_th(440) : min {np.nanmin(p440):.0f}  médiane {np.nanmedian(p440):.0f}  max {np.nanmax(p440):.0f} Pa")
    for nm, y in (("décades", np.log10(p900 / p100)), ("log10 p_th(440)", np.log10(p440))):
        sel = np.isfinite(y)
        F = {k: np.array([r[k] for r in lignes])[sel] for k in FACTEURS}
        res = doe_model.fit(F, y[sel], interactions=False)
        print(f"\nRéponse : {nm}")
        print(summary(res))
    return lignes


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)

"""Écart en cents entre la note jouée et la lame, nouvel excitateur, sans `_accorder`.

L'ancienne voix (`live._accorder`) retouche la géométrie jusqu'à tomber sur la
note : 1 à 40 cents d'écart avant retouche. Ici on ne retouche rien : la lame
est calculée par `languette` (Euler-Bernoulli exact, mode 1), la note jouée
sort du modèle à masse d'air (`air_mass_reed.played_note`).

Lames : la seule lame réelle de la banque (R12-grave, matrix.txt d'Ewen 2020,
67,4 Hz) et des lames d'acier uniformes NOMINALES de 110 à 1760 Hz
(`steel_family`, 0,3 x 3,5 mm). Réglage d'écoulement et sommier jamais
mesurés : plan 2^(7-1) (résolution VII, G = ABCDEF) sur chaque note
(64 réglages), aucun calage.

  A loi de levée     0,3 mm constante / 0,3 mm à 440 Hz et ∝ longueur
  B jeu a            0,03 / 0,14 mm
  C ζ                0,002 / 0,006
  D K_p              35 / 150
  E pression p0      500 / 1500 Pa
  F section de chambre S_c   celle de l'article (Do4) / ∝ longueur de lame
  G masse d'air d = d_coef √(S/π)   d_coef 0,5 (article, calé sur Ricot) / 1,0

    python research/scripts/excitateur_justesse_plan.py [sortie.csv]
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from banc_recherche.air_mass_reed import (AirMassReedModel, from_languette,  # noqa: E402
                                          steel_family)
from banc_recherche.banque_anches import importer  # noqa: E402
from banc_recherche.doe_analysis import design, model as doe_model, summary  # noqa: E402

NOTES_NOMINALES = (110.0, 220.0, 440.0, 880.0, 1760.0)
FACTEURS = dict(n_levee=(0.0, 1.0), jeu=(0.03e-3, 0.14e-3), zeta=(0.002, 0.006),
                K_p=(35.0, 150.0), p0=(500.0, 1500.0), loi_chambre=(0.0, 1.0),
                d_coef=(0.5, 1.0))
SC_C4, L_C4 = 14.8e-3 * 14.6e-3, 32.8e-3


def _sc(L, loi_chambre):
    return SC_C4 * (L / L_C4) ** loi_chambre


def r12_grave(jeu, zeta, K_p, loi_chambre=0.0, d_coef=0.5, n_levee=0.0):
    """La lame réelle R12-grave ; levée nominale de la banque (0,413 mm, à mesurer).
    `n_levee` est sans objet ici (levée de la banque)."""
    anches, _ = importer(RACINE / "fem" / "anche" / "banque_anches.csv")
    a = [x for x in anches if x.id == "R12-grave"][0]
    lang = a.languette()
    p = from_languette(lang, gap_m=jeu, x_rest_m=float(a.valeur("levee_mm")) * 1e-3,
                       zeta=zeta, K_p=K_p, chamber_section_m2=_sc(lang.L, loi_chambre),
                       d_coef=d_coef)
    return AirMassReedModel(p)


def modele(note, n_levee, jeu, zeta, K_p, loi_chambre=0.0, d_coef=0.5):
    if note == "R12-grave":
        return r12_grave(jeu, zeta, K_p, loi_chambre, d_coef)
    from banc_recherche.air_mass_reed import steel_length
    L = steel_length(float(note), 0.3e-3)
    return steel_family(float(note), lift_440_m=0.3e-3, lift_exponent=n_levee, gap_m=jeu,
                        zeta=zeta, K_p=K_p, chamber_section_m2=_sc(L, loi_chambre),
                        d_coef=d_coef)


def plan():
    codes = design.fractional_factorial(6, {6: (0, 1, 2, 3, 4, 5)})
    lignes = []
    for note in ("R12-grave",) + NOTES_NOMINALES:
        for c in codes:
            reg = {k: (v[0] if ci < 0 else v[1]) for (k, v), ci in zip(FACTEURS.items(), c)}
            p0 = reg.pop("p0")
            m = modele(note, **reg)
            r = m.played_note(p0, oversample=16)
            lignes.append(dict(note=note, f_lame=r["f_reed"], **reg, p0=p0, joue=int(r["plays"]),
                               f=r["f"], cents=r["cents"], amp_mm=r["amp"] * 1e3,
                               p_bas=r["band"][0], p_haut=r["band"][1], route=r["route"]))
    return lignes


def main(out=None):
    lignes = plan()
    if out:
        with open(out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(lignes[0]))
            w.writeheader()
            w.writerows(lignes)
    print("note        f_lame   joue/64   cents min  médiane  max")
    for note in ("R12-grave",) + NOTES_NOMINALES:
        sel = [r for r in lignes if r["note"] == note]
        c = np.array([r["cents"] for r in sel if r["joue"]])
        txt = (f"{np.min(c):7.1f} {np.median(c):7.1f} {np.max(c):7.1f}" if c.size else "  —")
        print(f"{str(note):10s} {sel[0]['f_lame']:8.2f}   {int(sum(r['joue'] for r in sel)):2d}/64   {txt}")
    ok = [r for r in lignes if r["joue"]]
    F = {k: np.array([r[k] for r in ok], float) for k in FACTEURS}
    res = doe_model.fit(F, np.array([r["cents"] for r in ok]), interactions=False)
    print("\nRéponse : cents (toutes notes qui jouent)")
    print(summary(res))
    return lignes


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)

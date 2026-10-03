"""Étude de la méthode, du maillage et du solveur pour l'impédance vue par la fente.

Chambre 1 du R12, fente de l'anche R12-grave (37,43 x 4,32 mm, plaque 0,83 mm).
Référence : le balayage harmonique de 70 fréquences, maille uniforme 2 mm (le calcul du
03/10/2026, `resultats/impedance_R12-grave.*`). Pour chaque variante : temps, pôles,
résidu a1 (donc volume effectif), masse d'air de la fente, écart de |Z| à la référence
sous 3 kHz (sous le 3e pôle), hors des +-3 % autour des pôles (là, un écart de fréquence
infime donne un écart de |Z| infini).

Usage : J:\\claude\\venv\\Scripts\\python.exe etude_impedance.py
Sortie : resultats/etude_impedance.csv
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import impedance_fente as imp  # noqa: E402

FENTE = (37.43, 4.319, 0.825)
VARIANTES = [
    ("rapide, maille uniforme 3 mm, direct", dict(h=3.0, solveur="direct")),
    ("rapide, maille uniforme 3 mm, itératif BiCGStab(l)+ILU1", dict(h=3.0, solveur="iteratif")),
    ("rapide, maille uniforme 2 mm, direct", dict(h=2.0, solveur="direct")),
    ("rapide, maille uniforme 2 mm, itératif BiCGStab(l)+ILU1", dict(h=2.0, solveur="iteratif")),
    ("rapide, maille adaptée 3 -> 0,8 mm, itératif", dict(h=3.0, h_fin=0.8, solveur="iteratif")),
    ("rapide, maille uniforme 1,2 mm, itératif", dict(h=1.2, solveur="iteratif")),
]
# Essayée le 03/10/2026 et écartée : maille adaptée 3 -> 0,5 mm, 139 561 nœuds, Umfpack
# n'a pas assez de mémoire (umf4num -1) ; la 3 -> 0,8 mm en direct a pris 737 s.


def main():
    ref = json.load(open(os.path.join(ICI, "resultats", "impedance_R12-grave.json"), encoding="utf-8"))
    z = np.loadtxt(os.path.join(ICI, "resultats", "impedance_R12-grave.csv"), delimiter=";", skiprows=1)
    f_ref, Z_ref = z[:, 0], z[:, 1] + 1j * z[:, 2]
    # comparaison sous 3 kHz (sous le 3e pôle, 3,6 kHz, que la référence ne résout pas),
    # hors des +-3 % autour des pôles
    loin = np.all([np.abs(f_ref / p - 1) > 0.03 for p in ref["poles_Hz"]], axis=0) & (f_ref <= 3000.0)
    lignes = [dict(variante="RÉFÉRENCE : balayage 70 fréquences, maille uniforme 2 mm, direct",
                   noeuds=ref["noeuds"], duree_s=round(ref["duree_s"], 1),
                   f1_Hz=round(ref["poles_Hz"][0], 2), f2_Hz=round(ref["poles_Hz"][1], 2),
                   V_eff_cm3=round(ref["reseau"]["V_eff_m3"] * 1e6, 3),
                   l_eff_trou_mm=round(ref["reseau"]["l_eff_trou_m"] * 1e3, 2),
                   L_fente=round(ref["ajustement"]["L_fente"], 2), ecart_Z_median_pct=0, ecart_Z_max_pct=0)]
    print(lignes[0], flush=True)
    for nom, kw in VARIANTES:
        t0 = time.time()
        try:
            res, f, Z = imp.calculer(1, *FENTE, etiquette="_etude_" + str(len(lignes)), **kw)
        except Exception as ex:                                       # noqa: BLE001
            lignes.append(dict(variante=nom, noeuds="", duree_s=round(time.time() - t0, 1), f1_Hz=f"échec : {ex}"))
            print(lignes[-1], flush=True)
            continue
        e = np.abs(Z[loin] - Z_ref[loin]) / np.abs(Z_ref[loin])
        r = res["reseau"]
        lignes.append(dict(variante=nom, noeuds=res["noeuds"], duree_s=round(res["duree_s"], 1),
                           f1_Hz=round(res["poles_Hz"][0], 2),
                           f2_Hz=round(res["poles_Hz"][1], 2) if len(res["poles_Hz"]) > 1 else "",
                           V_eff_cm3=round(r["V_eff_m3"] * 1e6, 3), l_eff_trou_mm=round(r["l_eff_trou_m"] * 1e3, 2),
                           L_fente=round(res["ajustement"]["L_fente"], 2),
                           ecart_Z_median_pct=round(100 * float(np.median(e)), 3),
                           ecart_Z_max_pct=round(100 * float(np.max(e)), 3)))
        print(lignes[-1], flush=True)
    ch = os.path.join(ICI, "resultats", "etude_impedance.csv")
    cles = []
    for l in lignes:
        cles += [k for k in l if k not in cles]
    with open(ch, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cles, delimiter=";")
        w.writeheader()
        w.writerows(lignes)
    print("->", ch)


if __name__ == "__main__":
    main()

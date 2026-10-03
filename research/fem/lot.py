"""Calculs Elmer en lot, avec cache : cotes -> maillage -> calcul -> résultat, en une commande.

Chaque calcul est rangé dans `J:\\claude\\calculs\\cache\\` sous l'empreinte de ses entrées
(`cache.py`) : relancer un plan ne recalcule que ce qui a changé.

Trois sortes de calculs :
- `chambre`   : modes propres de l'air d'une chambre du R12 (cotes modifiables), WaveSolver ;
- `impedance` : impédance vue par la fente (méthode rapide : pôles + 14 fréquences) ;
- `languette` : modes d'une languette (tronçons en mm), StressSolver.

Le plan est un fichier JSON :
    {"type": "chambre",
     "base": {"chambre": 6, "trou": [8, 25], "table": 8, "h": 2.0},
     "varier": {"trou": [[6, 25], [8, 25], [10, 25]], "table": [6, 8, 10]}}
-> le produit cartésien des valeurs de `varier` (ici 9 calculs). Sortie : un CSV.

Usage : J:\\claude\\venv\\Scripts\\python.exe lot.py plan.json [--sortie resultats/lot.csv]
"""
from __future__ import annotations

import argparse
import copy
import csv
import itertools
import json
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
sys.path.insert(0, os.path.join(ICI, "sommier"))
sys.path.insert(0, os.path.join(ICI, "anche"))
sys.path.insert(0, os.path.abspath(os.path.join(ICI, "..")))
import cache  # noqa: E402
import elmer_outils  # noqa: E402


def cotes_modifiees(table_chambres=None, pilotes=None):
    """Les cotes du sommier (sommier.py), avec des valeurs remplacées : `table_chambres`
    = {"ProfCase": {k: valeur}, ...}, `pilotes` = {"HauteurSommier": ...}."""
    from chambre_modes import cotes_sommier
    c = copy.deepcopy(cotes_sommier())
    for nom, valeurs in (table_chambres or {}).items():
        for k, v in valeurs.items():
            c["TABLE_R12"][nom][int(k) - 1] = float(v)
    c["PILOTES"].update(pilotes or {})
    return c


def chambre(chambre, trou=(8.0, 25.0), table=8.0, corr=0.85, h=2.0, n_modes=4, table_chambres=None,
            pilotes=None):
    """Modes propres de l'air de la chambre (Hz) et volumes, en cache."""
    import chambre_modes as cm

    def calcul():
        cotes = cotes_modifiees(table_chambres, pilotes)
        ch = cm.Chambre(chambre, cotes, trou=tuple(trou), table=table, corr_ext=corr)
        cle_dossier = cache.cle("chambre", entrees)
        dossier = os.path.join(elmer_outils.CALCULS, "lot", f"ch{chambre:02d}_{cle_dossier}")
        os.makedirs(dossier, exist_ok=True)
        g = cm.mailler(ch, os.path.join(dossier, "chambre.msh"), h=h)
        f = cm.elmer(dossier, n_modes)
        return dict(f_Hz=f, V_A_cm3=g["V_A_mm3"] / 1e3, V_B_cm3=g["V_B_mm3"] / 1e3,
                    V_cases_cm3=(g["V_A_mm3"] + g["V_B_mm3"]) / 1e3, noeuds=g["noeuds"])
    entrees = dict(chambre=chambre, trou=list(trou), table=table, corr=corr, h=h, n_modes=n_modes,
                   table_chambres=table_chambres or {}, pilotes=pilotes or {}, elmer=elmer_outils.version())
    return cache.en_cache("chambre", entrees, calcul)


def impedance(chambre, fente, plaque, trou=(8.0, 25.0), table=8.0, corr=0.85, h=2.0, h_fin=None,
              table_chambres=None, solveur="iteratif"):
    """Impédance vue par la fente (méthode rapide), en cache : pôles, résidus, réseau."""
    import impedance_fente as imp

    def calcul():
        res, f, Z = imp.calculer(chambre, fente[0], fente[1], plaque, etiquette="_lot_" + cache.cle("imp", entrees),
                                 trou=tuple(trou), table=table, corr=corr, h=h, h_fin=h_fin, solveur=solveur,
                                 cotes=cotes_modifiees(table_chambres))
        res["Z_f_Hz"], res["Z_re"], res["Z_im"] = list(f), list(Z.real), list(Z.imag)
        return res
    entrees = dict(chambre=chambre, fente=list(fente), plaque=plaque, trou=list(trou), table=table, corr=corr,
                   h=h, h_fin=h_fin, solveur=solveur, table_chambres=table_chambres or {},
                   elmer=elmer_outils.version())
    return cache.en_cache("impedance", entrees, calcul)


def languette(troncons, encastrement="pied", masses=()):
    """troncons : [[longueur, [b0, b1], [e0, e1], materiau], ...] en mm."""
    from banc_recherche.languette import Languette, Troncon
    from languette_modes import modes_elmer_cache
    lang = Languette([Troncon(t[0] * 1e-3, tuple(x * 1e-3 for x in t[1]), tuple(x * 1e-3 for x in t[2]),
                              t[3] if len(t) > 3 else "acier") for t in troncons],
                     masses=[(x * 1e-3, m * 1e-3) for x, m in masses])
    return modes_elmer_cache(lang, "lot", n_modes=6, encastrement=encastrement)


FONCTIONS = {"chambre": chambre, "impedance": impedance, "languette": languette}


def executer(plan):
    base = plan.get("base", {})
    varier = plan.get("varier", {})
    noms = list(varier)
    lignes = []
    for combo in itertools.product(*[varier[n] for n in noms]) if noms else [()]:
        args = dict(base, **dict(zip(noms, combo)))
        r = FONCTIONS[plan["type"]](**args)
        ligne = {k: json.dumps(v) if isinstance(v, (list, dict)) else v for k, v in args.items()}
        for k, v in r.items():
            if k.startswith("Z_") or k == "flexion" or k == "_entrees":
                continue
            ligne[k] = json.dumps(v) if isinstance(v, (list, dict)) else v
        lignes.append(ligne)
        print(ligne.get("_cache"), {k: ligne[k] for k in list(args)}, flush=True)
    return lignes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--sortie", default=os.path.join(ICI, "resultats", "lot.csv"))
    a = ap.parse_args(argv)
    lignes = executer(json.load(open(a.plan, encoding="utf-8")))
    os.makedirs(os.path.dirname(a.sortie), exist_ok=True)
    cles = []
    for l in lignes:
        cles += [k for k in l if k not in cles]
    with open(a.sortie, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cles, delimiter=";")
        w.writeheader()
        w.writerows(lignes)
    print("->", a.sortie)


if __name__ == "__main__":
    main()

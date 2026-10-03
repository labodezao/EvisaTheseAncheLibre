"""Optimisation des chambres du R12 (étape 6 du plan du sommier) : une PROPOSITION.

Le but, par chambre
-------------------
D'après l'étude du sommier (`seuils_cavite.py`, rapport du 03/10/2026), le seuil de
démarrage est le plus bas quand la résonance de la chambre f_H vaut 1,2 à 1,7 fois la note
de l'anche. Une chambre porte plusieurs notes (poussé, tiré) : on cherche f_H dans
l'intersection de leurs fenêtres, au centre (moyenne géométrique). Quand la fenêtre n'est
pas atteignable avec des cotes usinables (anches graves : il faudrait une chambre énorme ou
un trou minuscule), on veut f_H à au moins 50 cents des harmoniques 1 à 6 des notes, pour
qu'elle ne tire ni la justesse ni le timbre : si la chambre actuelle y est déjà, on n'y
touche pas ; sinon, le plus petit changement qui y parvient (à défaut, la plus grande marge). Le 2e mode (case A contre case B) est
vérifié par Elmer et comparé aux mêmes harmoniques.

Les variables et leurs bornes (HYPOTHÈSES à confirmer avec Ewen)
-----------------------------------------------------------------
- le trou de table : section S de 100 à 325 mm2 (largeur 4 à 13 mm le long du sommier, 25 mm
  en travers au plus, comme aujourd'hui), cotes au 0,5 mm. Le plancher de 100 mm2 évite
  d'étrangler l'air de l'anche (hypothèse : la moitié du trou actuel supposé) ;
- la longueur du trou (épaisseur de table, ou cheminée) : 4 à 12 mm, au 0,5 mm ;
- ProfCase (le volume de la case côté cloison) : de -1,5 à +3 mm autour de la cote
  actuelle, jamais sous 0,5 mm, au 0,25 mm. ATTENTION : la baisser réduit la place de
  l'anche intérieure et de sa soupape ;
- une cale au fond des cases A et B, de 0 à 6 mm (pièce rapportée : HYPOTHÈSE, la marge
  sous l'anche doit le permettre) ;
- LonCase n'est pas touchée (règle d'Ewen : la taille de l'anche plus une marge).
Coût d'un changement (pour préférer le plus petit) : |ln(S/S0)| + 0,5.|ln(L/L0)| + 0,3.|dProf| (mm).

La méthode
----------
1. Modèle rapide de f_H : formule de Helmholtz f = c/2pi.sqrt(S/(V.L_eff)), V = cases
   (calculé sur la géométrie de sommier.py), L_eff = longueur + kappa.rayon équivalent, kappa
   calé PAR CHAMBRE sur Elmer ; puis vérification par Elmer (modes propres, `lot.chambre`, en
   cache) et recalage de kappa, 3 itérations au plus.
2. Le gain : seuil de démarrage p_on de chaque note par `coupled_reeds` (lame d'acier
   uniforme accordée sur la note : les vraies anches ne sont pas encore mesurées), avec la
   chambre actuelle et la proposée.

Sorties : resultats/optimisation_r12.csv (tableau par chambre), resultats/proposition_cotes_R12.json
(ProfCase pour sommier.py, trou de table par chambre) et la commande `sommier.py --set`.
Rien n'est modifié dans ZW3D ni dans sommier.py.

Usage : J:\\claude\\venv\\Scripts\\python.exe optimisation_r12.py [--sans-seuil] [--chambres 6 12]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
sys.path.insert(0, os.path.dirname(ICI))
sys.path.insert(0, os.path.abspath(os.path.join(ICI, "..", "..")))
from chambre_modes import C_SON, Chambre, cotes_sommier  # noqa: E402

RESULTATS = os.path.join(ICI, "resultats")
FENETRE = (1.2, 1.7)
TROU0, TABLE0, CORR = (8.0, 25.0), 8.0, 0.85
# S_MIN : un trou trop petit étrangle l'air que l'anche consomme (100 mm2 : HYPOTHÈSE, la
# moitié du trou actuel supposé de 8 x 25 mm ; à confirmer par le débit mesuré au banc).
S_MIN, S_MAX, HX_MIN, HX_MAX, HY_MAX = 100.0, 325.0, 4.0, 13.0, 25.0
N_HARM = 6            # harmoniques « gênants » : 1 à 6
MARGE_VISEE = 50.0    # cents
L_MIN, L_MAX = 4.0, 12.0
D_PROF = (-1.5, 3.0)
# Cale : le fond des cases A et B relevé de 0 à 6 mm (HYPOTHÈSE : la marge sous l'anche le
# permet ; LonCase de sommier.py n'est pas changée, la cale est une pièce rapportée).
CALES = (0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0)


def lire_notes(chemin=os.path.join(ICI, "notes_r12.csv")):
    from banc_recherche.banque_anches import note_hz
    out = {}
    for l in open(chemin, encoding="utf-8"):
        if l.startswith("#") or l.startswith("chambre") or not l.strip():
            continue
        k, notes, source = (l.rstrip("\n").split(";") + ["", ""])[:3]
        out[int(k)] = dict(noms=notes.split(), f=[note_hz(n) for n in notes.split()], source=source)
    return out


def volume_cases_mm3(ch: Chambre):
    """Volume des cases A + B (mm3), intégré sur la géométrie de sommier.py (comme Gmsh)."""
    V = 0.0
    for nom, xa, xb, zf, yi, ye in ch.demi_cases():
        z = np.linspace(zf, ch.H, 401)
        V += (xb - xa) * abs(np.trapezoid([ye(t) - yi(t) for t in z], z))
    return V


def cotes_avec(cotes, k, prof):
    import copy
    c = copy.deepcopy(cotes)
    c["TABLE_R12"]["ProfCase"][k - 1] = prof
    return c


def trou_de(S):
    """Section (mm2) -> (hx, hy) usinables, au 0,5 mm : 25 mm en travers tant que possible."""
    if S >= HX_MIN * HY_MAX:
        return round(min(S / HY_MAX, HX_MAX) * 2) / 2, HY_MAX
    return HX_MIN, round(max(S / HX_MIN, 5.0) * 2) / 2


def f_helmholtz(S_mm2, V_mm3, L_mm, kappa):
    r = math.sqrt(S_mm2 / math.pi)
    return C_SON / (2 * math.pi) * math.sqrt(S_mm2 * 1e-6 / (V_mm3 * 1e-9 * (L_mm + kappa * r) * 1e-3))


def kappa_de(f, S_mm2, V_mm3, L_mm):
    r = math.sqrt(S_mm2 / math.pi)
    L_eff = S_mm2 * 1e-6 * C_SON ** 2 / (V_mm3 * 1e-9 * (2 * math.pi * f) ** 2) * 1e3
    return (L_eff - L_mm) / r


def marge_harmoniques(f, notes, n_max=N_HARM):
    """Distance (cents) de f à l'harmonique le plus proche des notes (n = 1..n_max)."""
    return min(abs(1200 * math.log2(f / (n * fn))) for fn in notes for n in range(1, n_max + 1))


def cout(S, L, dprof, cale=0.0, S0=TROU0[0] * TROU0[1]):
    return abs(math.log(S / S0)) + 0.5 * abs(math.log(L / TABLE0)) + 0.3 * abs(dprof) + 0.15 * cale


def table_chambre(cotes, k, prof, cale):
    """Les cotes de la chambre k à passer à lot.chambre (ProfCase, et la cale vue comme un
    fond relevé : la profondeur d'air des cases A et B diminue de `cale` mm)."""
    t = {}
    if prof != cotes["TABLE_R12"]["ProfCase"][k - 1]:
        t["ProfCase"] = {k: prof}
    if cale:
        t["LonCaseA"] = {k: cotes["TABLE_R12"]["LonCaseA"][k - 1] - cale}
        t["LonCaseB"] = {k: cotes["TABLE_R12"]["LonCaseB"][k - 1] - cale}
    return t


def cotes_chambre(cotes, k, prof, cale):
    import copy
    c = copy.deepcopy(cotes)
    for nom, d in table_chambre(cotes, k, prof, cale).items():
        c["TABLE_R12"][nom][k - 1] = d[k]
    return c


def resoudre_S(cible, V, L, kappa):
    """Section (mm2) qui donne f_H = cible, ou None hors de [S_MIN, S_MAX]."""
    a, b = S_MIN, S_MAX
    if not (f_helmholtz(a, V, L, kappa) <= cible <= f_helmholtz(b, V, L, kappa)):
        return None
    for _ in range(60):
        m = math.sqrt(a * b)
        if f_helmholtz(m, V, L, kappa) < cible:
            a = m
        else:
            b = m
    return math.sqrt(a * b)


def chercher(k, cotes, notes, kappa, f_actuel):
    """Le meilleur réglage (S, L, ProfCase, cale) au sens du modèle rapide. Trois buts :
    1. « fenêtre » : f_H dans [1,2 ; 1,7] x chaque note (centre de l'intersection) ;
    2. « note haute » : une note est au-dessus de f_H / 1,2 (elle ne démarre pas ou mal) :
       f_H visée à 1,25 x la note la plus haute, ou la plus haute possible ;
    3. « harmoniques » : sinon, à au moins 50 cents des harmoniques 1 à 6, plus petit changement."""
    prof0 = cotes["TABLE_R12"]["ProfCase"][k - 1]
    lo, hi = FENETRE[0] * max(notes), FENETRE[1] * min(notes)
    a_risque = [f for f in notes if f_actuel / f < FENETRE[0]]
    geos = []
    for prof in np.arange(max(0.5, prof0 + D_PROF[0]), prof0 + D_PROF[1] + 1e-9, 0.25):
        for cale in CALES:
            try:
                V = volume_cases_mm3(Chambre(k, cotes_chambre(cotes, k, float(prof), cale), trou=TROU0,
                                             table=TABLE0, corr_ext=CORR))
            except Exception:                                      # noqa: BLE001  (géométrie impossible)
                continue
            if V > 0:
                geos.append((float(prof), float(cale), V))

    def essai(cible):
        cands = []
        for prof, cale, V in geos:
            for L in np.arange(L_MIN, L_MAX + 1e-9, 0.5):
                S = resoudre_S(cible, V, L, kappa)
                if S is None:
                    continue
                hx, hy = trou_de(S)
                S = hx * hy
                fH = f_helmholtz(S, V, L, kappa)
                cands.append((cout(S, L, prof - prof0, cale),
                              dict(prof=prof, cale=cale, L=float(L), hx=hx, hy=hy, S=S, V=V, fH=fH,
                                   marge=marge_harmoniques(fH, notes))))
        return min(cands, key=lambda c: c[0])[1] if cands else None

    best, but = None, None
    if lo < hi:
        best = essai(math.sqrt(lo * hi))
        but = f"fenêtre {lo:.0f}-{hi:.0f} Hz (cible {math.sqrt(lo * hi):.0f})" if best else None
    if best is None and a_risque:
        cible = 1.25 * max(a_risque)
        best = essai(cible)
        but = f"note haute {max(a_risque):.0f} Hz : f_H visée {cible:.0f} Hz (1,25 x)" if best else None
        if best is None:                                           # au plus haut possible
            cands = []
            for prof, cale, V in geos:
                for L in (L_MIN,):
                    hx, hy = trou_de(S_MAX)
                    fH = f_helmholtz(hx * hy, V, L, kappa)
                    cands.append((-fH + 1e-3 * cout(hx * hy, L, prof - prof0, cale),
                                  dict(prof=prof, cale=cale, L=float(L), hx=hx, hy=hy, S=hx * hy, V=V, fH=fH,
                                       marge=marge_harmoniques(fH, notes))))
            best = min(cands, key=lambda c: c[0])[1]
            but = (f"note haute {max(a_risque):.0f} Hz : f_H visée {cible:.0f} Hz HORS D'ATTEINTE "
                   f"(le plus haut possible ; il faudrait une chambre plus petite)")
    if best is None:
        cands = []
        for prof, cale, V in geos:
            for L in np.arange(L_MIN, L_MAX + 1e-9, 0.5):
                for S in list(np.geomspace(S_MIN, S_MAX, 40)) + [TROU0[0] * TROU0[1]]:
                    hx, hy = trou_de(S)
                    S = hx * hy
                    fH = f_helmholtz(S, V, L, kappa)
                    mg = marge_harmoniques(fH, notes)
                    c = cout(S, L, prof - prof0, cale)
                    rang = c if mg >= MARGE_VISEE else 100.0 - mg / 10 + 0.01 * c
                    cands.append((rang, dict(prof=prof, cale=cale, L=float(L), hx=hx, hy=hy, S=S, V=V, fH=fH,
                                             marge=mg)))
        best = min(cands, key=lambda c: c[0])[1]
        but = ((f"fenêtre {lo:.0f}-{hi:.0f} Hz hors d'atteinte" if lo < hi else "pas de fenêtre commune")
               + " : loin des harmoniques 1 à 6")
    best["but"] = but
    return best


def elmer_f(k, cotes, prof, trou, L, cale=0.0):
    import lot
    t = table_chambre(cotes, k, prof, cale)
    r = lot.chambre(k, trou=list(trou), table=L, corr=CORR, h=2.0, table_chambres=t or None)
    return r["f_Hz"][0], r["f_Hz"][1], r


def seuil(f_note, V_mm3, S_mm2, L_mm, kappa):
    from seuils_cavite import modele, seuils
    r = math.sqrt(S_mm2 / math.pi)
    m = modele(f_note, V_mm3 * 1e-9, S_mm2 * 1e-6, (L_mm + kappa * r) * 1e-3, "pousser")
    p_on, f_on, _ = seuils(m)
    return p_on


def optimiser(k, cotes, notes, avec_seuil=True):
    t0 = time.time()
    prof0 = cotes["TABLE_R12"]["ProfCase"][k - 1]
    ch0 = Chambre(k, cotes, trou=TROU0, table=TABLE0, corr_ext=CORR)
    V0 = volume_cases_mm3(ch0)
    S0 = TROU0[0] * TROU0[1]
    f1_0, f2_0, _ = elmer_f(k, cotes, prof0, TROU0, TABLE0)
    kappa = kappa_de(f1_0, S0, V0, TABLE0)
    best = None
    for it in range(3):                                      # kappa recalé par Elmer sur la proposition
        best = chercher(k, cotes, notes["f"], kappa, f1_0)
        if best is None:
            break
        f1_e, f2_e, _ = elmer_f(k, cotes, best["prof"], (best["hx"], best["hy"]), best["L"], best["cale"])
        k_new = kappa_de(f1_e, best["S"], best["V"], best["L"])
        best.update(f1_elmer=f1_e, f2_elmer=f2_e, iterations=it + 1)
        if abs(k_new - kappa) < 0.02:
            break
        kappa = k_new
    ligne = dict(chambre=k, notes=" ".join(notes["noms"]),
                 notes_Hz=" ".join(f"{x:.1f}" for x in notes["f"]), source_notes=notes["source"],
                 actuel_trou_mm=f"{TROU0[0]:g} x {TROU0[1]:g}", actuel_longueur_trou_mm=TABLE0, actuel_ProfCase_mm=prof0,
                 actuel_V_cases_cm3=round(V0 / 1e3, 3), actuel_fH_Hz=round(f1_0, 1), actuel_fAB_Hz=round(f2_0, 1),
                 actuel_rapport_fH_note=" ".join(f"{f1_0 / x:.2f}" for x in notes["f"]),
                 actuel_marge_harmoniques_cents=round(marge_harmoniques(f1_0, notes["f"]), 0),
                 actuel_marge_AB_cents=round(marge_harmoniques(f2_0, notes["f"]), 0))
    if best is None:
        ligne["but"] = "aucun réglage dans les bornes"
        return ligne, None
    f1p, f2p = best["f1_elmer"], best["f2_elmer"]
    ligne.update(but=best["but"],
                 propose_trou_mm=f"{best['hx']:g} x {best['hy']:g}", propose_longueur_trou_mm=best["L"],
                 propose_ProfCase_mm=best["prof"], propose_cale_mm=best["cale"],
                 propose_V_cases_cm3=round(best["V"] / 1e3, 3),
                 propose_fH_elmer_Hz=round(f1p, 1), propose_fAB_elmer_Hz=round(f2p, 1),
                 propose_rapport_fH_note=" ".join(f"{f1p / x:.2f}" for x in notes["f"]),
                 propose_dans_fenetre=all(FENETRE[0] <= f1p / x <= FENETRE[1] for x in notes["f"]),
                 propose_marge_harmoniques_cents=round(marge_harmoniques(f1p, notes["f"]), 0),
                 propose_marge_AB_cents=round(marge_harmoniques(f2p, notes["f"]), 0),
                 kappa=round(kappa, 3), iterations=best["iterations"])
    if avec_seuil:
        k0 = kappa_de(f1_0, S0, V0, TABLE0)
        p0 = [seuil(x, V0, S0, TABLE0, k0) for x in notes["f"]]
        p1 = [seuil(x, best["V"], best["S"], best["L"], kappa) for x in notes["f"]]
        fmt = lambda p: f"{p:.0f}" if p else "non"
        ligne.update(actuel_p_on_Pa=" ".join(fmt(p) for p in p0), propose_p_on_Pa=" ".join(fmt(p) for p in p1),
                     gain_p_on_pct=" ".join(f"{100 * (b / a - 1):+.0f}" if (a and b) else "?" for a, b in zip(p0, p1)))
    ligne["duree_s"] = round(time.time() - t0, 1)
    return ligne, best


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chambres", type=int, nargs="*")
    ap.add_argument("--sans-seuil", action="store_true")
    ap.add_argument("--notes", default=os.path.join(ICI, "notes_r12.csv"))
    a = ap.parse_args(argv)
    cotes = cotes_sommier()
    notes = lire_notes(a.notes)
    ks = a.chambres or sorted(notes)
    lignes, prop = [], {"statut": "PROPOSITION, à confirmer (notes hypothétiques, bornes à valider)",
                        "notes": os.path.basename(a.notes), "ProfCase": {}, "trou_table": {}}
    for k in ks:
        l, b = optimiser(k, cotes, notes[k], not a.sans_seuil)
        lignes.append(l)
        print(l, flush=True)
        if b:
            prop["ProfCase"][k] = b["prof"]
            prop["trou_table"][k] = dict(hx_mm=b["hx"], hy_mm=b["hy"], longueur_mm=b["L"])
            if b["cale"]:
                prop.setdefault("cale_fond_mm", {})[k] = b["cale"]
    os.makedirs(RESULTATS, exist_ok=True)
    cles = []
    for l in lignes:
        cles += [c for c in l if c not in cles]
    ch = os.path.join(RESULTATS, "optimisation_r12.csv")
    with open(ch, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cles, delimiter=";")
        w.writeheader()
        w.writerows(lignes)
    actuels = cotes["TABLE_R12"]["ProfCase"]
    changes = {k: v for k, v in prop["ProfCase"].items() if abs(v - actuels[k - 1]) > 1e-9}
    prop["commande_sommier"] = ("J:\\claude\\venv\\Scripts\\python.exe outils/zw3d/sommier.py --set "
                                + " ".join(f"ProfCase_{k}={v:g}" for k, v in changes.items())) if changes else \
        "aucun changement de ProfCase"
    with open(os.path.join(RESULTATS, "proposition_cotes_R12.json"), "w", encoding="utf-8") as fh:
        json.dump(prop, fh, ensure_ascii=False, indent=1)
    print("->", ch)
    print("->", os.path.join(RESULTATS, "proposition_cotes_R12.json"))
    print(prop["commande_sommier"])


if __name__ == "__main__":
    main()

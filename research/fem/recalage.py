"""Recalage : confronter le modèle aux mesures d'Ewen, anche par anche.

Trois comparaisons, de la plus sûre à la plus fragile
-----------------------------------------------------
1. **Fréquence propre** (son pincé) contre éléments finis. Si elles diffèrent, on recale
   l'ÉPAISSEUR (un facteur commun à tous les tronçons), en gardant E de l'acier : une erreur
   de 0,01 mm au palmer sur 0,25 mm fait 4 % sur la fréquence, alors que E d'un acier à
   ressort ne varie que de 2 à 3 %. Le script donne aussi le E « apparent » qui expliquerait
   l'écart à épaisseur fixe, pour juger : un E hors de 190-215 GPa veut dire « remesurer ».
   Le modèle de fréquence est Euler-Bernoulli exact multiplié par le petit facteur
   Elmer / Euler-Bernoulli (effet de plaque, encastrement au rivet) lu dans
   `fem/anche/resultats/modal_<id>.json` s'il existe.
2. **Amortissement** (son pincé) contre la valeur du modèle (zeta = 0,004, deviné dans
   `coupled_reeds`). La mesure remplace la valeur devinée. Attention : c'est
   l'amortissement sans souffle (matériau, air, encastrement), pas celui en jeu.
3. **Seuil de démarrage et fréquence de jeu** (module Seuils du banc, CSV) contre le modèle
   semi-analytique (`coupled_reeds`), nourri par la languette recalée (masse, raideur,
   forme modales) et par la chambre vue par Elmer (`fem/sommier/resultats/impedance_<id>.json` :
   volume effectif et longueur effective du trou). Option `--recaler-levee` : la levée au
   repos (la cote la moins sûre au pied à coulisse) est ajustée pour retrouver le seuil mesuré.

Conditions initiales : il n'en faut pas d'autres que la levée au repos (dans la banque) et
la rampe de pression (le modèle part au repos et suit la pression, comme le banc).

Sorties : un tableau des écarts et des paramètres recalés (`fem/resultats/recalage.csv`).
Sans mesure, le script dit ce qu'il attend et affiche les valeurs du modèle seules.

Usage
-----
  J:\\claude\\venv\\Scripts\\python.exe recalage.py                          toutes les anches du yaml
  ... --mesure R12-grave 69.2 0.0012                                 f (Hz) et zeta à la main
  ... --pince R12-grave son.m4a                                      ou le son pincé
  ... --seuils R12-grave seuils_R12-grave.csv                        CSV du module Seuils
  ... --sans-seuil                                                   sauter le modèle semi-analytique (rapide)
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(ICI, "..")))           # research/
from banc_recherche.banque_anches import charger_yaml, nom_note  # noqa: E402
from banc_recherche.languette import (LanguetteModale, euler_bernoulli,  # noqa: E402
                                      forme_euler_bernoulli, parametres_modaux, reglage)

YAML = os.path.join(ICI, "anche", "anches_r12.yaml")
E_ACIER = 2.10e11
E_PLAUSIBLE = (1.90e11, 2.15e11)          # aciers à ressort, au carbone ou inox
U_PALMER_MM = 0.01                         # incertitude d'une épaisseur au palmer
ZETA_MODELE = 0.004                        # valeur devinée de coupled_reeds


def _nom_fichier(id_):
    return re.sub(r"[^\w.-]+", "_", id_)


# --- 1. Fréquence ----------------------------------------------------------------------------
def facteur_fem(id_, f_eb_nominal):
    """f1 Elmer / f1 Euler-Bernoulli (même languette nominale), 1 si pas de calcul Elmer."""
    ch = os.path.join(ICI, "anche", "resultats", f"modal_{_nom_fichier(id_)}.json")
    if not os.path.exists(ch):
        return 1.0, "Euler-Bernoulli seul (pas encore de calcul Elmer)"
    d = json.load(open(ch, encoding="utf-8"))
    if not d.get("mode1"):
        return 1.0, "Euler-Bernoulli seul"
    return d["mode1"]["f_Hz"] / f_eb_nominal, f"Elmer {d.get('elmer', '')}, {d.get('encastrement', '')}"


def recaler_epaisseur(anche, f_mesure, c_fem=1.0):
    """Facteur s sur toutes les épaisseurs tel que c_fem.f1_EB(s) = f_mesure."""
    from scipy.optimize import brentq

    def ecart(s):
        return c_fem * float(euler_bernoulli(anche.languette(facteur_epaisseur=s), 1)[0]) - f_mesure

    return brentq(ecart, 0.3, 3.0, xtol=1e-6)


def epaisseur_mediane_mm(anche):
    tr = sorted((0.5 * sum(t["epaisseur_mm"]), t["longueur_mm"]) for t in anche.troncons)
    tot, c = sum(l for _, l in tr), 0.0
    for e, l in tr:
        c += l
        if c >= tot / 2:
            return e
    return tr[-1][0]


# --- 3. Seuils -------------------------------------------------------------------------------
def lire_seuils(chemin):
    """CSV du module Seuils (PR #30) : p_on des cycles (lignes « # cycle »), fréquence de jeu
    près du démarrage (médiane de f0 quand l'anche sonne, entre p_on et 1,3 p_on)."""
    p_on, rows = [], []
    with open(chemin, encoding="utf-8", errors="replace") as fh:
        for ligne in fh:
            if ligne.startswith("# cycle"):
                m = re.search(r"p_on\s+([-\d.,]+)", ligne)
                if m and m.group(1) not in ("", "-"):
                    try:
                        p_on.append(float(m.group(1).replace(",", ".")))
                    except ValueError:
                        pass
            elif ligne and ligne[0].isdigit():
                rows.append(ligne.strip().split(","))
    p = float(np.median(p_on)) if p_on else float("nan")
    f_jeu = []
    for r in rows:
        try:
            pr, f0, sonne = float(r[1]), float(r[6]), r[7] == "1"
        except (ValueError, IndexError):
            continue
        if sonne and math.isfinite(p) and p <= pr <= 1.3 * p:
            f_jeu.append(f0)
    return dict(p_on_Pa=p, n_cycles=len(p_on), f_jeu_Hz=float(np.median(f_jeu)) if f_jeu else float("nan"))


def voicing_elmer(id_):
    """Le réseau de la chambre vu par Elmer (volume effectif, longueur effective du trou)."""
    from banc_recherche.coupled_reeds import Orifice, Voicing
    ch = os.path.join(ICI, "sommier", "resultats", f"impedance_{_nom_fichier(id_)}.json")
    if not os.path.exists(ch):
        return Voicing(shared_chamber=True), "réseau par défaut de coupled_reeds (pas d'impédance Elmer)"
    d = json.load(open(ch, encoding="utf-8"))
    r = d["reseau"]
    hx, hy = d["trou_mm"]
    return (Voicing(chamber_m3=r["V_eff_m3"], hole=Orifice(hx * hy * 1e-6, r["l_eff_trou_m"]), shared_chamber=True),
            f"Elmer : V = {r['V_eff_m3'] * 1e6:.2f} cm3, trou l_eff = {r['l_eff_trou_m'] * 1e3:.1f} mm")


def modele_semi_analytique(anche, s_ep, f1, zeta, levee_mm=None):
    """CoupledReedsModel à une anche (l'autre muette), languette recalée, chambre d'Elmer."""
    from banc_recherche.coupled_reeds import CoupledReedsModel
    lang = anche.languette(facteur_epaisseur=s_ep)
    p = parametres_modaux(lang, f_hz=f1, forme=lambda x: forme_euler_bernoulli(lang, f1, x), source="recalée")
    fente_l = anche.valeur("fente_largeur_mm") * 1e-3
    lm = [LanguetteModale(p, lang.L, fente_l, zeta) for _ in range(2)]
    b_bout = anche.troncons[-1]["largeur_mm"][1] * 1e-3
    e_bout = anche.troncons[-1]["epaisseur_mm"][1] * 1e-3 * s_ep
    lev = (levee_mm if levee_mm is not None else anche.valeur("levee_mm")) * 1e-3
    st = reglage(lev, anche.valeur("plaque_mm") * 1e-3, e_bout, fente_l, b_bout, p.phi_moyen)
    v, src = voicing_elmer(anche.id)
    sens = "tirer" if anche.valeur("sens") == "tire" else "pousser"
    return CoupledReedsModel(reeds=lm, settings=[st, st], voicing=v, direction=sens, muted=(False, True)), src


def seuil_modele(m):
    sys.path.insert(0, os.path.join(ICI, "sommier"))
    from seuils_cavite import seuils
    p_on, f_on, _ = seuils(m)
    return p_on, f_on


def recaler_levee(anche, s_ep, f1, zeta, p_mesure, lo=0.05, hi=3.0):
    """Levée (mm) qui redonne le seuil mesuré : dichotomie (en log) sur [lo, hi]. Le sens de
    variation du seuil avec la levée est lu dans le modèle aux deux bornes, pas supposé.
    Renvoie None si le seuil mesuré n'est pas atteignable dans la plage."""
    def p_de(lev):
        p, _ = seuil_modele(modele_semi_analytique(anche, s_ep, f1, zeta, lev)[0])
        return p if p else float("inf")

    p_lo, p_hi = p_de(lo), p_de(hi)
    if not (min(p_lo, p_hi) <= p_mesure <= max(p_lo, p_hi)):
        return None
    croissant = p_hi > p_lo
    for _ in range(12):
        mid = math.sqrt(lo * hi)
        if (p_de(mid) > p_mesure) == croissant:
            hi = mid
        else:
            lo = mid
    return math.sqrt(lo * hi)


# --- Le tableau ------------------------------------------------------------------------------
def recaler(anche, f_mesure=None, zeta_mesure=None, seuils_mesure=None, avec_seuil=True,
            avec_levee=False):
    lang = anche.languette()
    f_eb = float(euler_bernoulli(lang, 1)[0])
    c, src_f = facteur_fem(anche.id, f_eb)
    f_mod = c * f_eb
    t_med = epaisseur_mediane_mm(anche)
    d = dict(id=anche.id, note=anche.valeur("note"), f_modele_Hz=round(f_mod, 2), source_f=src_f,
             f_mesure_Hz="", ecart_f_cents="", facteur_epaisseur="", delta_ep_mm="", E_apparent_GPa="",
             verdict_f="en attente du son pincé", zeta_modele=ZETA_MODELE, zeta_mesure="", ecart_zeta_pct="",
             p_on_modele_Pa="", p_on_mesure_Pa="", ecart_p_on_pct="", f_jeu_modele_Hz="", f_jeu_mesure_Hz="",
             ecart_f_jeu_cents="", levee_recalee_mm="", chambre_modele="", a_mesurer=", ".join(anche.liste_a_mesurer()))
    s_ep, f1, zeta = 1.0, f_mod, ZETA_MODELE
    if f_mesure:
        s_ep = recaler_epaisseur(anche, f_mesure, c)
        E_app = E_ACIER * (f_mesure / f_mod) ** 2
        delta = (s_ep - 1) * t_med
        ok = abs(delta) <= U_PALMER_MM
        d.update(f_mesure_Hz=round(f_mesure, 3), ecart_f_cents=round(1200 * math.log2(f_mod / f_mesure), 1),
                 facteur_epaisseur=round(s_ep, 4), delta_ep_mm=round(delta, 4), E_apparent_GPa=round(E_app / 1e9, 1),
                 verdict_f=("cohérent : écart dans l'incertitude du palmer, on garde E de l'acier"
                            if ok else
                            ("épaisseur recalée hors du palmer ; E apparent plausible : remesurer l'épaisseur"
                             if E_PLAUSIBLE[0] <= E_app <= E_PLAUSIBLE[1] else
                             "écart trop grand pour l'épaisseur ou E : vérifier longueur libre, encastrement, masse au bout")))
        f1 = f_mesure
    if zeta_mesure:
        zeta = zeta_mesure
        d.update(zeta_mesure=f"{zeta_mesure:.2e}", ecart_zeta_pct=round(100 * (ZETA_MODELE / zeta_mesure - 1), 0))
    if avec_seuil:
        m, src = modele_semi_analytique(anche, s_ep, f1, zeta)
        d["chambre_modele"] = src
        p_on, f_on = seuil_modele(m)
        bas = p_on is not None and p_on <= 10.0 * 1.0001          # bas de la plage de seuils()
        d.update(p_on_modele_Pa=("10 Pa ou moins (bas de la plage)" if bas else round(p_on, 1)) if p_on
                 else "pas de démarrage sous 8 kPa",
                 f_jeu_modele_Hz=round(f_on, 2) if f_on == f_on else "")
        if seuils_mesure and math.isfinite(seuils_mesure["p_on_Pa"]):
            pm, fj = seuils_mesure["p_on_Pa"], seuils_mesure["f_jeu_Hz"]
            d.update(p_on_mesure_Pa=round(pm, 1), ecart_p_on_pct=round(100 * (p_on / pm - 1), 0) if p_on and not bas else "",
                     f_jeu_mesure_Hz=round(fj, 2) if fj == fj else "",
                     ecart_f_jeu_cents=round(1200 * math.log2(f_on / fj), 1) if (fj == fj and f_on == f_on) else "")
            if avec_levee:
                lv = recaler_levee(anche, s_ep, f1, zeta, pm)
                d["levee_recalee_mm"] = round(lv, 3) if lv else "hors de 0,05-3 mm"
    return d


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--yaml", default=YAML)
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--mesure", nargs="+", action="append", metavar="ID F [ZETA]", default=[])
    ap.add_argument("--pince", nargs=2, action="append", metavar=("ID", "FICHIER"), default=[])
    ap.add_argument("--seuils", nargs=2, action="append", metavar=("ID", "CSV"), default=[])
    ap.add_argument("--sans-seuil", action="store_true")
    ap.add_argument("--recaler-levee", action="store_true")
    ap.add_argument("--sortie", default=os.path.join(ICI, "resultats", "recalage.csv"))
    a = ap.parse_args(argv)
    anches = charger_yaml(a.yaml)
    base = os.path.dirname(os.path.abspath(a.yaml))
    mesures = {m[0]: (float(m[1]), float(m[2]) if len(m) > 2 else None) for m in a.mesure}
    pinces = dict(a.pince)
    seuils_f = dict(a.seuils)
    lignes = []
    for an in anches:
        if a.ids and an.id not in a.ids:
            continue
        f_m, z_m = mesures.get(an.id, (None, None))
        fichier = pinces.get(an.id) or an.valeur("son_pince")
        if f_m is None and fichier:
            from banc_recherche.pince import analyser_fichier
            ch = fichier if os.path.isabs(fichier) else os.path.join(base, fichier)
            r = analyser_fichier(ch, f_attendue=an.valeur("note_Hz"))
            print(r.resume())
            f_m, z_m = r.f_hz, r.zeta
        s_csv = seuils_f.get(an.id) or an.valeur("seuils_csv")
        s_m = None
        if s_csv:
            s_m = lire_seuils(s_csv if os.path.isabs(s_csv) else os.path.join(base, s_csv))
        d = recaler(an, f_m, z_m, s_m, avec_seuil=not a.sans_seuil, avec_levee=a.recaler_levee)
        lignes.append(d)
        print(f"\n{an.id} ({d['note']}) : modèle f1 = {d['f_modele_Hz']} Hz [{d['source_f']}]")
        if f_m:
            print(f"  son pincé {d['f_mesure_Hz']} Hz : écart {d['ecart_f_cents']} c ; épaisseur x {d['facteur_epaisseur']}"
                  f" ({d['delta_ep_mm']:+} mm), ou E = {d['E_apparent_GPa']} GPa -> {d['verdict_f']}")
        else:
            print("  son pincé : pas encore mesuré")
        if d["p_on_modele_Pa"] != "":
            print(f"  seuil modèle {d['p_on_modele_Pa']} Pa, fréquence de jeu {d['f_jeu_modele_Hz']} Hz"
                  f" ; mesure : {d['p_on_mesure_Pa'] or 'pas encore'} [{d['chambre_modele']}]")
        print(f"  à mesurer : {d['a_mesurer']}")
    os.makedirs(os.path.dirname(a.sortie), exist_ok=True)
    with open(a.sortie, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(lignes[0].keys()), delimiter=";")
        w.writeheader()
        w.writerows(lignes)
    print("\n->", a.sortie)


if __name__ == "__main__":
    main()

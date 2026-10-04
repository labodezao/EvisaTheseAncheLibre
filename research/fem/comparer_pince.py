"""Comparer le son pincé au modèle : l'anche seule, puis l'anche sur sa chambre.

Les deux premiers gestes du protocole de recalage (`docs/protocole_recalage_experimental.md`) :

(a) l'anche seule, sur sa plaque, pincée : les modes de la languette.
    Modèle : Elmer (`anche/resultats/modal_<id>.json`, tous les modes, avec leur type) et
    Euler-Bernoulli exact (flexion seule). Ce qu'on recale :
    - l'ÉPAISSEUR (facteur commun) par le mode 1, comme `recalage.py` ;
    - rien de plus par les modes 2 et 3, mais ils JUGENT la géométrie : un facteur commun
      d'épaisseur (ou un E faux) multiplie toutes les fréquences par le même nombre, donc
      les rapports f2/f1 et f3/f1 n'en dépendent pas. S'ils diffèrent du modèle de plus de
      3 %, c'est la forme qui est fausse (masse au bout, profil gratté, longueur libre,
      encastrement), pas l'épaisseur ;
    - l'amortissement de chaque mode (zeta_1, zeta_2) remplace la valeur devinée du
      modèle RK4 (`ReedModel(..., zeta=[zeta_1, zeta_2])`).

(b) l'anche sur sa chambre, pincée (l'anche extérieure, soupape relevée) : la languette voit
    l'air de la chambre par sa fente. Modèle : le réseau d'Elmer vu par la fente
    (`sommier/resultats/impedance_<id>.json`) : inertance de la fente L_f, inertance du trou
    de table L_t, compliance de la chambre C = V_eff / (rho c^2). La languette (masse m,
    raideur k, aire balayée gamma = volume déplacé par mètre de course du bout) pousse un
    débit gamma.dy/dt dans ce réseau, qui lui renvoie une pression. Sans pertes :

        k - w^2 m - w^2 (kappa.gamma)^2 [ L_f + L_t / (1 - w^2 / w_H^2) ] = 0

    soit, en s = w^2 :  (A / w_H^2) s^2 - (k / w_H^2 + A + B) s + k = 0,
    avec A = m + (kappa.gamma)^2 L_f et B = (kappa.gamma)^2 L_t.
    Deux racines : la languette (un peu plus grave sur la chambre, l'air lui ajoute de la
    masse sous f_H) et le résonateur de la chambre (f_H, un peu déplacé).
    kappa (0 à 1) dit quelle part du volume balayé passe vraiment par la chambre : l'air
    peut aussi contourner la languette par le jeu dans la fente. kappa = 1 : tout passe.
    Ce qu'on recale :
    - kappa, par le décalage de la languette (sur la chambre moins seule) ;
    - la longueur effective du trou de table, par la fréquence mesurée du résonateur
      (le volume de la chambre est connu par la CAO, la correction de bout du trou l'est
      moins) ;
    - la résistance de pertes R du résonateur (Elmer est sans pertes) par son amortissement :
      pour un R-L-C série, zeta_H = (R/2) sqrt(C / L_t), donc R = 2 zeta_H sqrt(L_t / C).

Hypothèses et limites : un seul mode de languette ; réseau sans pertes à 1 résonateur (le
mode « case A contre case B » n'y est pas) ; la languette seule est supposée chargée par la
seule inertance de sa fente (L_f), la même que sur la chambre ; l'air autour de la languette
en champ libre (masse ajoutée, environ -0,1 à -0,3 % sur la fréquence) n'est pas dans Elmer.

Usage (depuis `research\\fem\\`) :
  J:\\claude\\venv\\Scripts\\python.exe comparer_pince.py R12-grave --seule pince_seule.wav
      [--cavite pince_chambre.wav] [--fmax 4000]
Sorties : `resultats/comparaison_pince_<id>.csv` (une ligne par mode et par grandeur recalée).
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
from banc_recherche.languette import euler_bernoulli  # noqa: E402

YAML = os.path.join(ICI, "anche", "anches_r12.yaml")
RHO, C_SON = 1.2, 343.0
TOL_RAPPORT = 0.03          # au-delà, la géométrie (pas l'épaisseur) est en cause


def _nom(id_):
    return re.sub(r"[^\w.-]+", "_", id_)


def cents(a, b):
    return 1200.0 * math.log2(a / b)


# --- Le modèle ---------------------------------------------------------------------------------
def modes_modele(anche, n_eb=5):
    """Liste de dicts (rang, type, f_eb, f_elmer) : les modes d'Elmer s'il y en a (tous types),
    sinon les modes de flexion d'Euler-Bernoulli."""
    f_eb = [float(f) for f in euler_bernoulli(anche.languette(), n_eb)]
    ch = os.path.join(ICI, "anche", "resultats", f"modal_{_nom(anche.id)}.json")
    if os.path.exists(ch):
        d = json.load(open(ch, encoding="utf-8"))
        out, k = [], 0
        for f, t in zip(d["frequences_Hz"], d.get("types", ["flexion"] * len(d["frequences_Hz"]))):
            eb = None
            if t == "flexion":
                eb = f_eb[k] if k < len(f_eb) else None
                k += 1
            out.append(dict(rang=len(out) + 1, type=t, f_eb=eb, f_elmer=float(f)))
        return out, d.get("mode1")
    return [dict(rang=i + 1, type="flexion", f_eb=f, f_elmer=None) for i, f in enumerate(f_eb)], None


def apparier(modele, mesures, tol_rel=0.2):
    """Associe chaque mode du modèle au mode mesuré le plus proche (en cents), à tol_rel près,
    sans réutiliser un mode mesuré. Rend {rang: ModeMesure}.

    Les modes de FLEXION (hors plan) passent d'abord : un pincement pousse la languette
    perpendiculairement à son plan et le micro entend surtout ce mouvement. La flexion dans
    le plan (Elmer : 996 Hz pour l'anche de matrix.txt, tout près de la flexion 2 à 842 Hz)
    est à peine excitée ; sans cet ordre, une flexion 2 décalée de 10 % lui serait attribuée."""
    pris_m, pris_x, out = set(), set(), {}
    for passe in (lambda m: m["type"] == "flexion", lambda m: m["type"] != "flexion"):
        paires = []
        for m in modele:
            if not passe(m):
                continue
            fm = m["f_elmer"] or m["f_eb"]
            for j, x in enumerate(mesures):
                if abs(x.f_hz / fm - 1) < tol_rel:
                    paires.append((abs(cents(x.f_hz, fm)), m["rang"], j))
        paires.sort()
        for _, r, j in paires:
            if r not in pris_m and j not in pris_x:
                out[r] = mesures[j]
                pris_m.add(r)
                pris_x.add(j)
    return out


def racines_languette_chambre(m, k, gamma, L_f, L_t, f_H, kappa=1.0):
    """(f languette, f résonateur) du système languette + réseau de la chambre, sans pertes."""
    wH2 = (2 * math.pi * f_H) ** 2
    g2 = (kappa * gamma) ** 2
    A, B = m + g2 * L_f, g2 * L_t
    a2, a1, a0 = A / wH2, -(k / wH2 + A + B), k
    disc = a1 * a1 - 4 * a2 * a0
    s1 = (-a1 - math.sqrt(disc)) / (2 * a2)
    s2 = (-a1 + math.sqrt(disc)) / (2 * a2)
    s1, s2 = sorted((s1, s2))
    return math.sqrt(s1) / (2 * math.pi), math.sqrt(s2) / (2 * math.pi)


def reseau_chambre(id_):
    ch = os.path.join(ICI, "sommier", "resultats", f"impedance_{_nom(id_)}.json")
    if not os.path.exists(ch):
        return None
    d = json.load(open(ch, encoding="utf-8"))
    r = d["reseau"]
    hx, hy = d["trou_mm"]
    return dict(f_H=r["f1_Hz"], L_t=r["L_trou_kg_m4"], L_f=r["L_fente_kg_m4"], V=r["V_eff_m3"],
                l_eff=r["l_eff_trou_m"], S_trou=hx * hy * 1e-6, chambre=d.get("chambre"))


def prediction_chambre(mode1, res, kappa=1.0):
    """Ce que le modèle prédit pour le pincement sur la chambre."""
    m, k, g = mode1["m_eff_kg"], mode1["k_eff_N_m"], mode1["gamma_m2"]
    f_vide = math.sqrt(k / m) / (2 * math.pi)
    f_seule, _ = racines_languette_chambre(m, k, g, res["L_f"], 0.0, res["f_H"], kappa)
    f_lang, f_res = racines_languette_chambre(m, k, g, res["L_f"], res["L_t"], res["f_H"], kappa)
    return dict(f_vide=f_vide, f_seule=f_seule, f_chambre=f_lang, f_resonateur=f_res,
                decalage_cents=cents(f_lang, f_seule))


def recaler_kappa(mode1, res, decalage_mesure_cents):
    """kappa^2 ~ décalage mesuré / décalage prédit (le décalage est quasi linéaire en kappa^2)."""
    pred = prediction_chambre(mode1, res, 1.0)["decalage_cents"]
    if pred == 0:
        return float("nan")
    return decalage_mesure_cents / pred


def recaler_trou(mode1, res, f_res_mesure):
    """Longueur effective du trou (m) qui redonne la fréquence mesurée du résonateur, à volume
    fixé (dichotomie sur L_t ; C reste celle d'Elmer)."""
    C = 1.0 / ((2 * math.pi * res["f_H"]) ** 2 * res["L_t"])
    m, k, g = mode1["m_eff_kg"], mode1["k_eff_N_m"], mode1["gamma_m2"]

    def f_de(Lt):
        fH = 1.0 / (2 * math.pi * math.sqrt(Lt * C))
        return racines_languette_chambre(m, k, g, res["L_f"], Lt, fH)[1]

    lo, hi = res["L_t"] / 50, res["L_t"] * 50
    if not (f_de(hi) <= f_res_mesure <= f_de(lo)):
        return None
    for _ in range(80):
        mid = math.sqrt(lo * hi)
        if f_de(mid) > f_res_mesure:
            lo = mid
        else:
            hi = mid
    Lt = math.sqrt(lo * hi)
    return Lt * res["S_trou"] / RHO, Lt, C


def resistance_pertes(zeta_H, L_t, C):
    """R (Pa.s/m3) d'un R-L-C série qui donne l'amortissement mesuré du résonateur."""
    return 2.0 * zeta_H * math.sqrt(L_t / C)


# --- Le tableau --------------------------------------------------------------------------------
def _non_vu(m, f_max):
    fm = m["f_elmer"] or m["f_eb"]
    if fm > f_max:
        return f"au-dessus de la bande analysée ({f_max:.0f} Hz)"
    if m["type"] == "flexion dans le plan":
        return "attendu : un pincement perpendiculaire à la lame ne l'excite presque pas"
    return "non vu (nœud du micro ou du pincement ? pincer aussi au milieu de la lame)"


def recalage_mode1(anche, f1_mes):
    """Facteur d'épaisseur et E apparent qui expliquent f1 mesuré (la logique de recalage.py)."""
    import recalage as rc
    f_eb = float(euler_bernoulli(anche.languette(), 1)[0])
    c, _ = rc.facteur_fem(anche.id, f_eb)
    s_ep = rc.recaler_epaisseur(anche, f1_mes, c)
    e_app = rc.E_ACIER * (f1_mes / (c * f_eb)) ** 2
    delta = (s_ep - 1) * rc.epaisseur_mediane_mm(anche)
    return s_ep, e_app, delta, abs(delta) <= rc.U_PALMER_MM


def comparer_seule(anche, res_modes, f_max=float("inf")):
    """Lignes du tableau pour l'anche seule. `res_modes` : ResultatModes (pince_modes)."""
    modele, mode1 = modes_modele(anche)
    mes = res_modes.vrais_modes()
    paires = apparier(modele, mes)
    lignes = []
    f1_mod = modele[0]["f_elmer"] or modele[0]["f_eb"]
    f1_mes = paires[1].f_hz if 1 in paires else None
    for m in modele:
        x = paires.get(m["rang"])
        fm = m["f_elmer"] or m["f_eb"]
        lignes.append(dict(
            geste="seule", grandeur=f"mode {m['rang']} ({m['type']})",
            modele_euler_bernoulli=round(m["f_eb"], 2) if m["f_eb"] else "",
            modele_elmer=round(m["f_elmer"], 2) if m["f_elmer"] else "",
            mesure=round(x.f_hz, 3) if x else "", ecart_cents=round(cents(fm, x.f_hz), 1) if x else "",
            rapport_modele=round(fm / f1_mod, 4) if m["rang"] > 1 else "",
            rapport_mesure=round(x.f_hz / f1_mes, 4) if (x and f1_mes and m["rang"] > 1) else "",
            zeta_mesure=f"{x.zeta:.2e}" if x else "", q_mesure=round(x.q) if x else "",
            n_pincements=x.n_pincements if x else "",
            verdict=_verdict_rapport(fm / f1_mod, x.f_hz / f1_mes) if (x and f1_mes and m["rang"] > 1) else
            ("" if x else _non_vu(m, f_max))))
    if f1_mes:
        try:
            s_ep, e_app, delta, ok = recalage_mode1(anche, f1_mes)
            lignes[0]["verdict"] = (f"épaisseur x {s_ep:.4f} ({delta:+.3f} mm) ou E = {e_app / 1e9:.0f} GPa ; "
                                    + ("dans l'incertitude du palmer" if ok else "hors du palmer : remesurer"))
        except Exception as e:                                  # anche incomplète, scipy absent...
            lignes[0]["verdict"] = f"recalage de l'épaisseur impossible : {e}"
    flex = [paires[m["rang"]] for m in modele if m["type"] == "flexion" and m["rang"] in paires][:2]
    if flex:
        lignes.append(dict(geste="seule", grandeur="amortissements pour le modèle RK4",
                           mesure=", ".join(f"{x.zeta:.2e}" for x in flex),
                           verdict="ReedModel(..., zeta=[" + ", ".join(f"{x.zeta:.2e}" for x in flex)
                           + "]) : sans souffle (matériau, air, encastrement), pas l'amortissement en jeu"))
    vus = {id(v) for v in paires.values()}
    for x in mes:
        if id(x) not in vus:
            lignes.append(dict(geste="seule", grandeur="mode non apparié", mesure=round(x.f_hz, 3),
                               zeta_mesure=f"{x.zeta:.2e}", q_mesure=round(x.q), n_pincements=x.n_pincements,
                               verdict="pas dans le modèle : support, plaque, chambre, ou mode dans le plan"))
    return lignes, paires, mode1


def _verdict_rapport(r_mod, r_mes):
    e = r_mes / r_mod - 1
    if abs(e) <= TOL_RAPPORT:
        return f"rapport à {100 * e:+.1f} % : la forme est juste, seule l'échelle (épaisseur, E) peut bouger"
    return (f"rapport à {100 * e:+.1f} % : la FORME est en cause (masse au bout, profil, longueur libre, "
            "encastrement), pas l'épaisseur")


def comparer_chambre(anche, res_cav, f1_seule=None, mode1=None):
    """Lignes du tableau pour l'anche sur sa chambre."""
    res = reseau_chambre(anche.id)
    if res is None or mode1 is None:
        return [dict(geste="chambre", grandeur="modèle", verdict="pas d'impédance Elmer ou de mode 1 Elmer : "
                     "lancer sommier/impedance_fente.py et anche/languette_modes.py --anches")]
    p = prediction_chambre(mode1, res)
    mes = res_cav.vrais_modes()
    lignes = []
    # la languette : le mode mesuré le plus proche du mode 1
    lang = min(mes, key=lambda x: abs(cents(x.f_hz, p["f_chambre"]))) if mes else None
    if lang and abs(cents(lang.f_hz, p["f_chambre"])) > 600:
        lang = None
    d_mes = cents(lang.f_hz, f1_seule) if (lang and f1_seule) else None
    kap2 = recaler_kappa(mode1, res, d_mes) if d_mes is not None else None
    lignes.append(dict(geste="chambre", grandeur="languette : décalage sur la chambre (cents)",
                       modele_elmer=round(p["decalage_cents"], 2), mesure=round(d_mes, 2) if d_mes is not None else "",
                       zeta_mesure=f"{lang.zeta:.2e}" if lang else "",
                       verdict=("kappa^2 = %.2f (part du volume balayé qui passe par la chambre)" % kap2
                                if kap2 is not None else "il faut aussi le pincement de l'anche seule (--seule)")))
    # le résonateur de la chambre : le mode mesuré le plus proche de f_H
    reso = min(mes, key=lambda x: abs(cents(x.f_hz, p["f_resonateur"]))) if mes else None
    if reso and abs(cents(reso.f_hz, p["f_resonateur"])) > 500:
        reso = None
    v = "non vu : le résonateur est trop amorti ou peu excité (taper la plaque près de la fente)"
    if reso:
        rt = recaler_trou(mode1, res, reso.f_hz)
        if rt:
            l_eff, Lt, C = rt
            R = resistance_pertes(reso.zeta, Lt, C)
            v = (f"trou l_eff : {res['l_eff'] * 1e3:.1f} -> {l_eff * 1e3:.1f} mm ; pertes R = {R:.3g} Pa.s/m3 "
                 f"(Q = {reso.q:.0f})")
        else:
            v = "fréquence hors de portée d'un simple changement de trou : revoir le volume ou le maillage"
    lignes.append(dict(geste="chambre", grandeur=f"résonateur de la chambre {res['chambre']} (Hz)",
                       modele_elmer=round(p["f_resonateur"], 1), mesure=round(reso.f_hz, 2) if reso else "",
                       ecart_cents=round(cents(p["f_resonateur"], reso.f_hz), 1) if reso else "",
                       zeta_mesure=f"{reso.zeta:.2e}" if reso else "", q_mesure=round(reso.q) if reso else "",
                       verdict=v))
    return lignes


def ecrire(lignes, chemin):
    cles = ["geste", "grandeur", "modele_euler_bernoulli", "modele_elmer", "mesure", "ecart_cents",
            "rapport_modele", "rapport_mesure", "zeta_mesure", "q_mesure", "n_pincements", "verdict"]
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cles, delimiter=";", extrasaction="ignore")
        w.writeheader()
        for l in lignes:
            w.writerow({k: l.get(k, "") for k in cles})


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    from banc_recherche.banque_anches import charger_yaml
    from banc_recherche.pince_modes import analyser_fichier
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("id")
    ap.add_argument("--seule", help="son de l'anche seule pincée (wav, m4a...)")
    ap.add_argument("--cavite", help="son de l'anche pincée sur sa chambre")
    ap.add_argument("--yaml", default=YAML)
    ap.add_argument("--fmax", type=float, default=4000.0)
    a = ap.parse_args(argv)
    anche = next((x for x in charger_yaml(a.yaml) if x.id == a.id), None)
    if anche is None:
        raise SystemExit(f"anche {a.id} absente de {a.yaml}")
    modele, mode1 = modes_modele(anche)
    attendues = [m["f_elmer"] or m["f_eb"] for m in modele]
    lignes, f1_seule = [], None
    if a.seule:
        r = analyser_fichier(a.seule, f_max=a.fmax, attendues=attendues)
        print(r.resume())
        l, paires, mode1 = comparer_seule(anche, r, a.fmax)
        lignes += l
        f1_seule = paires[1].f_hz if 1 in paires else None
    if a.cavite:
        res = reseau_chambre(anche.id)
        att = attendues + ([res["f_H"]] if res else [])
        r = analyser_fichier(a.cavite, f_max=a.fmax, attendues=att)
        print(r.resume())
        lignes += comparer_chambre(anche, r, f1_seule, mode1)
    if not lignes:
        print("rien à comparer : donner --seule et/ou --cavite")
        return
    print()
    for l in lignes:
        print(f"[{l['geste']}] {l['grandeur']} : modèle {l.get('modele_elmer') or l.get('modele_euler_bernoulli', '')}"
              f", mesure {l.get('mesure', '')} ; {l.get('verdict', '')}")
    sortie = os.path.join(ICI, "resultats", f"comparaison_pince_{_nom(anche.id)}.csv")
    ecrire(lignes, sortie)
    print("->", sortie)


if __name__ == "__main__":
    main()

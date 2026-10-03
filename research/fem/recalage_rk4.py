"""Recalage entre Elmer et le modèle Runge-Kutta 4 de l'anche (`reed_model`, `reed_oscillator`).

Trois étapes, chacune avec un écart chiffré AVANT et APRÈS recalage.

1. La languette. Ce que `reed_model` utilise : `modal.assemble` (Rayleigh-Ritz sur N = 2
   modes du cantilever uniforme, coefficients sigma arrondis). Comparé à Euler-Bernoulli
   exact (`languette.euler_bernoulli`) et à Elmer 3D (hexaèdres quadratiques), sur les
   mêmes languettes : `SECTIONS_DEFAULT` de `reed_model`, l'anche de `matrix.txt`, les
   anches nominales de la banque, la lame de la CAO 2019 (Code_Aster). Grandeurs : f1, f2,
   masse et raideur modales du mode 1 ramenées au bout, projection de la pression
   (gamma), forme (MAC). Recalage : les paramètres d'Elmer injectés dans le modèle RK4
   (`modal_params`, option « paramètres issus d'Elmer »).
2. La cavité. `reed_model` : une cavité fermée de 35 x 15 x 15 mm, adiabatique ; vue de
   l'anche, une pure compliance Z = 1 / (i.omega.C), C = V / (gamma.P). Elmer : la chambre
   et son trou de table vus depuis la fente (`sommier/impedance_fente.py`). Recalage : un
   résonateur à constantes localisées Z = i.omega.[L_fente + a / (omega_1^2 - omega^2)]
   (volume effectif V = rho.c^2 / a, inertance du trou a / omega_1^2), calé sur Elmer dans
   la bande de l'anche [f1/2 ; 4.f1] (bornée sous le 2e pôle).
3. Le couplé. Seuil, fréquence de jeu, amplitude : (a) `FreeReedModel` (RK4 reformulé de
   `reed_model`) avec ses ingrédients d'origine ; (b) le même avec la languette et le
   volume d'Elmer ; (c) `coupled_reeds` (réseau avec le trou de table d'Elmer). Le
   `reed_model` d'origine n'auto-oscille pas (loi de cavité inversée,
   `docs/audit_modele_anche.md`) : on le vérifie, sans le recaler.

Usage : J:\\claude\\venv\\Scripts\\python.exe recalage_rk4.py [--sans-couple] [--amplitude]
Sorties : resultats/recalage_rk4_*.csv et figures resultats/recalage_rk4_*.png.
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
sys.path.insert(0, os.path.abspath(os.path.join(ICI, "..")))
sys.path.insert(0, ICI)
sys.path.insert(0, os.path.join(ICI, "anche"))
sys.path.insert(0, os.path.join(ICI, "sommier"))

from banc_recherche import modal  # noqa: E402
from banc_recherche.banque_anches import charger_yaml  # noqa: E402
from banc_recherche.languette import (Languette, ParametresModaux, Troncon,  # noqa: E402
                                      euler_bernoulli, forme_euler_bernoulli, parametres_modaux)
from banc_recherche.reed_model import SECTIONS_DEFAULT, Cavity, ReedModel  # noqa: E402

RESULTATS = os.path.join(ICI, "resultats")
RHO, C_SON, GAMMA, PATM = 1.2, 343.0, 1.4, 1e5


# --- Les languettes --------------------------------------------------------------------------
def lame_cao_2019():
    """La lame « reed grande masse 1 » (Code_Aster 2019 et bass_reed 2020), relue sur le
    maillage (mesh.nodes, sections par volumes de tétraèdres, 03/10/2026) : partie libre de
    37,5 mm au-delà du talon, largeur 4,33 -> 3,35 mm, épaisseur 0,335 -> 0,10 -> 0,248 mm,
    masse d'acier de 1,4 mm sur les 9 derniers mm. E = 210 GPa, rho = 7800, nu = 0,3."""
    def b(x):
        return 4.33 - (4.33 - 3.35) * (x - 8.35) / 37.5
    T = [(8.35, 13.0, 0.335, 0.10), (13.0, 27.9, 0.10, 0.10), (27.9, 36.85, 0.10, 0.248), (36.85, 45.85, 1.4, 1.4)]
    return Languette([Troncon((x1 - x0) * 1e-3, (b(x0) * 1e-3, b(x1) * 1e-3), (t0 * 1e-3, t1 * 1e-3), "acier",
                              E=2.1e11, rho=7800, nu=0.3) for x0, x1, t0, t1 in T], nom="CAO 2019")


CODE_ASTER_2019 = [144.437, 910.548, 1546.03, 2149.15]      # même maillage que bass_reed (tétra. linéaires)


def languettes():
    out = [("reed_model SECTIONS_DEFAULT", Languette.depuis_matrice(SECTIONS_DEFAULT, nom="SECTIONS_DEFAULT"), None)]
    yaml = os.path.join(ICI, "anche", "anches_r12.yaml")
    for a in charger_yaml(yaml):
        out.append((a.id, a.languette(), a))
    out.append(("CAO 2019 (Code_Aster)", lame_cao_2019(), None))
    return out


# --- 1. La languette -------------------------------------------------------------------------
def modal_reed_model(lang, n_modes=2):
    """Ce que voit reed_model : Rayleigh-Ritz de modal.assemble (sigma arrondis), sur les
    tronçons (variables -> 8 marches). Mode 1 ramené au bout."""
    sec = lang.matrice(n_sous=8)
    rm = ReedModel(sections=sec, n_modes=n_modes, zeta=0.004)
    w2, Phi = rm._eig_generalise()
    v = Phi[:, 0]                                   # M-orthonormé : v.M.v = 1
    tip = float(rm.phi_tip @ v)
    f = np.sqrt(np.clip(w2, 0, None)) / (2 * math.pi)
    L = rm.L

    def forme(x):
        return sum(v[i] * modal._phi(modal.bl_sigma(i + 1)[0] / L, modal.bl_sigma(i + 1)[1], np.asarray(x))
                   for i in range(n_modes)) / tip
    p = ParametresModaux(float(f[0]), 1.0 / tip ** 2, float(w2[0]) / tip ** 2, float(rm.gamma @ v) / tip,
                         float(np.mean(forme(np.linspace(0, L, 400)))), "reed_model")
    return f, p, forme


def mac(a, b):
    return float(np.dot(a, b) ** 2 / (np.dot(a, a) * np.dot(b, b)))


def etape_languette(liste, encastrement="pied"):
    from languette_modes import modes_elmer_cache
    lignes, details = [], {}
    for nom, lang, _ in liste:
        t0 = time.time()
        f_rm, p_rm, forme_rm = modal_reed_model(lang)
        eb = euler_bernoulli(lang, 2)
        el = modes_elmer_cache(lang, "rk4_" + nom, n_modes=8, encastrement=encastrement)
        fl = el["flexion"]
        f_el = [m["f_Hz"] for m in fl]
        xs = np.asarray(fl[0]["x_mm"]) * 1e-3
        prof = np.asarray(fl[0]["profil"])
        forme_el = lambda x, xs=xs, prof=prof: np.interp(np.asarray(x), xs, prof)
        p_el = parametres_modaux(lang, f_hz=f_el[0], forme=forme_el, source="elmer")
        x = np.linspace(0, lang.L, 300)
        M = mac(forme_rm(x), forme_el(x))
        p_eb = parametres_modaux(lang)
        for grandeur, a, b, c in (("f1 (Hz)", f_rm[0], eb[0], f_el[0]),
                                  ("f2 (Hz)", f_rm[1], eb[1], f_el[1]),
                                  ("masse modale au bout (mg)", p_rm.m_eff * 1e6, p_eb.m_eff * 1e6, p_el.m_eff * 1e6),
                                  ("raideur modale au bout (N/m)", p_rm.k_eff, p_eb.k_eff, p_el.k_eff),
                                  ("gamma (mm2)", p_rm.gamma * 1e6, p_eb.gamma * 1e6, p_el.gamma * 1e6)):
            lignes.append(dict(languette=nom, grandeur=grandeur, reed_model_origine=round(a, 4),
                               euler_bernoulli=round(b, 4), elmer_recale=round(c, 4),
                               ecart_origine_elmer_pct=round(100 * (a / c - 1), 2),
                               ecart_EB_elmer_pct=round(100 * (b / c - 1), 2)))
        lignes.append(dict(languette=nom, grandeur="MAC forme mode 1 (reed_model / Elmer)",
                           reed_model_origine=round(M, 5), euler_bernoulli="", elmer_recale=1.0,
                           ecart_origine_elmer_pct=round(100 * (M - 1), 3), ecart_EB_elmer_pct=""))
        if nom.startswith("CAO 2019"):
            for k, fa in enumerate(CODE_ASTER_2019[:2]):
                lignes.append(dict(languette=nom, grandeur=f"f{k + 1} Code_Aster 2019, tétraèdres linéaires (Hz)",
                                   reed_model_origine="", euler_bernoulli="", elmer_recale=round(fa, 2),
                                   ecart_origine_elmer_pct="", ecart_EB_elmer_pct=round(100 * (fa / f_el[k] - 1), 1)))
        details[nom] = dict(p_elmer=p_el, p_rm=p_rm, f_el=f_el, forme_el=forme_el, forme_rm=forme_rm, lang=lang,
                            elmer_cache=el.get("_cache"))
        print(f"[languette] {nom} : f1 reed_model {f_rm[0]:.2f} / EB {eb[0]:.2f} / Elmer {f_el[0]:.2f} Hz, "
              f"MAC {M:.4f} ({el.get('_cache')}, {time.time() - t0:.1f} s)", flush=True)
    return lignes, details


# --- 2. La cavité ----------------------------------------------------------------------------
def lire_impedance(id_):
    base = os.path.join(ICI, "sommier", "resultats", f"impedance_{id_}")
    if not os.path.exists(base + ".json"):
        return None
    d = json.load(open(base + ".json", encoding="utf-8"))
    z = np.loadtxt(base + ".csv", delimiter=";", skiprows=1)
    return d, z[:, 0], z[:, 1] + 1j * z[:, 2]


def caler_cavite(f, Z, f_anche, f_pole1, f_pole2):
    """Z = i.omega.[L_s + a/(omega_1^2 - omega^2)] calé sur Elmer dans la bande de l'anche
    [f/2 ; 4f] (bornée à 0,9 x le 2e pôle) : (L_s, a) par moindres carrés relatifs,
    omega_1 parti du pôle d'Elmer et ajusté (sauf si la bande est loin sous le pôle, où il
    n'est pas identifiable : il reste celui d'Elmer). Renvoie (L_s, a, f_1, masque, bande)."""
    lo, hi = max(f[0], 0.5 * f_anche), min(4 * f_anche, 0.9 * f_pole2 if f_pole2 else 4 * f_anche)
    m = (f >= lo) & (f <= hi)
    w = 2 * np.pi * f[m]
    y = Z.imag[m] / w

    def lin(w1):
        A = np.column_stack([np.ones_like(w), 1 / (w1 ** 2 - w ** 2)])
        pds = 1 / np.abs(y)
        return np.linalg.lstsq(A * pds[:, None], y * pds, rcond=None)[0]

    w1 = 2 * np.pi * f_pole1
    if hi > 0.5 * f_pole1:                       # la bande voit la résonance : f_1 ajustable
        def cout(w1_):
            Ls, a = lin(w1_)
            return float(np.sum(((Ls + a / (w1_ ** 2 - w ** 2) - y) / np.abs(y)) ** 2))
        # le coût saute quand omega_1 passe sur un point de mesure : balayage, puis affinage
        grille = w1 * np.linspace(0.8, 1.2, 801)
        k = int(np.argmin([cout(g) for g in grille]))
        from scipy.optimize import minimize_scalar
        r = minimize_scalar(cout, bounds=(grille[max(k - 1, 0)], grille[min(k + 1, len(grille) - 1)]),
                            method="bounded", options={"xatol": 1e-9 * w1})
        w1 = float(r.x)
    Ls, a = lin(w1)
    return Ls, a, w1 / (2 * np.pi), m, (lo, hi)


def etape_cavite(liste, details):
    lignes = []
    cav = Cavity()
    V0 = cav.length * cav.width * cav.height
    C0 = V0 / (GAMMA * PATM)
    for nom, lang, anche in liste:
        if anche is None:
            continue
        imp = lire_impedance(anche.id)
        if imp is None:
            print(f"[cavité] {nom} : pas d'impédance Elmer (lancer sommier/impedance_fente.py --yaml)")
            continue
        d, f, Z = imp
        f_a = details[nom]["f_el"][0]
        poles = d["poles_Hz"]
        Ls, a, f1c, m, (lo, hi) = caler_cavite(f, Z, f_a, poles[0], poles[1] if len(poles) > 1 else None)
        w = 2 * np.pi * f[m]
        Z0 = 1 / (1j * w * C0)
        Z1 = 1j * w * (Ls + a / ((2 * np.pi * f1c) ** 2 - w ** 2))
        # deux résonateurs (forme de Foster d'Elmer, toute la bande) : le 2e est le mode
        # « case A contre case B » ; c'est le premier qu'on donne au réseau de coupled_reeds
        fit = d["ajustement"]
        Z2 = 1j * w * (fit["L_fente"] + sum(an / ((2 * np.pi * fn) ** 2 - w ** 2) for fn, an in fit["poles"]))
        e0 = np.abs(Z0 - Z[m]) / np.abs(Z[m])
        e1 = np.abs(Z1 - Z[m]) / np.abs(Z[m])
        e2 = np.abs(Z2 - Z[m]) / np.abs(Z[m])
        V_1res = RHO * C_SON ** 2 / a
        f1c, a = fit["poles"][0]
        Ls = fit["L_fente"]
        V_eff = RHO * C_SON ** 2 / a
        L_h = a / (2 * np.pi * f1c) ** 2
        S_trou = d["trou_mm"][0] * d["trou_mm"][1] * 1e-6
        details[nom]["cavite"] = dict(V_eff=V_eff, l_eff=L_h * S_trou / RHO, S_trou=S_trou, L_s=Ls, trou_mm=d["trou_mm"])
        lignes.append(dict(anche=nom, chambre=d["chambre"], bande_Hz=f"{lo:.0f}-{hi:.0f}", f_anche_Hz=round(f_a, 1),
                           f_helmholtz_elmer_Hz=round(poles[0], 1), f_resonateur_cale_Hz=round(f1c, 1),
                           V_origine_cm3=round(V0 * 1e6, 3), V_eff_cale_cm3=round(V_eff * 1e6, 3),
                           V_cases_geometrie_cm3=round(d["V_cases_cm3"], 3),
                           trou_origine="aucun (cavité fermée)", l_eff_trou_mm=round(L_h * S_trou / RHO * 1e3, 2),
                           L_fente_kg_m4=round(Ls, 2),
                           ecart_Z_origine_median_pct=round(100 * float(np.median(e0)), 1),
                           ecart_Z_origine_max_pct=round(100 * float(np.max(e0)), 1),
                           ecart_Z_1resonateur_median_pct=round(100 * float(np.median(e1)), 2),
                           ecart_Z_1resonateur_max_pct=round(100 * float(np.max(e1)), 2),
                           V_1resonateur_cm3=round(V_1res * 1e6, 3),
                           ecart_Z_2resonateurs_median_pct=round(100 * float(np.median(e2)), 2),
                           ecart_Z_2resonateurs_max_pct=round(100 * float(np.max(e2)), 2),
                           phase_origine_deg=round(float(np.degrees(np.angle(Z0[0]))), 0),
                           phase_elmer_deg=round(float(np.degrees(np.angle(Z[m][0]))), 0)))
        details[nom]["Z"] = (f, Z, m, Z0, Z2)
        print(f"[cavité] {nom} : écart |Z| médian {lignes[-1]['ecart_Z_origine_median_pct']} % -> "
              f"{lignes[-1]['ecart_Z_1resonateur_median_pct']} % (1 résonateur) -> "
              f"{lignes[-1]['ecart_Z_2resonateurs_median_pct']} % (2)", flush=True)
    return lignes


# --- 3. Le couplé ----------------------------------------------------------------------------
def reed_model_oscille():
    """Le RK4 d'origine, valeurs par défaut : surpression moyenne et fréquence dominante."""
    from banc_recherche.coupled_reeds import dominant_frequency
    rm = ReedModel()
    r = rm.simulate(0.3, 22050.0, q_in=3e-5)
    dP = r.pressure - rm.cav.patm
    k = r.t > 0.1
    return float(np.mean(dP[k])), float(dominant_frequency(r.position[k], 22050.0))


def free_reed(lang, anche, p_modal=None, V=None):
    from banc_recherche.reed_oscillator import Chamber, FreeReedModel, Slot
    largeur = (anche.valeur("fente_largeur_mm") if anche else 4.8) * 1e-3
    ch = Chamber(volume_m3=V if V else Cavity().length * Cavity().width * Cavity().height)
    return FreeReedModel(sections=lang.matrice(n_sous=8), chamber=ch, slot=Slot(width_m=largeur), n_modes=2,
                         zeta=0.004, modal_params=p_modal)


def allure(tip, t, t0=0.5):
    """Demi-course (mm) sur la fin, et allure : établi, croît ou s'éteint (taux de
    variation de la course entre deux fenêtres, seuil 0,5 /s, comme seuils_cavite)."""
    k = t > t0
    x, tt = tip[k], t[k]
    n = x.size
    c1, c2 = float(np.ptp(x[: n // 2])), float(np.ptp(x[n // 2:]))
    dt = (tt[-1] - tt[0]) / 2
    taux = math.log(max(c2, 1e-15) / max(c1, 1e-15)) / dt
    return 0.5 * c2 * 1e3, ("s'éteint" if taux < -0.5 else "croît" if taux > 0.5 else "établi")


def amplitude_free(m, p_cible, kick=0.1e-3, dur=1.0):
    """Débit qui donne la pression d'équilibre p_cible, puis simulation, languette lancée."""
    lo, hi = 1e-9, 1e-1
    for _ in range(60):
        q = math.sqrt(lo * hi)
        if m.equilibrium(q)[2 * m.N] > p_cible:
            hi = q
        else:
            lo = q
    s0 = m.equilibrium(q)
    s0[m.N:2 * m.N] += kick * m.phi_tip / float(m.phi_tip @ m.phi_tip)
    r = m.simulate(dur, fs=22050.0, q_in=q, oversample=8, state0=s0)
    return allure(r.tip, r.t)


def etape_couple(liste, details, avec_amplitude=False):
    from banc_recherche.coupled_reeds import CoupledReedsModel, Orifice, Voicing
    from banc_recherche.languette import LanguetteModale, reglage
    from seuils_cavite import seuils
    lignes = []
    for nom, lang, anche in liste:
        if anche is None or "cavite" not in details[nom]:
            continue
        D = details[nom]
        f1 = D["f_el"][0]
        res = {}
        for cas, p_mod, V in (("RK4 FreeReedModel, origine (modal N=2, cavité 7,9 cm3 fermée)", None, None),
                              ("RK4 FreeReedModel, recalé (languette et volume d'Elmer)", D["p_elmer"], D["cavite"]["V_eff"])):
            t0 = time.time()
            m = free_reed(lang, anche, p_mod, V)
            s = m.hopf_threshold(q_lo=1e-8, q_hi=1e-2, n_scan=30)
            amp = ""
            if s is not None and avec_amplitude:
                a_mm, al = amplitude_free(m, 1.5 * s[1])
                amp = f"{a_mm:.3f} ({al})"
            res[cas] = (s[1] if s else None, s[2] if s else None, amp, m.f_modes[0])
            print(f"[couplé] {nom} : {cas} : seuil {s} ({time.time() - t0:.0f} s)", flush=True)
        # coupled_reeds : réseau avec le trou de table d'Elmer
        t0 = time.time()
        p = D["p_elmer"]
        fente_l = anche.valeur("fente_largeur_mm") * 1e-3
        lm = [LanguetteModale(p, lang.L, fente_l, 0.004) for _ in range(2)]
        st = reglage(anche.valeur("levee_mm") * 1e-3, anche.valeur("plaque_mm") * 1e-3,
                     lang.troncons[-1].epaisseur[1], fente_l, lang.troncons[-1].largeur[1], p.phi_moyen)
        cav = D["cavite"]
        v = Voicing(chamber_m3=cav["V_eff"], hole=Orifice(cav["S_trou"], cav["l_eff"]), shared_chamber=True)
        cm = CoupledReedsModel(reeds=lm, settings=[st, st], voicing=v, muted=(False, True))
        p_on, f_on, _ = seuils(cm)
        amp = ""
        if p_on and avec_amplitude:
            r = cm.simulate(1.0, supply_pa=1.5 * p_on, kick_tip_m=0.1e-3)
            a_mm, al = allure(r.tips[0], r.t)
            amp = f"{a_mm:.3f} ({al})"
        res["coupled_reeds, réseau d'Elmer (chambre + trou de table)"] = (p_on, f_on, amp, p.f_hz)
        print(f"[couplé] {nom} : coupled_reeds : p_on {p_on}, f_on {f_on} ({time.time() - t0:.0f} s)", flush=True)
        for cas, (pon, fon, amp, fl) in res.items():
            lignes.append(dict(anche=nom, modele=cas, f_lame_Hz=round(fl, 2),
                               p_on_Pa=round(pon, 1) if pon else "pas de démarrage",
                               f_jeu_Hz=round(fon, 2) if fon else "",
                               f_jeu_cents_sur_lame=round(1200 * math.log2(fon / fl), 1) if fon else "",
                               amplitude_bout_1p5_seuil_mm=amp,
                               mesure_banc="en attente"))
    return lignes


def ecrire(lignes, nom):
    os.makedirs(RESULTATS, exist_ok=True)
    cles = []
    for l in lignes:
        cles += [k for k in l if k not in cles]
    ch = os.path.join(RESULTATS, nom)
    with open(ch, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cles, delimiter=";")
        w.writeheader()
        w.writerows(lignes)
    print("->", ch, flush=True)


def figures(details):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    noms = [n for n in details if "Z" in details[n]]
    fig, ax = plt.subplots(2, max(1, len(noms)), figsize=(5 * max(1, len(noms)), 7), squeeze=False)
    for j, n in enumerate(noms):
        f, Z, m, Z0, Z1 = details[n]["Z"]
        a = ax[0, j]
        a.loglog(f, np.abs(Z), "k-", lw=1, label="Elmer (fente)")
        a.loglog(f[m], np.abs(Z0), "r--", label="reed_model : cavité fermée")
        a.loglog(f[m], np.abs(Z1), "b:", lw=2, label="calé : 2 résonateurs (V_eff, trou, mode A-B)")
        a.axvline(details[n]["f_el"][0], color="g", lw=0.8)
        a.set_title(n); a.set_xlabel("f (Hz)"); a.set_ylabel("|Z| (Pa.s/m3)"); a.legend(fontsize=8)
        b = ax[1, j]
        x = np.linspace(0, details[n]["lang"].L, 300)
        b.plot(x * 1e3, details[n]["forme_rm"](x), "r--", label="reed_model (N=2)")
        b.plot(x * 1e3, details[n]["forme_el"](x), "k-", label="Elmer")
        b.set_xlabel("x (mm)"); b.set_ylabel("mode 1 / bout"); b.legend(fontsize=8)
    fig.tight_layout()
    ch = os.path.join(RESULTATS, "recalage_rk4.png")
    fig.savefig(ch, dpi=110)
    print("->", ch)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sans-couple", action="store_true")
    ap.add_argument("--amplitude", action="store_true", help="amplitudes par simulation (lent)")
    a = ap.parse_args(argv)
    liste = languettes()
    l1, details = etape_languette(liste)
    ecrire(l1, "recalage_rk4_languette.csv")
    l2 = etape_cavite(liste, details)
    ecrire(l2, "recalage_rk4_cavite.csv")
    figures(details)
    if not a.sans_couple:
        dp, f = reed_model_oscille()
        print(f"[couplé] reed_model d'origine (défauts) : surpression moyenne {dp:.0f} Pa, "
              f"fréquence dominante {f:.1f} Hz (anche à 100 Hz) : il n'auto-oscille pas (audit, défaut 1)")
        l3 = etape_couple(liste, details, a.amplitude)
        l3.insert(0, dict(anche="SECTIONS_DEFAULT", modele="reed_model d'origine (RK4, volume en variable d'état)",
                          f_lame_Hz="", p_on_Pa=f"surpression moyenne {dp:.0f} Pa", f_jeu_Hz=round(f, 1),
                          f_jeu_cents_sur_lame="", amplitude_bout_1p5_seuil_mm="", mesure_banc=""))
        ecrire(l3, "recalage_rk4_couple.csv")


if __name__ == "__main__":
    main()

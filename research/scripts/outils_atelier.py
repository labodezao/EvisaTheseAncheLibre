#!/usr/bin/env python3
"""Outils d'aide à la conception et à la réparation d'accordéons (design_practical).

Chaque chiffre de design_practical qui se calcule se recalcule ici, avec les valeurs
de l'atelier à la place des exemples :

    python research/scripts/outils_atelier.py trou 1 --p 500           # fuite d'un trou rond
    python research/scripts/outils_atelier.py fente --jeu 0.02 --long 100 --portee 5
    python research/scripts/outils_atelier.py chute --volume 10 --temps 60 --p 600
    python research/scripts/outils_atelier.py gazometre --surface 150 --p 500
    python research/scripts/outils_atelier.py cloche --volume 0.4 --p 500 --fuite 0.02
    python research/scripts/outils_atelier.py ressort --trou 8x25 --force 90
    python research/scripts/outils_atelier.py levee --trou 20x15
    python research/scripts/outils_atelier.py soufflet --force 40 --p 1000 --voix 2 \
        --debit-anche 2 --course 0.4 --duree 4
    python research/scripts/outils_atelier.py battement --f 440 --cents 5 10 15 20
    python research/scripts/outils_atelier.py tables     # toutes les tables du livre

Les lois :
- trou (orifice en paroi mince) : q = Cd S sqrt(2 dp / rho), Cd = 0,6 (fuite en p^0,5) ;
- fente plate (joint mal plan, tiroir, cire) : q = w h^3 dp / (12 mu L), loi de Poiseuille
  entre deux plans (fuite en p^1, et en h^3 : jeu divisé par deux = fuite divisée par huit) ;
- soupape tenue fermée : elle décolle quand dp A dépasse la force du ressort à la soupape ;
- levée utile : le « rideau » d'air autour du trou (périmètre P x levée h) égale le trou A
  quand h = A / P ; au-delà, lever plus ne donne plus d'air.
"""
from __future__ import annotations

import argparse
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from banc_recherche.leak import (P_ATM, RHO, equivalent_hole_mm,  # noqa: E402
                                 hole_leak_lpm)

G = 9.81            # m/s²
MU_AIR = 1.8e-5     # Pa s, viscosité de l'air vers 20 °C
LPM = 60000.0       # m³/s -> L/min


# ------------------------------------------------------------------- fuites ---

def fuite_fente_lpm(jeu_mm, longueur_mm, portee_mm, p_pa, mu=MU_AIR):
    """Fuite (L/min) d'un joint plat : fente de hauteur `jeu_mm`, de longueur
    développée `longueur_mm` (le tour du joint) et de portée `portee_mm` (la largeur
    de bois que l'air doit traverser). Loi de Poiseuille plan."""
    h, w, l = jeu_mm * 1e-3, longueur_mm * 1e-3, portee_mm * 1e-3
    return w * h ** 3 * p_pa / (12 * mu * l) * LPM


def jeu_max_mm(fuite_lpm, longueur_mm, portee_mm, p_pa, mu=MU_AIR):
    """Jeu (mm) qu'un joint plat peut avoir pour fuir au plus `fuite_lpm`."""
    q = fuite_lpm / LPM
    w, l = longueur_mm * 1e-3, portee_mm * 1e-3
    return (12 * mu * l * q / (w * p_pa)) ** (1 / 3) * 1e3


def reynolds_fente(jeu_mm, longueur_mm, portee_mm, p_pa, mu=MU_AIR, rho=RHO):
    """Nombre de Reynolds dans la fente : la loi de Poiseuille vaut tant qu'il reste petit."""
    q = fuite_fente_lpm(jeu_mm, longueur_mm, portee_mm, p_pa, mu) / LPM
    v = q / (longueur_mm * 1e-3 * jeu_mm * 1e-3)
    return rho * v * jeu_mm * 1e-3 / mu


def chute(volume_l, temps_s, p_pa):
    """Test de chute : le soufflet balaie `volume_l` en `temps_s` sous `p_pa`.
    Renvoie (fuite en L/min, trou équivalent en mm)."""
    q = volume_l / (temps_s / 60.0)
    return q, equivalent_hole_mm(q, p_pa)


def gazometre(surface_cm2, p_pa):
    """Masse (kg, boîte comprise) qui donne `p_pa`, et descente (cm/min) pour 1 L/min."""
    s = surface_cm2 * 1e-4
    return p_pa * s / G, 1e-3 / s * 100.0


def cloche_demi_temps_s(volume_l, p_pa, fuite_lpm, p_atm=P_ATM):
    """Temps pour qu'une cloche de `volume_l` posée sur une soupape atteigne p/2
    (fuite de type orifice) : t ≈ 0,59 V P / (p_atm Q)."""
    return 0.59 * volume_l * 1e-3 * p_pa / (p_atm * fuite_lpm / LPM)


# ------------------------------------------------------- soupapes, clavier ---

def lire_trou(texte):
    """« 8x25 » (rectangle, mm) ou « d12 » (rond) -> (aire mm², périmètre mm)."""
    t = texte.lower().replace(",", ".")
    if t.startswith("d"):
        d = float(t[1:])
        return math.pi * d * d / 4, math.pi * d
    a, b = (float(x) for x in t.split("x"))
    return a * b, 2 * (a + b)


def levee_utile_mm(aire_mm2, perimetre_mm):
    """Levée au-delà de laquelle la soupape ne donne plus d'air : h = A / P."""
    return aire_mm2 / perimetre_mm


def pression_decollement_pa(force_g, aire_mm2):
    """Pression qui soulève une soupape tenue par `force_g` grammes (force à la soupape)."""
    return force_g * 1e-3 * G / (aire_mm2 * 1e-6)


def force_ressort_g(aire_mm2, p_max_pa, marge=1.5):
    """Force (g, à la soupape) pour qu'aucune soupape ne décolle sous marge x p_max."""
    return marge * p_max_pa * aire_mm2 * 1e-6 / G * 1e3


# ---------------------------------------------------------------- soufflet ---

def fenetre_soufflet(force_n, p_pa, voix, debit_anche_lpm, course_m, duree_s, fuite_lpm=0.0):
    """Section efficace du soufflet (m²) : (mini, maxi).

    maxi : au-delà, le bras ne donne plus `p_pa` avec `force_n` (p = F / S) ;
    mini : en dessous, une course de `course_m` ne nourrit pas `voix` anches
    (plus la fuite) pendant `duree_s` (V = S x course = Q x durée)."""
    q = (voix * debit_anche_lpm + fuite_lpm) / LPM
    return q * duree_s / course_m, force_n / p_pa


# --------------------------------------------------------------- accordage ---

def battement_hz(f_hz, cents):
    """Battement (Hz) entre deux voix écartées de `cents` autour de `f_hz`."""
    return f_hz * (2 ** (cents / 1200) - 1)


# ------------------------------------------------------------------ tables ---

def tables():
    print("Fuite d'un trou rond (L/min), loi d'orifice Cd = 0,6")
    for d in (0.3, 0.5, 1, 2):
        print(f"  {d:>4} mm : " + "  ".join(f"{p} Pa {hole_leak_lpm(d, p):.2f}" for p in (100, 500, 1500)))
    print("\nFuite d'un joint plat à 500 Pa, 100 mm de tour, 5 mm de portée (L/min)")
    for h in (0.01, 0.02, 0.03, 0.05, 0.1):
        print(f"  jeu {h:.2f} mm : {fuite_fente_lpm(h, 100, 5, 500):.3f}"
              f"   (Re {reynolds_fente(h, 100, 5, 500):.1f})")
    print(f"  jeu maxi pour 0,05 L/min : {jeu_max_mm(0.05, 100, 5, 500):.3f} mm")
    print("\nTest de chute, soufflet de 10 L sous 600 Pa")
    for t in (30, 60, 120, 300):
        q, d = chute(10, t, 600)
        print(f"  {t:>4} s : {q:5.1f} L/min, trou {d:.1f} mm")
    m, v = gazometre(150, 500)
    print(f"\nGazomètre 150 cm² : {m:.2f} kg pour 500 Pa ; 1 L/min = {v:.1f} cm/min")
    print(f"Cloche 0,4 L à 500 Pa : 0,02 L/min -> {cloche_demi_temps_s(0.4, 500, 0.02):.1f} s ; "
          f"0,002 L/min -> {cloche_demi_temps_s(0.4, 500, 0.002):.0f} s")
    print("\nSoupape : levée utile et pression de décollement à 90 g (force à la soupape)")
    for trou in ("8x12", "15x15", "20x15"):
        a, p = lire_trou(trou)
        print(f"  {trou:>6} : A {a:6.0f} mm², P {p:5.1f} mm, levée utile {levee_utile_mm(a, p):.1f} mm, "
              f"décolle à {pression_decollement_pa(90, a):6.0f} Pa, "
              f"ressort pour 1,5 x 3 kPa : {force_ressort_g(a, 3000):.0f} g")
    print("\nBattements (Hz, et par minute) autour de La 440")
    for c in (2, 3, 5, 10, 15, 20, 25):
        b = battement_hz(440, c)
        print(f"  {c:>3} cents : {b:.2f} Hz, {60 * b:.0f} /min")


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("trou"); a.add_argument("d", type=float); a.add_argument("--p", type=float, default=500)
    a = sp.add_parser("fente")
    for k in ("jeu", "long", "portee"):
        a.add_argument(f"--{k}", type=float, required=True)
    a.add_argument("--p", type=float, default=500)
    a = sp.add_parser("chute")
    for k in ("volume", "temps"):
        a.add_argument(f"--{k}", type=float, required=True)
    a.add_argument("--p", type=float, default=600)
    a = sp.add_parser("gazometre"); a.add_argument("--surface", type=float, required=True)
    a.add_argument("--p", type=float, default=500)
    a = sp.add_parser("cloche")
    for k in ("volume", "fuite"):
        a.add_argument(f"--{k}", type=float, required=True)
    a.add_argument("--p", type=float, default=500)
    a = sp.add_parser("ressort"); a.add_argument("--trou", required=True)
    a.add_argument("--force", type=float, default=90); a.add_argument("--pmax", type=float, default=3000)
    a = sp.add_parser("levee"); a.add_argument("--trou", required=True)
    a = sp.add_parser("soufflet")
    for k in ("force", "p", "voix", "debit-anche", "course", "duree"):
        a.add_argument(f"--{k}", type=float, required=True)
    a.add_argument("--fuite", type=float, default=0.0)
    a = sp.add_parser("battement"); a.add_argument("--f", type=float, required=True)
    a.add_argument("--cents", type=float, nargs="+", required=True)
    sp.add_parser("tables")
    x = ap.parse_args(argv)

    if x.cmd == "trou":
        print(f"{hole_leak_lpm(x.d, x.p):.3f} L/min")
    elif x.cmd == "fente":
        print(f"{fuite_fente_lpm(x.jeu, x.long, x.portee, x.p):.4f} L/min "
              f"(Reynolds {reynolds_fente(x.jeu, x.long, x.portee, x.p):.1f})")
    elif x.cmd == "chute":
        q, d = chute(x.volume, x.temps, x.p)
        print(f"{q:.2f} L/min, trou équivalent {d:.2f} mm")
    elif x.cmd == "gazometre":
        m, v = gazometre(x.surface, x.p)
        print(f"masse {m:.3f} kg ; 1 L/min = {v:.2f} cm/min de descente")
    elif x.cmd == "cloche":
        print(f"demi-pression en {cloche_demi_temps_s(x.volume, x.p, x.fuite):.1f} s")
    elif x.cmd == "ressort":
        aire, _ = lire_trou(x.trou)
        print(f"décolle à {pression_decollement_pa(x.force, aire):.0f} Pa ; "
              f"pour tenir 1,5 x {x.pmax:.0f} Pa il faut {force_ressort_g(aire, x.pmax):.0f} g à la soupape")
    elif x.cmd == "levee":
        aire, per = lire_trou(x.trou)
        print(f"A {aire:.0f} mm², P {per:.1f} mm, levée utile {levee_utile_mm(aire, per):.2f} mm")
    elif x.cmd == "soufflet":
        smin, smax = fenetre_soufflet(x.force, x.p, x.voix, x.debit_anche, x.course, x.duree, x.fuite)
        verdict = "fenêtre ouverte" if smin <= smax else "aucune section ne convient"
        print(f"section mini {smin * 1e4:.0f} cm², maxi {smax * 1e4:.0f} cm² : {verdict}")
    elif x.cmd == "battement":
        for c in x.cents:
            b = battement_hz(x.f, c)
            print(f"{c:g} cents : {b:.3f} Hz, {60 * b:.1f} par minute")
    else:
        tables()


if __name__ == "__main__":
    main()

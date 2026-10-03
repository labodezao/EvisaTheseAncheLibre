"""Seuil d'auto-entretien d'une anche et résonance de sa chambre : plan d'expérience numérique.

La question
-----------
Comment la chambre du sommier (son volume V et le trou de table qui la ferme, de section S)
change-t-elle :
  - p_on    : la pression de soufflet où l'anche DÉMARRE (seuil bas, bifurcation de Hopf) ;
  - p_haut  : la pression où elle s'arrête de nouveau en poussant plus fort (étouffement,
              languette plaquée dans sa fente), si elle existe dans la plage balayée ;
  - f_on    : la fréquence qui naît au seuil (écart en cents à la lame seule, et à la
              résonance de la chambre) ;
  - et, en régime établi à 2 x p_on : course du bout, débit consommé, puissance rayonnée.

Le modèle
---------
`banc_recherche.coupled_reeds.CoupledReedsModel` (le « petit modèle » du dépôt), réduit à
UNE anche (la seconde est bloquée) : soufflet -> anche -> chambre V -> trou de table
(masse d'air rho*L_eff/S + perte d'orifice) -> canal -> clapet -> dehors. Anche fermée par le
souffle (`ReedSetting`, hypothèse du modèle, cf. docs/audit_deux_anches.md).
`direction='pousser'` : la chambre est EN AVAL de l'anche (anche extérieure) ;
`direction='tirer'` : la chambre est EN AMONT (anche intérieure, dans la case).

La résonance de la chambre f_H se règle par la section du trou S ; la longueur effective
L_eff = épaisseur de table + kappa x rayon équivalent, avec kappa calé sur les calculs Elmer
(`chambre_modes.py --balayage`). C'est la chaîne voulue : Elmer calcule les paramètres
effectifs sur la vraie géométrie, le petit modèle fait le plan d'expérience.

Méthode du seuil : équilibre statique (intégration fortement amortie puis Newton), jacobienne
par différences finies, valeurs propres. Taux de croissance > 0 : l'anche démarre. C'est la
méthode de `FreeReedModel.growth_rate`, appliquée au réseau.

Limites : tout ce qui est dit dans coupled_reeds.py (un mode de lame, valeurs devinées pour
la levée, le jeu, l'épaisseur de plaque ; courses et débits trop grands) ; le seuil absolu
n'est pas recalé sur une mesure. On lit des TENDANCES : comment p_on bouge quand f_H/f_anche
change, pas la valeur de p_on.

Usage : J:\\claude\\venv\\Scripts\\python.exe seuils_cavite.py [--plan rapport|luthier] [--tirer]
Sorties : resultats/seuils_rapport.csv, resultats/seuils_luthier.csv
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import sys
import time

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(ICI, "..", "..")))   # research/
from banc_recherche.coupled_reeds import CoupledReedsModel, Orifice, Voicing, steel_reed  # noqa: E402

C, RHO = 343.0, 1.2


def modele(f_lame, V_m3, S_m2, L_eff_m, direction):
    r1, s1 = steel_reed(f_lame)
    r2, s2 = steel_reed(f_lame)
    v = Voicing(chamber_m3=V_m3, hole=Orifice(S_m2, L_eff_m), shared_chamber=True)
    return CoupledReedsModel(reeds=[r1, r2], settings=[s1, s2], voicing=v,
                             direction=direction, muted=(False, True))


def f_helmholtz_reseau(m):
    """Résonances passives du réseau (anche bloquée) : chambre, trou, canal, clapet, sans pertes.
    Renvoie la plus basse (Hz)."""
    v = m.v
    K = v.gamma * v.patm
    Ca, Cn = v.chamber_m3 / K, v.channel_m3 / K
    Lh, Lp = m.L_hole, m.L_pal
    # états [p_c, q_h, p_n, q_p] ; p_c' = -q_h/Ca ; q_h' = (p_c - p_n)/Lh ; p_n' = (q_h - q_p)/Cn ; q_p' = p_n/Lp
    A = np.array([[0, -1 / Ca, 0, 0], [1 / Lh, 0, -1 / Lh, 0], [0, 1 / Cn, 0, -1 / Cn], [0, 0, 1 / Lp, 0]])
    w = np.sort(np.abs(np.linalg.eigvals(A).imag))
    w = w[w > 1.0]
    return float(w[0] / (2 * np.pi))


class Stabilite:
    """Équilibre et taux de croissance du réseau à une anche, pour une pression P."""

    def __init__(self, m):
        self.m = m
        lay = m._layout()
        self.n = lay["size"]
        self.idx = [0, 1, lay["p_ch"], lay["q_h"], lay["p_n"], lay["q_p"]]
        self.s = None

    def _rk4(self, s, P, dt, n):
        d = self.m.deriv
        for _ in range(n):
            k1 = d(s, P)
            k2 = d([a + 0.5 * dt * b for a, b in zip(s, k1)], P)
            k3 = d([a + 0.5 * dt * b for a, b in zip(s, k2)], P)
            k4 = d([a + dt * b for a, b in zip(s, k3)], P)
            s = [a + dt / 6 * (b + 2 * c + 2 * e + f) for a, b, c, e, f in zip(s, k1, k2, k3, k4)]
        return s

    def equilibre(self, P):
        from scipy.optimize import root
        m = self.m
        s = list(self.s) if self.s is not None else [0.0] * self.n
        c0 = m.c_damp[0]
        m.c_damp[0] = 2 * 0.7 * math.sqrt(m.k[0] * m.m[0])       # lame très amortie : va au repos
        try:
            s = self._rk4(s, P, 1 / (22050 * 8), 2000 if self.s is not None else 6000)
        finally:
            m.c_damp[0] = c0
        sc = np.array([max(abs(s[i]), 1e-9) for i in self.idx])

        def F(z):
            s2 = list(s)
            for j, i in enumerate(self.idx):
                s2[i] = z[j] * sc[j]
            d = m.deriv(s2, P)
            return [d[i] / sc[j] for j, i in enumerate(self.idx)]

        sol = root(F, [s[i] / sc[j] for j, i in enumerate(self.idx)], method="hybr", options={"xtol": 1e-12})
        z = sol.x if sol.success else [s[i] / sc[j] for j, i in enumerate(self.idx)]
        for j, i in enumerate(self.idx):
            s[i] = z[j] * sc[j]
        self.s = s
        return s

    def croissance(self, P):
        """(taux de croissance max en 1/s, fréquence associée en Hz) à la pression P."""
        try:
            s = self.equilibre(P)
        except (FloatingPointError, OverflowError, ValueError):
            self.s = None
            return float("nan"), float("nan")
        if not all(math.isfinite(x) for x in s):
            self.s = None
            return float("nan"), float("nan")
        m = self.m
        J = np.zeros((len(self.idx), len(self.idx)))
        for j, i in enumerate(self.idx):
            h = 1e-6 * max(abs(s[i]), {0: 1e-3, 1: 1e-8}.get(j, 1e-6 if j % 2 else 1.0))
            sp, sm = list(s), list(s)
            sp[i] += h
            sm[i] -= h
            dp, dm = m.deriv(sp, P), m.deriv(sm, P)
            J[:, j] = [(dp[ii] - dm[ii]) / (2 * h) for ii in self.idx]
        if not np.isfinite(J).all():
            return float("nan"), float("nan")                      # calcul divergé : ni oui ni non
        ev = np.linalg.eigvals(J)
        osc = ev[np.abs(ev.imag) > 2 * np.pi * 20]                  # modes oscillants seulement
        if osc.size == 0:
            return -np.inf, float("nan")
        k = int(np.argmax(osc.real))
        return float(osc[k].real), float(abs(osc[k].imag) / (2 * np.pi))


def seuils(m, p_min=10.0, p_max=8000.0, n=28):
    """p_on, f_on, p_haut (None si hors plage) par balayage géométrique puis dichotomie."""
    st = Stabilite(m)
    Ps = np.geomspace(p_min, p_max, n)
    g = [st.croissance(P)[0] > 0 for P in Ps]

    def dicho(a, b, signe_b):
        st.s = None
        st.equilibre(a)
        for _ in range(14):
            c = math.sqrt(a * b)
            if (st.croissance(c)[0] > 0) == signe_b:
                b = c
            else:
                a = c
        return b

    p_on = p_haut = None
    for i in range(n - 1):
        if p_on is None and not g[i] and g[i + 1]:
            p_on = dicho(Ps[i], Ps[i + 1], True)
        elif p_on is not None and g[i] and not g[i + 1]:
            p_haut = dicho(Ps[i], Ps[i + 1], False)
            break
    if p_on is None and g[0]:
        p_on = Ps[0]                                               # instable dès le bas
    f_on = float("nan")
    if p_on is not None:
        st.s = None
        f_on = st.croissance(p_on * 1.02)[1]
    return p_on, f_on, p_haut


def regime(m, P, dur=0.4, kick_m=0.3e-3):
    """Course du bout (mm), fréquence jouée (Hz), débit (L/s), puissance rayonnée (dB re 1 pW),
    et l'allure : « établi », « s'éteint » ou « croît », à la pression P.

    La languette est lancée (`kick_m`) pour atteindre vite le cycle. ATTENTION (vérifié le
    03/10/2026) : près du seuil, le taux de croissance ne vaut que quelques 1/s ; une oscillation
    lancée sous le seuil met des secondes à mourir et ressemble, sur 0,4 s, à de l'hystérésis.
    D'où l'allure, lue sur deux fenêtres de la partie établie : le taux de variation de la course,
    ln(c2/c1)/dt, sous -0,5 1/s est « s'éteint » (ce n'est pas un régime : valeurs à écarter),
    au-dessus de +0,5 1/s « croît ». Un cycle limite donne un taux proche de 0."""
    try:
        r = m.simulate(dur, supply_pa=P, kick_tip_m=kick_m)
    except FloatingPointError:
        return float("nan"), float("nan"), float("nan"), float("nan"), "diverge"
    k = r.steady()
    tip = r.tips[0][k]
    n = tip.size
    c1, c2 = float(np.ptp(tip[: n // 2])), float(np.ptp(tip[n // 2:]))
    dt = (r.t[k][-1] - r.t[k][0]) / 2
    taux = math.log(max(c2, 1e-15) / max(c1, 1e-15)) / dt if dt > 0 else 0.0
    allure = "s'éteint" if taux < -0.5 else ("croît" if taux > 0.5 else "établi")
    course = c2 * 1e3
    if course < 0.01:
        return course, float("nan"), r.consumption()["pallet"] * 1e3, float("nan"), "silence"
    W = r.radiated_power()
    return (course, r.frequencies()[0], r.consumption()["pallet"] * 1e3,
            10 * math.log10(max(W, 1e-30) / 1e-12), allure)

def section_pour(f_vise, f_lame, V, table, kappa, direction, S_max=400e-6):
    """Section du trou qui place la résonance du réseau à f_vise (None si > S_max)."""
    S = 1e-4
    for _ in range(40):
        L = table + kappa * math.sqrt(S / math.pi)
        m = modele(f_lame, V, S, L, direction)
        fH = f_helmholtz_reseau(m)
        if abs(fH / f_vise - 1) < 1e-4:
            break
        S = min(S * (f_vise / fH) ** 1.6, 4 * S_max)
    return (S, L, m, fH) if S <= S_max else None


def ecrire(lignes, nom):
    os.makedirs(os.path.join(ICI, "resultats"), exist_ok=True)
    cles = []
    for l in lignes:
        cles += [k for k in l if k not in cles]
    chemin = os.path.join(ICI, "resultats", nom)
    with open(chemin, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cles, delimiter=";")
        w.writeheader()
        w.writerows(lignes)
    print("->", chemin, flush=True)


def ligne_seuil(m, f_lame, fH, S, L, V, direction, pressions):
    t0 = time.time()
    p_on, f_on, p_haut = seuils(m)
    d = dict(f_lame_Hz=f_lame, direction=direction, V_cm3=round(V * 1e6, 2), S_mm2=round(S * 1e6, 1),
             L_eff_mm=round(L * 1e3, 2), fH_Hz=round(fH, 1), fH_sur_flame=round(fH / f_lame, 3),
             p_on_Pa=round(p_on, 1) if p_on else "",
             f_on_cents=round(1200 * math.log2(f_on / f_lame), 1) if f_on == f_on else "",
             p_haut_Pa=round(p_haut, 1) if p_haut else "")
    for P in pressions:
        course, f_j, debit, LW, allure = regime(m, P)
        joue = course > 0.02 and allure in ("établi", "croît")
        d[f"allure_{P}Pa"] = allure
        d[f"course_{P}Pa_mm"] = round(course, 3)
        d[f"cents_{P}Pa"] = round(1200 * math.log2(f_j / f_lame), 1) if joue and f_j == f_j else ""
        d[f"debit_{P}Pa_Ls"] = round(debit, 4) if debit == debit else ""
        d[f"LW_{P}Pa_dB"] = round(LW, 1) if joue and LW == LW else ""
    d["duree_s"] = round(time.time() - t0, 1)
    print(d, flush=True)
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", choices=("rapport", "luthier"), default="luthier",
                    help="rapport : f_H/f_lame balayé ; luthier : section du trou x volume x lame")
    ap.add_argument("--tirer", action="store_true", help="calculer aussi le sens tiré")
    ap.add_argument("--kappa", type=float, default=1.9,
                    help="L_eff = table + kappa x rayon équivalent (Elmer, 03/10/2026 : 1,03 intérieur "
                         "+ 0,85 extérieur ; le plan du 03/10 a tourné avec 1,55)")
    ap.add_argument("--table", type=float, default=8e-3)
    a = ap.parse_args()
    # « tirer » donne exactement les mêmes taux que « pousser » dans ce réseau (chaîne
    # symétrique, vérifié le 03/10/2026) : un seul sens suffit, sauf --tirer.
    sens = ("pousser", "tirer") if a.tirer else ("pousser",)
    lames = [700.0, 1000.0, 1400.0]
    lignes = []
    if a.plan == "rapport":
        V = 10.2e-6                                                   # cases de la chambre 12 (Elmer)
        for f_lame in lames:
            for direction in sens:
                for rap in [0.5, 0.7, 0.85, 1.0, 1.1, 1.2, 1.4, 1.7, 2.0]:
                    r = section_pour(rap * f_lame, f_lame, V, a.table, a.kappa, direction)
                    if r is None:
                        print(f"f_lame {f_lame} rapport {rap} : trou > 400 mm2, sauté", flush=True)
                        continue
                    S, L, m, fH = r
                    lignes.append(ligne_seuil(m, f_lame, fH, S, L, V, direction, pressions=(1000,)))
        ecrire(lignes, "seuils_rapport.csv")
    else:
        volumes = {"chambre 1": 18.3e-6, "chambre 12": 10.2e-6}          # cases seules, Elmer (03/10/2026)
        for f_lame in lames:
            for nom_v, V in volumes.items():
                for S in (25e-6, 50e-6, 100e-6, 200e-6, 400e-6):
                    for direction in sens:
                        L = a.table + a.kappa * math.sqrt(S / math.pi)
                        m = modele(f_lame, V, S, L, direction)
                        fH = f_helmholtz_reseau(m)
                        d = ligne_seuil(m, f_lame, fH, S, L, V, direction, pressions=(300, 1000, 2000))
                        d["chambre"] = nom_v
                        lignes.append(d)
        ecrire(lignes, "seuils_luthier.csv")


if __name__ == "__main__":
    main()

"""La grosse basse qui joue derrière son trou et sa soupape : modèle temporel (RK4).

Ce que fait ce script, en mots
------------------------------
1. La lame : acier 74 x 8 x 1 mm (Ewen, 05/10/2026), encastrée, avec une masse au bout réglée
   pour donner la note (mi0 = 41,2 Hz par défaut). Une lame uniforme de 1 mm sur 74 mm vibre
   à 153 Hz : sans masse au bout ce n'est pas une basse. La masse est donc une HYPOTHÈSE
   (calculée, pas mesurée : environ 14 g pour mi0). Premier mode par Euler-Bernoulli exact
   (`banc_recherche.languette`, vérifié contre Elmer à 0,4 % dans `fem/README.md`).
2. L'écoulement dans la fente : le réglage « anche fermée par le souffle » de
   `coupled_reeds.ReedSetting` (levée au repos, plaque, jeu latéral 0,05 mm) ; la languette
   entre dans la plaque, l'air passe par le jeu, puis ressort. Rien d'autre n'est changé.
3. Le réseau derrière l'anche : UN seul résonateur, avec les valeurs d'Elmer
   (`trou_soupape_bb95.py` : ressort d'air C, masse d'air L du trou ET du rideau, rayonnement R)
   et les pertes d'orifice non linéaires rho.q|q|/2.(1/(Cd.A_trou)² + 1/(Cd.A_rideau)²) :
   le trou et le rideau de la soupape sont deux orifices en série, traversés par le même débit.
   Sans le CSV d'Elmer, les formules de la note (constantes localisées) servent de repli.
   État : (x, x', p_chambre, q_trou). RK4 suréchantillonné, 3 s (la lame met ~1 s à s'établir :
   1/(zeta.omega) = 0,97 s), mesures sur la dernière demi-seconde.
4. Pour chaque trou et chaque levée : à 2 kPa, le débit moyen et de crête (facteur de crête),
   la section efficace de l'anche, la pression dans la chambre (moyenne et à la crête : la
   « part perdue »), la fréquence de jeu, l'amplitude du bout, le spectre rayonné (niveau du
   fondamental, part au-dessus de 500 Hz), le temps d'attaque ; puis le seuil de parole par
   bissection. Référence : le même calcul sans trou (chambre ouverte, pertes nulles).

Ce qui n'est pas modélisé : le second mode de la lame, la torsion, la seconde anche du
sommier à 3 voix (bouchée), les pertes visqueuses dans un rideau de 1 mm, le dehors fermé
(caisse). Les Cd (0,65) sont une hypothèse ; le vrai coefficient d'un rideau sous soupape
est entre 0,6 et 1.

Usage (depuis `research\\fem\\sommier\\`) :
  J:\\claude\\venv\\Scripts\\python.exe trou_soupape_jeu.py                 le plan (4 trous x 5 levées)
  ... --note 82.4 --trou 12x12 --levee 3                               un cas
  ... --seuils                                                         avec les seuils (plus long)
  ... --profil grattee                                                 lame grattée (hypothèse) au lieu de la lame uniforme
Sortie : resultats/trou_soupape_jeu.csv
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import sys

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(ICI, "..", "..")))    # research/
sys.path.insert(0, ICI)
from banc_recherche.languette import Languette, Troncon, euler_bernoulli, parametres_modaux, LanguetteModale, reglage  # noqa: E402
from banc_recherche.coupled_reeds import CoupledReedsModel, Voicing, dominant_frequency  # noqa: E402
import trou_soupape_bb95 as elm  # noqa: E402

RHO, C_SON = 1.2, 343.0
RESULTATS = os.path.join(ICI, "resultats")

# --- La lame et son réglage (Ewen, 05/10/2026 ; le reste : hypothèses) -----------------------
LAME = dict(L=74e-3, b=8e-3, e=1.0e-3)
JEU = 0.05e-3                 # jeu lame / plaquette, de chaque côté et au bout
# Levée au repos : HYPOTHÈSE = la flèche statique de la lame vers 2,5 kPa (règle du harmoniste :
# au plus fort, le bout affleure la plaque). Balayage du 05/10/2026 : en dessous la lame se
# plaque à 2 kPa, au-dessus elle consomme sans osciller.
LEVEE_REPOS = {"uniforme": 0.5e-3, "grattee": 2.0e-3}
PLAQUE = elm.PLAQUE * 1e-3
ZETA = 0.004
CD = 0.65
P_JEU = 2000.0


PROFILS = {
    # Ewen, 05/10/2026 : 74 x 8 mm, 1 mm d'épaisseur constante.
    "uniforme": [(74e-3, 8e-3, (1.0e-3, 1.0e-3))],
    # HYPOTHÈSE, à la manière de ses lames (R12-grave 0,35/0,2/0,275/1,5 mm ; CAO 2019
    # 0,335 -> 0,10 -> 0,248 puis bloc de 1,4 mm) : grattée de 0,8 à 0,6 mm, bloc de 1 mm sur 14 mm.
    "grattee": [(12e-3, 8e-3, (0.8e-3, 0.6e-3)), (48e-3, 8e-3, (0.6e-3, 0.6e-3)),
                (14e-3, 8e-3, (1.0e-3, 1.0e-3))],
}


def lame_basse(f_note=41.2, zeta=ZETA, profil="uniforme"):
    """La lame d'Ewen (ou le profil gratté) avec une masse au bout réglée (bissection) pour
    donner `f_note`. Renvoie (lame modale, réglage, infos)."""
    tr = [Troncon(L_, b_, e_, "acier") for L_, b_, e_ in PROFILS[profil]]
    f_nue = float(euler_bernoulli(Languette(tr), n_modes=1, f_max=2000.0, n_balayage=400)[0])
    if f_note >= f_nue:
        raise ValueError(f"la lame nue vibre à {f_nue:.1f} Hz : pas besoin de masse pour {f_note} Hz")
    lo, hi = 0.0, 0.2

    def f_de(m):
        return float(euler_bernoulli(Languette(tr, masses=[(LAME["L"], m)]), n_modes=1, f_max=4 * f_note, n_balayage=200)[0])

    for _ in range(24):
        mid = 0.5 * (lo + hi)
        if f_de(mid) > f_note:
            lo = mid
        else:
            hi = mid
    m = 0.5 * (lo + hi)
    lang = Languette(tr, masses=[(LAME["L"], m)], nom=f"BB95 {profil} {f_note:g} Hz")
    p = parametres_modaux(lang)
    lame = LanguetteModale(p, LAME["L"], LAME["b"] + 2 * JEU, zeta=zeta)
    e_bout = tr[-1].epaisseur[1]
    st = reglage(LEVEE_REPOS[profil], PLAQUE, e_bout, LAME["b"] + 2 * JEU, LAME["b"], p.phi_moyen)
    return lame, st, dict(profil=profil, levee_repos_mm=LEVEE_REPOS[profil] * 1e3, f_nue_Hz=f_nue, masse_bout_g=m * 1e3, f1_Hz=p.f_hz, m_eff_g=p.m_eff * 1e3,
                          k_eff_N_m=p.k_eff, gamma_m2=p.gamma, phi_moyen=p.phi_moyen,
                          fleche_statique_mm=p.gamma * P_JEU / p.k_eff * 1e3)


# --- Le réseau (valeurs d'Elmer ou de la note) ------------------------------------------------
def reseau_elmer(trou, levee, csv_path=None):
    """L, C, R du CSV d'Elmer pour (trou, levée) ; None si absent."""
    csv_path = csv_path or os.path.join(RESULTATS, "trou_soupape_bb95.csv")
    if not os.path.exists(csv_path):
        return None
    with open(csv_path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh, delimiter=";"):
            if r["trou"] == trou and abs(float(r["levee_mm"]) - levee) < 1e-6:
                return dict(L=float(r["L_elmer_kg_m4"]), C=float(r["V_eff_cm3"]) * 1e-6 / (RHO * C_SON ** 2),
                            R=float(r["R_Pa_s_m3"]), source="elmer", f_H=float(r["f_H_elmer_Hz"]))
    return None


def reseau_note(trou, levee, V_cm3=40.6):
    a, b = elm.TROUS[trou]
    n = elm.formules_note((a, b), levee, V_cm3=V_cm3)
    C = V_cm3 * 1e-6 / (RHO * C_SON ** 2)
    return dict(L=n["L_kg_m4"], C=C, R=0.0, source="note", f_H=n["f_H_Hz"])


class BasseTrouSoupape:
    """Une anche, sa chambre, son trou et le rideau de sa soupape (poussé)."""

    def __init__(self, lame, st, trou, levee_mm, reseau, cd=CD, sans_trou=False):
        self.cr = CoupledReedsModel(reeds=[lame, lame], settings=[st, st], voicing=Voicing(),
                                    muted=(False, True))
        self.m, self.k, self.c = self.cr.m[0], self.cr.k[0], self.cr.c_damp[0]
        self.g = self.cr.g[0]
        a, b = elm.TROUS[trou]
        self.A_trou = a * b * 1e-6
        self.A_rideau = 2 * (a + b) * 1e-3 * levee_mm * 1e-3
        self.L, self.C, self.R = reseau["L"], reseau["C"], reseau["R"]
        self.cd = cd
        if sans_trou:
            # chambre largement ouverte : pas de perte, masse d'air d'un trou de 50 x 50 mm, 5 mm
            self.L, self.R = RHO * 0.005 / 2.5e-3, 0.0
            self.perte = 0.0
        else:
            self.perte = RHO / 2 * (1 / (cd * self.A_trou) ** 2 + 1 / (cd * self.A_rideau) ** 2)

    def deriv(self, s, P):
        x, xd, p_c, q_h = s
        dp = P - p_c
        q_r, _ = self.cr._reed_flow(0, dp, x)
        part = self.cr._series(0, x)[1]
        xdd = (dp * part * self.g - self.k * x - self.c * xd) / self.m
        dp_c = (q_r - q_h) / self.C
        dq_h = (p_c - self.R * q_h - self.perte * q_h * abs(q_h)) / self.L
        return (xd, xdd, dp_c, dq_h), q_r

    def simuler(self, dur=3.0, P=P_JEU, fs=8000.0, sur=4, attaque_s=0.02, x0=1e-6):
        n = int(dur * fs)
        dt = 1.0 / (fs * sur)
        s = (x0, 0.0, 0.0, 0.0)
        X = np.zeros(n); PC = np.zeros(n); QR = np.zeros(n); QH = np.zeros(n)
        t = 0.0
        for j in range(n):
            for _ in range(sur):
                Pt = P * min(1.0, t / attaque_s) if attaque_s > 0 else P
                k1, _ = self.deriv(s, Pt)
                k2, _ = self.deriv(tuple(a + 0.5 * dt * b for a, b in zip(s, k1)), Pt)
                k3, _ = self.deriv(tuple(a + 0.5 * dt * b for a, b in zip(s, k2)), Pt)
                k4, _ = self.deriv(tuple(a + dt * b for a, b in zip(s, k3)), Pt)
                s = tuple(a + dt / 6 * (b + 2 * c_ + 2 * d + e) for a, b, c_, d, e in zip(s, k1, k2, k3, k4))
                t += dt
            if not all(math.isfinite(v) for v in s):
                raise FloatingPointError("divergence : augmenter `sur`")
            _, q_r = self.deriv(s, P)
            X[j], PC[j], QR[j], QH[j] = s[0], s[2], q_r, s[3]
        return dict(t=np.arange(n) / fs, x=X, p_ch=PC, q_r=QR, q_h=QH, fs=fs, P=P)


# --- Les mesures sur une simulation ---------------------------------------------------------
def mesures(sim, f1, t_etabli=0.5):
    fs, P = sim["fs"], sim["P"]
    m = sim["t"] >= sim["t"][-1] - t_etabli
    x, pc, qr, qh = sim["x"][m], sim["p_ch"][m], sim["q_r"][m], sim["q_h"][m]
    amp = 0.5 * (x.max() - x.min())
    out = dict(amplitude_bout_mm=amp * 1e3)
    if amp < 20e-6:
        out.update(joue=False)
        return out
    f_jeu = dominant_frequency(x - x.mean(), fs)
    q_moy, q_cr = qr.mean(), qr.max()
    v_jet = math.sqrt(2 * P / RHO)
    # spectre rayonné : p ~ dq_h/dt
    pr = np.gradient(qh) * fs
    n = pr.size
    S = np.abs(np.fft.rfft((pr - pr.mean()) * np.hanning(n))) ** 2
    f = np.fft.rfftfreq(n, 1 / fs)
    i1 = int(np.argmin(np.abs(f - f_jeu)))
    b = max(1, int(0.25 * f_jeu * n / fs))
    e_fond = S[max(0, i1 - b):i1 + b + 1].sum()
    e_tot = S[1:].sum()
    centroide = float((f[1:] * S[1:]).sum() / e_tot) if e_tot > 0 else float("nan")
    # temps d'attaque : enveloppe du bout, 10 à 90 % de l'amplitude établie
    env = np.abs(sim["x"] - sim["x"].mean())
    w = max(1, int(fs / f1))
    env = np.array([env[i:i + w].max() for i in range(0, env.size - w, w)])
    te = np.arange(env.size) * w / fs
    cible = amp
    try:
        t10 = te[np.argmax(env >= 0.1 * cible)]
        t90 = te[np.argmax(env >= 0.9 * cible)]
        attaque = float(t90 - t10)
    except ValueError:
        attaque = float("nan")
    out.update(joue=True, f_jeu_Hz=float(f_jeu), ecart_cents=1200 * math.log2(f_jeu / f1),
               q_moyen_L_s=q_moy * 1e3, q_crete_L_s=q_cr * 1e3, facteur_crete=q_cr / q_moy,
               A_anche_eff_mm2=q_moy / (CD * v_jet) * 1e6, A_crete_mm2=q_cr / (CD * v_jet) * 1e6,
               p_ch_moy_pct=100 * pc.mean() / P, p_ch_crete_pct=100 * pc.max() / P,
               p_ch_cc_pct=100 * (pc.max() - pc.min()) / P,
               niveau_fond_dB=10 * math.log10(e_fond + 1e-30), part_sup_500Hz_pct=(100 * S[1:][f[1:] > 500].sum() / e_tot) if e_tot > 0 else float("nan"),
               centroide_Hz=centroide, attaque_10_90_s=attaque)
    return out


def seuil(modele, f1, lo=20.0, hi=P_JEU, n=7, dur=3.0):
    """Pression de démarrage par bissection (demi-marche d'incertitude)."""
    if not mesures(modele.simuler(dur=dur, P=hi), f1).get("joue"):
        return float("nan"), float("nan")
    for _ in range(n):
        mid = math.sqrt(lo * hi)
        if mesures(modele.simuler(dur=dur, P=mid), f1).get("joue"):
            hi = mid
        else:
            lo = mid
    return math.sqrt(lo * hi), (hi - lo) / 2


def un_cas(trou, levee, f_note=41.2, avec_seuil=False, source="auto", sans_trou=False, profil="uniforme", cache={}):
    if (f_note, profil) not in cache:
        cache[(f_note, profil)] = lame_basse(f_note, profil=profil)
    lame, st, info = cache[(f_note, profil)]
    r = (reseau_elmer(trou, levee) if source in ("auto", "elmer") else None) or reseau_note(trou, levee)
    mod = BasseTrouSoupape(lame, st, trou, levee, r, sans_trou=sans_trou)
    sim = mod.simuler(P=P_JEU)
    res = dict(trou="sans" if sans_trou else trou, levee_mm=levee, note_Hz=f_note, profil=profil, reseau=r["source"],
               f_H_Hz=r["f_H"], L_kg_m4=r["L"], V_eff_cm3=r["C"] * RHO * C_SON ** 2 * 1e6, R=r["R"],
               A_rideau_mm2=mod.A_rideau * 1e6, masse_bout_g=info["masse_bout_g"], f1_Hz=info["f1_Hz"],
               k_eff_N_m=info["k_eff_N_m"], fleche_statique_mm=info["fleche_statique_mm"],
               levee_repos_mm=info["levee_repos_mm"])
    res.update(mesures(sim, info["f1_Hz"]))
    if avec_seuil:
        p_on, dp = seuil(mod, info["f1_Hz"])
        res.update(p_on_Pa=p_on, p_on_incert_Pa=dp)
    return res


def ecrire(res, nom="trou_soupape_jeu.csv"):
    os.makedirs(RESULTATS, exist_ok=True)
    cles = []
    for r in res:
        for k in r:
            if k not in cles:
                cles.append(k)
    with open(os.path.join(RESULTATS, nom), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cles, delimiter=";")
        w.writeheader()
        for r in res:
            w.writerow({k: (f"{v:.5g}" if isinstance(v, float) else v) for k, v in r.items()})


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--note", type=float, default=41.2)
    ap.add_argument("--trou")
    ap.add_argument("--levee", type=float)
    ap.add_argument("--seuils", action="store_true")
    ap.add_argument("--source", default="auto", choices=["auto", "elmer", "note"])
    ap.add_argument("--sortie", default="trou_soupape_jeu.csv")
    ap.add_argument("--profil", default="grattee", choices=list(PROFILS))
    a = ap.parse_args()
    if a.trou:
        r = un_cas(a.trou, a.levee or 3.0, a.note, a.seuils, a.source, profil=a.profil)
        for k, v in r.items():
            print(f"{k:22s} {v}")
        return
    res = [un_cas("20x15", 6.0, a.note, a.seuils, a.source, sans_trou=True, profil=a.profil)]
    print("référence sans trou :", {k: round(v, 3) if isinstance(v, float) else v for k, v in res[0].items()})
    for trou in elm.TROUS:
        for lev in elm.LEVEES:
            r = un_cas(trou, lev, a.note, a.seuils and lev in (1.0, 3.0, 6.0), a.source, profil=a.profil)
            res.append(r)
            print(f"{trou:6s} levée {lev:g} mm ({r['reseau']}) : joue {r.get('joue')} f {r.get('f_jeu_Hz', 0):.2f} Hz "
                  f"({r.get('ecart_cents', 0):+.1f} c) q {r.get('q_moyen_L_s', 0):.3f} L/s crête x{r.get('facteur_crete', 0):.2f} "
                  f"A_eff {r.get('A_anche_eff_mm2', 0):.1f} mm² p_ch moy {r.get('p_ch_moy_pct', 0):.1f} % crête "
                  f"{r.get('p_ch_crete_pct', 0):.1f} % fond {r.get('niveau_fond_dB', 0):.1f} dB >500 Hz "
                  f"{r.get('part_sup_500Hz_pct', 0):.1f} % attaque {r.get('attaque_10_90_s', 0):.3f} s"
                  + (f" p_on {r['p_on_Pa']:.0f} Pa" if 'p_on_Pa' in r else ""), flush=True)
            ecrire(res, a.sortie)


if __name__ == "__main__":
    main()

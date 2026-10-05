"""La grosse basse qui joue derrière son trou et sa soupape : modèle temporel (RK4).

Ce que fait ce script, en mots
------------------------------
1. La lame (Ewen, 05/10/2026, correction du premier calcul) : acier 74 x 8 x 1 mm, NUE (pas de
   masse au bout), jeu 0,05 mm, levée de l'ANCHE au repos 1 mm (règle d'atelier : à peu près
   l'épaisseur de la lame). C'est une lame de ré#. La lame uniforme de 74 mm vibre à 153,1 Hz
   (Euler-Bernoulli exact, `banc_recherche.languette`) : 28 cents sous ré# = 155,56 Hz
   (ré#2 en notation française la3 = 440 Hz ; D#3 en notation scientifique). On l'accorde sur
   155,56 Hz en raccourcissant la longueur LIBRE à 73,4 mm (0,6 mm sous le rivet ou le talon :
   dans l'incertitude sur E et sur l'encastrement) ; la fente reste de 74 mm.
   Le premier calcul (PR #44) prenait une masse de 14,4 g au bout (mi0 = 41,2 Hz) et une levée
   au repos de 0,5 mm : ces deux hypothèses étaient fausses (git log pour l'ancien code).
2. L'écoulement dans la fente : le réglage « anche fermée par le souffle » de
   `coupled_reeds.ReedSetting` (levée au repos, plaquette 2,5 mm, jeu latéral 0,05 mm).
3. Le réseau derrière l'anche : UN résonateur avec les valeurs d'Elmer (`trou_soupape_bb95.py` :
   ressort d'air C, masse d'air L du trou ET du rideau, rayonnement R ; la géométrie n'a pas
   changé, Elmer n'est pas relancé) et les pertes d'orifice non linéaires
   rho.q|q|/2.(1/(Cd.A_trou)² + 1/(Cd.A_rideau)²) : trou et rideau de soupape en série.
   Pour une levée de SOUPAPE h qui varie (ouverture), L(h) = L0 + a/h, ajusté sur les 5 levées
   d'Elmer de ce trou.
4. Deux façons de faire parler la lame (le transitoire, ce qui compte pour le musicien) :
   - « soupape » : le soufflet est déjà en pression P, la chambre aussi (soupape fermée) ; la
     soupape s'ouvre de 0 à h en `t_ouv` (10 ms par défaut). La chambre se vide, la différence
     de pression s'installe sur l'anche et la lame part.
   - « soufflet » : la soupape est déjà ouverte, le soufflet monte de 0 à P en 20 ms.
   Mesures, depuis t = 0 (début d'ouverture ou de montée) : la lame « parle » quand l'enveloppe
   (demi crête-à-crête sur une période) atteint 10 % de l'amplitude établie, puis 90 % ; en ms et
   en périodes. Et le temps où la différence de pression sur l'anche (moyenne sur une période)
   atteint 90 % de sa valeur établie.
5. En régime établi (dernière demi-seconde) : débit moyen et de crête (facteur de crête), section
   efficace de l'anche, pression dans la chambre (moyenne et à la crête : la « part perdue »),
   fréquence de jeu et écart en cents à la lame, amplitude du bout, spectre rayonné. Seuil de
   parole par bissection (scénario soufflet).

Ce qui n'est pas modélisé : le second mode de la lame, la torsion, la seconde anche du sommier
(bouchée), les pertes visqueuses dans un rideau de 1 mm, la caisse (dehors libre), le terme
q.dL/dt pendant l'ouverture. Les Cd (0,65) et l'amortissement de la lame (zeta = 0,004) sont des
hypothèses ; le temps de réponse dépend de zeta (voir `--sensibilite`).

Usage (depuis `research\\fem\\sommier\\`) :
  J:\\claude\\venv\\Scripts\\python.exe trou_soupape_jeu.py                 le plan (4 trous x 5 levées x 1 et 2 kPa)
  ... --trou 12x12 --levee 3 --pression 2000                          un cas
  ... --seuils                                                         avec les seuils (plus long)
  ... --sensibilite                                                    ce qui allonge ou raccourcit la réponse
Sorties : resultats/trou_soupape_jeu.csv, resultats/trou_soupape_reponse_sensibilite.csv
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
LAME = dict(L=74e-3, b=8e-3, e=1.0e-3)   # lame nue, épaisseur constante
F_NOTE = 155.56                          # ré# (ré#2 français, D#3 scientifique), la = 440 Hz
JEU = 0.05e-3                            # jeu lame / plaquette
LEVEE_REPOS = 1.0e-3                     # levée de l'ANCHE au repos (bout au-dessus de la plaquette)
PLAQUE = elm.PLAQUE * 1e-3
ZETA = 0.004
CD = 0.65
PRESSIONS = (1000.0, 2000.0)
P_JEU = 2000.0
T_OUV = 0.010                            # durée d'ouverture de la soupape (hypothèse : appui vif)
H_MIN = 0.02e-3                          # soupape « fermée » : fuite de 0,02 mm (évite 1/0)
R_RAYONNEMENT = RHO * (2 * math.pi * F_NOTE) ** 2 / (4 * math.pi * C_SON)   # monopôle, Pa.s/m³


def lame_nue(f_note=F_NOTE, zeta=ZETA, levee_repos=LEVEE_REPOS):
    """La lame nue 74 x 8 x 1 mm, accordée sur `f_note` par sa longueur libre (None : 74 mm).
    Renvoie (lame modale, réglage, infos)."""
    f_74 = float(euler_bernoulli(Languette([Troncon(LAME["L"], LAME["b"], (LAME["e"], LAME["e"]), "acier")]),
                                 n_modes=1, f_max=2000.0, n_balayage=400)[0])
    L_libre = LAME["L"] if f_note is None else LAME["L"] * math.sqrt(f_74 / f_note)   # f ~ 1/L² (poutre uniforme)
    lang = Languette([Troncon(L_libre, LAME["b"], (LAME["e"], LAME["e"]), "acier")], nom="BB95 lame nue")
    p = parametres_modaux(lang)
    lame = LanguetteModale(p, LAME["L"], LAME["b"] + 2 * JEU, zeta=zeta)
    st = reglage(levee_repos, PLAQUE, LAME["e"], LAME["b"] + 2 * JEU, LAME["b"], p.phi_moyen)
    return lame, st, dict(f_74mm_Hz=f_74, L_libre_mm=L_libre * 1e3, f1_Hz=p.f_hz, m_eff_g=p.m_eff * 1e3,
                          k_eff_N_m=p.k_eff, gamma_m2=p.gamma, phi_moyen=p.phi_moyen, zeta=zeta,
                          levee_repos_mm=levee_repos * 1e3,
                          fleche_2kPa_mm=p.gamma * 2000.0 / p.k_eff * 1e3)


# --- Le réseau (valeurs d'Elmer ou de la note) ------------------------------------------------
def _lignes_elmer(csv_path=None):
    csv_path = csv_path or os.path.join(RESULTATS, "trou_soupape_bb95.csv")
    if not os.path.exists(csv_path):
        return []
    with open(csv_path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def ajuste_L(levees_mm, L):
    """L(h) = L0 + a/h aux moindres carrés (h en mm). Renvoie (L0, a)."""
    A = np.column_stack([np.ones(len(levees_mm)), 1.0 / np.asarray(levees_mm, float)])
    (L0, a), *_ = np.linalg.lstsq(A, np.asarray(L, float), rcond=None)
    return float(L0), float(a)


def reseau_elmer(trou, levee, csv_path=None):
    """L, C, R du CSV d'Elmer pour (trou, levée), et la loi L(h) du trou ; None si absent."""
    lignes = [r for r in _lignes_elmer(csv_path) if r["trou"] == trou]
    ici = [r for r in lignes if abs(float(r["levee_mm"]) - levee) < 1e-6]
    if not ici:
        return None
    r = ici[0]
    L0, a = ajuste_L([float(x["levee_mm"]) for x in lignes], [float(x["L_elmer_kg_m4"]) for x in lignes])
    # R : PAS celui de l'ajustement d'Elmer (3,1e4 à 3,2e4 Pa.s/m³ pour tous les cas = rho.c/S de la
    # boîte absorbante, 13 300 mm² : un artefact de la condition d'onde plane posée à 30 mm). La
    # vraie résistance de rayonnement d'une petite source à 155 Hz est rho.omega²/(4.pi.c), 100 fois
    # moins ; elle comptait pour 20 % de l'amortissement de la lame par le volume balayé.
    return dict(L=float(r["L_elmer_kg_m4"]), C=float(r["V_eff_cm3"]) * 1e-6 / (RHO * C_SON ** 2),
                R=R_RAYONNEMENT, R_elmer=float(r["R_Pa_s_m3"]), source="elmer", f_H=float(r["f_H_elmer_Hz"]),
                L0=L0, a=a * 1e-3)


def reseau_note(trou, levee, V_cm3=40.6):
    a, b = elm.TROUS[trou]
    n = elm.formules_note((a, b), levee, V_cm3=V_cm3)
    C = V_cm3 * 1e-6 / (RHO * C_SON ** 2)
    return dict(L=n["L_kg_m4"], C=C, R=R_RAYONNEMENT, source="note", f_H=n["f_H_Hz"], L0=n["L_kg_m4"], a=0.0)


def air_elmer(trou, levee, levee_anche_mm=LEVEE_REPOS * 1e3, csv_path=None):
    """Masse d'air entraînée et R_a du mode 1 (couplage_lame_air.py), ou None. Si le cas exact
    n'est pas calculé, la levée de soupape la plus proche pour ce trou (la masse d'air locale
    dépend surtout de la lame et de la fente, voir le README)."""
    csv_path = csv_path or os.path.join(RESULTATS, "couplage_lame_air.csv")
    if not os.path.exists(csv_path):
        return None
    with open(csv_path, encoding="utf-8") as fh:
        lignes = [r for r in csv.DictReader(fh, delimiter=";") if r.get("trou") == trou
                  and abs(float(r.get("levee_anche_mm") or "nan") - levee_anche_mm) < 1e-6]
    if not lignes:
        return None
    r = min(lignes, key=lambda r: abs(float(r["levee_soupape_mm"]) - levee))
    return dict(m_a=float(r["m_a_g"]) * 1e-3, R_a=float(r["R_a_kg_s"]), f=float(r["f_couple_Hz"]),
                levee_elmer_mm=float(r["levee_soupape_mm"]))


def masse_reseau(g, reseau, f):
    """La part de la masse d'air que le réseau L, C, R du modèle temporel porte déjà (par le
    volume balayé g.x') : Im(g².Z_res)/omega. On la retire de la masse d'Elmer pour ne pas la
    compter deux fois ; il reste la masse d'air LOCALE (jeux, fente, côté soufflet)."""
    w = 2 * math.pi * f
    Z = 1.0 / (1j * w * reseau["C"] + 1.0 / (reseau["R"] + 1j * w * reseau["L"]))
    return (g * g * Z).imag / w, (g * g * Z).real


class BasseTrouSoupape:
    """Une anche, sa chambre, son trou et le rideau de sa soupape (poussé)."""

    def __init__(self, lame, st, trou, levee_mm, reseau, cd=CD, sans_trou=False, facteur_volume=1.0,
                 m_air=0.0, zeta_air=0.0, balayage=1.0, l_fente=None):
        self.cr = CoupledReedsModel(reeds=[lame, lame], settings=[st, st], voicing=Voicing(),
                                    muted=(False, True))
        self.m, self.k, self.c = self.cr.m[0], self.cr.k[0], self.cr.c_damp[0]
        # l'air (couplage_lame_air.py, Elmer) : masse entraînée et amortissement par rayonnement
        self.m = self.m + m_air
        self.c = self.c + 2 * zeta_air * math.sqrt(self.k * self.m)
        self.g = self.cr.g[0]
        # volume balayé par la lame (g.x') : il remplit la chambre en poussé (comme coupled_reeds,
        # sweep = 1). Il manquait dans le premier calcul (PR #44).
        self.balayage = balayage
        # longueur du passage dans l'écart pour l'inertie du jet (None : débit quasi statique)
        self.l_fente = l_fente
        a, b = elm.TROUS[trou]
        self.A_trou = a * b * 1e-6
        self.perimetre = 2 * (a + b) * 1e-3
        self.levee = levee_mm * 1e-3
        self.A_rideau = self.perimetre * self.levee
        self.L, self.C, self.R = reseau["L"], reseau["C"] * facteur_volume, reseau["R"]
        self.L0, self.a_L = reseau.get("L0", self.L), reseau.get("a", 0.0)
        self.cd = cd
        self.sans_trou = sans_trou
        if sans_trou:
            # chambre largement ouverte : pas de perte, masse d'air d'un trou de 50 x 50 mm, 5 mm
            self.L, self.R = RHO * 0.005 / 2.5e-3, 0.0
            self.L0, self.a_L = self.L, 0.0
        self.perte = self.perte_de(self.levee)

    def perte_de(self, h):
        if self.sans_trou:
            return 0.0
        return RHO / 2 * (1 / (self.cd * self.A_trou) ** 2 + 1 / (self.cd * self.perimetre * h) ** 2)

    def L_de(self, h):
        if h >= self.levee - 1e-12:
            return self.L                      # la valeur d'Elmer à la levée nominale
        return self.L0 + self.a_L / max(h, H_MIN)

    def deriv(self, s, P, perte=None, L=None):
        perte = self.perte if perte is None else perte
        L = self.L if L is None else L
        x, xd, p_c, q_h, q_i = s
        dp = P - p_c
        a_eff, part = self.cr._series(0, x)
        if self.l_fente is None:
            q_r, dq_r = self.cr._reed_flow(0, dp, x)[0], 0.0
        else:
            # inertie de l'air qui passe dans l'écart (St Hilaire 1971 ; Millot & Baumann 2007) :
            # rho.(l + h/2)/A . dq/dt = dp - rho.q|q|/(2 (alpha.A_eff)²), débit à sens unique
            alpha = self.cr.settings[0].alpha
            A = self.cr._area(0, x)
            h = A / self.cr.w_eff[0]
            q_r = max(0.0, q_i)
            dq_r = (dp - RHO * q_r * q_r / (2 * (alpha * a_eff) ** 2)) / (RHO * (self.l_fente + 0.5 * h) / A)
            if q_i <= 0.0 and dq_r < 0.0:
                dq_r = 0.0
        xdd = (dp * part * self.g - self.k * x - self.c * xd) / self.m
        dp_c = (q_r + self.balayage * self.g * xd - q_h) / self.C
        dq_h = (p_c - self.R * q_h - perte * q_h * abs(q_h)) / L
        return (xd, xdd, dp_c, dq_h, dq_r), q_r

    def simuler(self, dur=3.0, P=P_JEU, fs=8000.0, sur=4, scenario="soupape", t_ouv=T_OUV, rampe=0.02, x0=1e-6):
        """scenario « soupape » : P constant, chambre à P, soupape de H_MIN à sa levée en t_ouv.
        scenario « soufflet » : soupape ouverte, P de 0 à P en `rampe`."""
        n = int(dur * fs)
        dt0 = 1.0 / fs
        p0 = P if scenario == "soupape" else 0.0
        s = (x0, 0.0, p0, 0.0, 0.0)
        X = np.zeros(n); PC = np.zeros(n); QR = np.zeros(n); QH = np.zeros(n)
        t = 0.0
        Pt = P
        for j in range(n):
            if scenario == "soupape":
                h = self.levee if (t_ouv <= 0 or t >= t_ouv) else H_MIN + (self.levee - H_MIN) * t / t_ouv
                perte, L = self.perte_de(h), self.L_de(h)
            else:
                perte, L = self.perte, self.L
            # pas adapté à la raideur de la perte d'orifice (rideau presque fermé)
            taux = 2 * math.sqrt(max(P, 1.0) * perte) / L if perte > 0 else 0.0
            nsub = max(sur, int(math.ceil(dt0 * taux)))
            dt = dt0 / nsub
            for _ in range(nsub):
                if scenario != "soupape":
                    Pt = P * min(1.0, t / rampe) if rampe > 0 else P
                k1, _ = self.deriv(s, Pt, perte, L)
                k2, _ = self.deriv(tuple(a + 0.5 * dt * b for a, b in zip(s, k1)), Pt, perte, L)
                k3, _ = self.deriv(tuple(a + 0.5 * dt * b for a, b in zip(s, k2)), Pt, perte, L)
                k4, _ = self.deriv(tuple(a + dt * b for a, b in zip(s, k3)), Pt, perte, L)
                s = tuple(a + dt / 6 * (b + 2 * c_ + 2 * d + e) for a, b, c_, d, e in zip(s, k1, k2, k3, k4))
                t += dt
            if not all(math.isfinite(v) for v in s):
                raise FloatingPointError("divergence : augmenter `sur`")
            _, q_r = self.deriv(s, P, perte, L)
            X[j], PC[j], QR[j], QH[j] = s[0], s[2], q_r, s[3]
        return dict(t=np.arange(n) / fs, x=X, p_ch=PC, q_r=QR, q_h=QH, fs=fs, P=P)


# --- Les mesures sur une simulation ---------------------------------------------------------
def par_periode(y, w, fn):
    nb = y.size // w
    return np.array([fn(y[i * w:(i + 1) * w]) for i in range(nb)])


def transitoire(sim, f1, amp, dp_etabli):
    """Temps (s) où l'enveloppe atteint 10 % et 90 % de l'amplitude établie, et où la différence
    de pression sur l'anche atteint 90 % de sa valeur établie. Fenêtres d'une période ; le temps
    d'une fenêtre est sa fin (on ne peut pas le savoir avant)."""
    fs, P = sim["fs"], sim["P"]
    w = max(1, int(round(fs / f1)))
    env = par_periode(sim["x"], w, lambda y: 0.5 * (y.max() - y.min()))
    dp = P - par_periode(sim["p_ch"], w, np.mean)
    tf = (np.arange(env.size) + 1) * w / fs

    def premier(ok):
        i = np.flatnonzero(ok)
        return float(tf[i[0]]) if i.size else float("nan")

    return dict(t_parle_10_s=premier(env >= 0.1 * amp), t_parle_50_s=premier(env >= 0.5 * amp),
                t_parle_90_s=premier(env >= 0.9 * amp),
                t_dp90_s=premier(dp >= 0.9 * dp_etabli))


def mesures(sim, f1, t_etabli=0.5):
    fs, P = sim["fs"], sim["P"]
    m = sim["t"] >= sim["t"][-1] - t_etabli
    x, pc, qr, qh = sim["x"][m], sim["p_ch"][m], sim["q_r"][m], sim["q_h"][m]
    amp = 0.5 * (x.max() - x.min())
    out = dict(amplitude_bout_mm=amp * 1e3)
    # joue : amplitude d'au moins 50 µm ET qui ne décroît pas sur la dernière demi-seconde (sinon
    # c'est le coup de l'ouverture qui sonne et s'éteint, pas une auto-oscillation)
    w = max(1, int(round(fs / f1)))
    env = par_periode(x, w, lambda y: 0.5 * (y.max() - y.min()))
    tient = env.size >= 10 and env[-5:].mean() >= 0.9 * env[:5].mean()
    if amp < 50e-6 or not tient:
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
    tr = transitoire(sim, f_jeu, amp, P - pc.mean())
    out.update(joue=True, f_jeu_Hz=float(f_jeu), ecart_cents=1200 * math.log2(f_jeu / f1),
               q_moyen_L_s=q_moy * 1e3, q_crete_L_s=q_cr * 1e3, facteur_crete=q_cr / q_moy,
               A_anche_eff_mm2=q_moy / (CD * v_jet) * 1e6, A_crete_mm2=q_cr / (CD * v_jet) * 1e6,
               p_ch_moy_pct=100 * pc.mean() / P, p_ch_crete_pct=100 * pc.max() / P,
               p_ch_cc_pct=100 * (pc.max() - pc.min()) / P,
               niveau_fond_dB=10 * math.log10(e_fond + 1e-30),
               part_sup_500Hz_pct=(100 * S[1:][f[1:] > 500].sum() / e_tot) if e_tot > 0 else float("nan"),
               centroide_Hz=centroide,
               t_parle_10_ms=1e3 * tr["t_parle_10_s"], t_parle_50_ms=1e3 * tr["t_parle_50_s"],
               t_parle_90_ms=1e3 * tr["t_parle_90_s"],
               periodes_10=tr["t_parle_10_s"] * f_jeu, periodes_90=tr["t_parle_90_s"] * f_jeu,
               t_dp90_ms=1e3 * tr["t_dp90_s"])
    return out


def seuil(modele, f1, lo=20.0, hi=P_JEU, n=7, dur=3.0):
    """Pression de démarrage par bissection (scénario soufflet ; demi-marche d'incertitude)."""
    if not mesures(modele.simuler(dur=dur, P=hi, scenario="soufflet"), f1).get("joue"):
        return float("nan"), float("nan")
    for _ in range(n):
        mid = math.sqrt(lo * hi)
        if mesures(modele.simuler(dur=dur, P=mid, scenario="soufflet"), f1).get("joue"):
            hi = mid
        else:
            lo = mid
    return math.sqrt(lo * hi), (hi - lo) / 2


def parametres_lame(lame):
    return dict(gamma=float(lame.gamma[0]), m_eff=float(lame.M[0, 0]), k_eff=float(lame.K[0, 0]))


_CACHE = {}


def la_lame(f_note=F_NOTE, zeta=ZETA, levee_repos=LEVEE_REPOS):
    cle = (f_note, zeta, levee_repos)
    if cle not in _CACHE:
        _CACHE[cle] = lame_nue(f_note, zeta, levee_repos)
    return _CACHE[cle]


def un_cas(trou, levee, P=P_JEU, scenario="soupape", t_ouv=T_OUV, f_note=F_NOTE, avec_seuil=False, source="auto",
           sans_trou=False, zeta=ZETA, levee_repos=LEVEE_REPOS, facteur_volume=1.0, x0=1e-6, dur=4.0,
           avec_air=True, l_fente=None):
    lame, st, info = la_lame(f_note, zeta, levee_repos)
    r = (reseau_elmer(trou, levee) if source in ("auto", "elmer") else None) or reseau_note(trou, levee)
    m_air = zeta_air = 0.0
    air = air_elmer(trou, levee, levee_repos * 1e3) if (avec_air and not sans_trou) else None
    if air:
        g = parametres_lame(lame)["gamma"]
        m_res, R_res = masse_reseau(g, r, air["f"])
        m_air = max(0.0, air["m_a"] - m_res)
        zeta_air = max(0.0, air["R_a"] - R_res) / (2 * math.sqrt(info["k_eff_N_m"] * (info["m_eff_g"] * 1e-3 + m_air)))
    mod = BasseTrouSoupape(lame, st, trou, levee, r, sans_trou=sans_trou, facteur_volume=facteur_volume,
                           m_air=m_air, zeta_air=zeta_air, l_fente=l_fente)
    f_air = info["f1_Hz"] / math.sqrt(1 + m_air / (info["m_eff_g"] * 1e-3))
    sim = mod.simuler(dur=dur, P=P, scenario=scenario, t_ouv=t_ouv, x0=x0)
    res = dict(trou="sans" if sans_trou else trou, levee_soupape_mm=levee, P_Pa=P, scenario=scenario,
               t_ouv_ms=t_ouv * 1e3 if scenario == "soupape" else float("nan"), reseau=r["source"],
               f_H_Hz=r["f_H"], L_kg_m4=r["L"], V_eff_cm3=mod.C * RHO * C_SON ** 2 * 1e6, R=r["R"],
               A_rideau_mm2=mod.A_rideau * 1e6, f1_Hz=info["f1_Hz"], L_libre_mm=info["L_libre_mm"],
               k_eff_N_m=info["k_eff_N_m"], zeta=zeta, levee_anche_mm=info["levee_repos_mm"],
               fleche_2kPa_mm=info["fleche_2kPa_mm"], x0_um=x0 * 1e6, m_air_local_mg=m_air * 1e6,
               zeta_air=zeta_air, f_air_Hz=f_air)
    res.update(mesures(sim, info["f1_Hz"]))
    if res.get("joue"):
        res["ecart_cents_air"] = 1200 * math.log2(res["f_jeu_Hz"] / f_air)   # écart à la lame pincée en place
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


def ligne(r):
    nan = float("nan")
    return (f"{r['trou']:6s} soupape {r['levee_soupape_mm']:g} mm {r['P_Pa']:.0f} Pa {r['scenario']:8s}: "
            f"joue {r.get('joue')} parle {r.get('t_parle_10_ms', nan):.0f} / {r.get('t_parle_50_ms', nan):.0f} / {r.get('t_parle_90_ms', nan):.0f} ms "
            f"({r.get('periodes_90', nan):.0f} pér.) dp90 {r.get('t_dp90_ms', nan):.1f} ms "
            f"f {r.get('f_jeu_Hz', 0):.2f} Hz ({r.get('ecart_cents', 0):+.1f} c) q {r.get('q_moyen_L_s', 0):.3f} L/s "
            f"crête x{r.get('facteur_crete', 0):.2f} p_ch moy {r.get('p_ch_moy_pct', 0):.1f} % crête {r.get('p_ch_crete_pct', 0):.1f} %"
            + (f" p_on {r['p_on_Pa']:.0f} Pa" if 'p_on_Pa' in r else ""))


def sensibilite(nom="trou_soupape_reponse_sensibilite.csv"):
    """Un facteur à la fois autour de 12x12, soupape 3 mm, 2 kPa, ouverture 10 ms."""
    base = dict(trou="12x12", levee=3.0, P=2000.0)
    plan = [("reference", {})]
    plan += [("t_ouv", dict(t_ouv=v)) for v in (0.0, 0.005, 0.02, 0.04)]
    plan += [("levee_anche", dict(levee_repos=v)) for v in (0.5e-3, 0.75e-3, 1.5e-3)]
    plan += [("volume", dict(facteur_volume=v)) for v in (0.5, 2.0)]
    plan += [("zeta", dict(zeta=v)) for v in (0.002, 0.008)]
    plan += [("x0", dict(x0=v)) for v in (1e-7, 1e-5)]
    plan += [("scenario", dict(scenario="soufflet"))]
    plan += [("l_fente", dict(l_fente=1e-3))]
    res = []
    for facteur, kw in plan:
        r = dict(facteur=facteur, **un_cas(**base, **kw))
        res.append(r)
        print(facteur, ligne(r), flush=True)
        ecrire(res, nom)
    return res


# --- Source de débit, sans chambre (Ewen, 05/10/2026) ------------------------------------------
class SourceDebit(BasseTrouSoupape):
    """La lame sur sa fente, SANS chambre en aval (dehors à 0), alimentée par un DÉBIT q0 (source
    de grande impédance : souffler sans étanchéité) dans un petit volume amont V_amont. La pression
    amont n'est plus imposée : elle s'ajuste au débit. État : (x, x', p_amont, -, -).
    Le volume balayé par la lame (g.x') agrandit le volume amont quand elle entre dans la fente."""

    def __init__(self, lame, st, q0, V_amont_cm3=5.0, **kw):
        super().__init__(lame, st, "20x15", 6.0, reseau_note("20x15", 6.0), sans_trou=True, **kw)
        self.q0 = q0
        self.C_amont = V_amont_cm3 * 1e-6 / (RHO * C_SON ** 2)

    def deriv(self, s, P=None, perte=None, L=None):
        x, xd, p_a, _, _ = s
        dp = max(p_a, 0.0)
        q_r, _ = self.cr._reed_flow(0, dp, x)
        part = self.cr._series(0, x)[1]
        xdd = (dp * part * self.g - self.k * x - self.c * xd) / self.m
        dp_a = (self.q0 - q_r - self.balayage * self.g * xd) / self.C_amont
        return (xd, xdd, dp_a, 0.0, 0.0), q_r

    def simuler(self, dur=3.0, P=None, fs=8000.0, sur=8, x0=1e-6, **kw):
        n = int(dur * fs)
        dt = 1.0 / (fs * sur)
        s = (x0, 0.0, 0.0, 0.0, 0.0)
        X = np.zeros(n); PA = np.zeros(n); QR = np.zeros(n)
        for j in range(n):
            for _ in range(sur):
                k1, _ = self.deriv(s)
                k2, _ = self.deriv(tuple(a + 0.5 * dt * b for a, b in zip(s, k1)))
                k3, _ = self.deriv(tuple(a + 0.5 * dt * b for a, b in zip(s, k2)))
                k4, _ = self.deriv(tuple(a + dt * b for a, b in zip(s, k3)))
                s = tuple(a + dt / 6 * (b + 2 * c_ + 2 * d + e) for a, b, c_, d, e in zip(s, k1, k2, k3, k4))
            if not all(math.isfinite(v) for v in s):
                raise FloatingPointError("divergence : augmenter `sur`")
            _, q_r = self.deriv(s)
            X[j], PA[j], QR[j] = s[0], s[2], q_r
        return dict(t=np.arange(n) / fs, x=X, p_amont=PA, q_r=QR, fs=fs)


def cas_debit(q0_L_s, V_amont_cm3=5.0, dur=3.0, x0=1e-6):
    """Mesures du scénario « source de débit sans chambre »."""
    lame, st, info = la_lame()
    mod = SourceDebit(lame, st, q0_L_s * 1e-3, V_amont_cm3)
    sim = mod.simuler(dur=dur, x0=x0)
    fs = sim["fs"]
    m = sim["t"] >= sim["t"][-1] - 0.5
    x = sim["x"][m]
    amp = 0.5 * (x.max() - x.min())
    w = max(1, int(round(fs / info["f1_Hz"])))
    env = par_periode(x, w, lambda y: 0.5 * (y.max() - y.min()))
    joue = bool(amp >= 50e-6 and env[-5:].mean() >= 0.9 * env[:5].mean())
    res = dict(q0_L_s=q0_L_s, V_amont_cm3=V_amont_cm3, joue=joue, amplitude_bout_mm=amp * 1e3,
               p_amont_moy_Pa=float(sim["p_amont"][m].mean()))
    if joue:
        f = dominant_frequency(x - x.mean(), fs)
        envt = par_periode(sim["x"], w, lambda y: 0.5 * (y.max() - y.min()))
        tf = (np.arange(envt.size) + 1) * w / fs
        i90 = np.flatnonzero(envt >= 0.9 * amp)
        res.update(f_jeu_Hz=float(f), ecart_cents=1200 * math.log2(f / info["f1_Hz"]),
                   t_parle_90_ms=1e3 * float(tf[i90[0]]) if i90.size else float("nan"))
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--trou")
    ap.add_argument("--levee", type=float)
    ap.add_argument("--pression", type=float, default=P_JEU)
    ap.add_argument("--scenario", default="soupape", choices=["soupape", "soufflet"])
    ap.add_argument("--seuils", action="store_true")
    ap.add_argument("--sensibilite", action="store_true")
    ap.add_argument("--source", default="auto", choices=["auto", "elmer", "note"])
    ap.add_argument("--sortie", default="trou_soupape_jeu.csv")
    ap.add_argument("--debit", action="store_true", help="source de débit sans chambre")
    a = ap.parse_args()
    if a.debit:
        res = []
        for V in (0.5, 5.0, 50.0):
            for q0 in (0.5, 1.0, 2.0):
                r = cas_debit(q0, V)
                res.append(r)
                print(r, flush=True)
                ecrire(res, "trou_soupape_source_debit.csv")
        return
    if a.sensibilite:
        sensibilite()
        return
    if a.trou:
        r = un_cas(a.trou, a.levee or 3.0, a.pression, a.scenario, avec_seuil=a.seuils, source=a.source)
        for k, v in r.items():
            print(f"{k:22s} {v}")
        return
    res = []
    for P in PRESSIONS:
        for sc in ("soupape", "soufflet"):
            res.append(un_cas("20x15", 6.0, P, sc, sans_trou=True))
            print("sans trou :", ligne(res[-1]), flush=True)
    for trou in elm.TROUS:
        for lev in elm.LEVEES:
            for P in PRESSIONS:
                for sc in ("soupape", "soufflet"):
                    s = a.seuils and sc == "soufflet" and P == PRESSIONS[-1]
                    r = un_cas(trou, lev, P, sc, avec_seuil=s, source=a.source)
                    res.append(r)
                    print(ligne(r), flush=True)
                    ecrire(res, a.sortie)


if __name__ == "__main__":
    main()

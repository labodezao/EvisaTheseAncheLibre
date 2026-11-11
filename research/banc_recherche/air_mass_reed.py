"""Anche libre entretenue par la **masse d'air de la fente** (Adachi et al. 2026).

Nouvel excitateur, **à côté** de `reed_oscillator.FreeReedModel` (qui reste tel
quel, ses tests aussi). Source : S. Adachi, H. Okada, T. Samejima, M. Takeda,
K. Nishimiya, « Aerodynamic mechanism of accordion pitch bending : simulation
and theoretical analysis », Forum Acusticum 2026 (Graz), article 000418,
https://dael.euracoustics.org/confs/fa2026/data/articles/000418.pdf
(lu en entier le 11/11/2026 ; numéros d'équation de l'article ci-dessous).

Ce qui change par rapport à `FreeReedModel`, et pourquoi
---------------------------------------------------------
Dans l'ancien modèle l'anche ne s'entretient que par la compliance de la
chambre (débit quasi stationnaire, ouverture écrêtée, force indépendante de
la position). Une anche réelle s'entretient **sans cavité accordée** (Ricot,
Caussé, Misdariis, JASA 117(4), 2005) : l'air qui passe dans la fente a une
masse, le débit suit l'ouverture **avec retard**, et la pression sur la lame
en tire une composante en phase avec sa vitesse.

Équations (x : déplacement du bout, **positif vers la chambre**, c'est-à-dire
vers l'amont ; x = 0 : lame au ras de la plaque ; l'anche est fermée par le
souffle) :

    (2)  ρ (d/S) dU/dt = p0 − K_p ρ/2 (U/S_c)² − K_r ρ/2 (U/S)²
    (3)  p   = p0 − K_p ρ/2 (U/S_c)²            pression de la chambre
    (4)  S(x) = (L + W) √(max(x, 0)² + a²)        aire de passage
    (5)  p_r = p − ρ (d/S) dU/dt = K_r ρ/2 (U/S)²  pression sur la face amont
    (6)  ẍ = −ω0² (x − x_repos) − 2ζω0 ẋ − (S_r/M) p_r ,  S_r = L·W
    (7)  p_out = ρ ΔL/S_r · dU/dt ,  ΔL = √(S_r/π)     son rayonné
         d = 0,5 √(S/π)  (masse d'air « cylindre » ; 0,5 calé par les auteurs
         sur l'expérience de Ricot)

L'écoulement est **incompressible** dans l'article : la chambre n'y est que la
section `S_c` où se perd `K_p` (le clapet). Seul écart d'écriture : les carrés
`U²` sont codés `U|U|` (identiques tant que U > 0, ce que le modèle donne ;
le signe compte si l'air reflue, ce que l'article n'envisage pas).

Options ajoutées (désactivées par défaut, donc défaut = l'article) :

- `stack` (une `slot_stack.SlotStack`) : géométrie réelle de la fente au lieu
  de `max(x, 0)` — la section qui se ferme dans la plaque **et se rouvre**
  quand le bout ressort de l'autre côté (idée de Millot et Baumann 2007,
  reprise dans `coupled_reeds.ReedSetting` et `slot_stack`), sens inverse,
  anche en sandwich. Hauteur de passage = `SlotStack.passage(y)[0]` avec
  `y = x_repos − x` (l'axe de `slot_stack` suit l'air). La pile doit être
  construite avec la levée `x_repos` (`SlotStack.accordion(plaque, x_repos)`).
- `chamber_volume_m3` : chambre **compressible** (compliance V/(γ P_atm)) entre
  le clapet et l'anche ; le clapet reçoit alors sa propre masse d'air
  `ρ ℓ_p/S_c` (même loi que la fente si `pallet_length_m` n'est pas donné :
  ℓ_p = 0,5 √(S_c/π), HYPOTHÈSE de ma part, non tirée d'une mesure). Quand V
  tend vers 0 on retrouve (2) avec la masse du clapet en plus.

Ce que l'article n'a pas et que ce module n'invente pas : soupape de cuir,
seconde anche, corps, second mode. La voix à deux anches est dans
`coupled_reeds.py` ; le branchement de ce module y est un lot à part.

Intégration : RK4 à pas fixe suréchantillonné (le débit relaxe en quelques
µs quand la fente est fermée : `√(2 K_r p0/ρ)/d`). Le cœur est en Python pur
(`math`) ; si `numba` est installé il est compilé (≈ 100 fois plus rapide),
mêmes résultats. `BANC_SANS_NUMBA=1` force le Python pur.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field, replace

import numpy as np

# ---------------------------------------------------------------------------
# Paramètres
# ---------------------------------------------------------------------------


@dataclass
class AirMassReedParams:
    """Paramètres d'une anche à masse d'air. Défauts : tableau 1 d'Adachi
    et al. 2026 (anche Do4 au banc d'Okada), K_r = 8, K_p = 35 (clapet grand
    ouvert ; 150 pour un clapet ouvert de 1 mm)."""
    f0_hz: float = 267.6                    # fréquence propre de la lame
    mass_kg: float = (2.0 / 3.0) * 0.248e-3  # masse effective (2/3 de 0,248 g)
    zeta: float = 0.003                     # amortissement réduit
    length_m: float = 32.8e-3               # L
    width_m: float = 3.45e-3                # W
    gap_m: float = 0.14e-3                  # a : jeu lame / plaque
    x_rest_m: float = 0.3e-3                # levée au repos (côté chambre)
    chamber_section_m2: float = 14.8e-3 * 14.6e-3   # S_c
    K_r: float = 8.0                        # perte à l'ouverture de l'anche
    K_p: float = 35.0                       # perte au clapet
    rho: float = 1.17
    d_coef: float = 0.5                     # d = d_coef √(S/π)
    perimeter_m: float | None = None        # défaut L + W (éq. 4)
    force_area_m2: float | None = None      # défaut S_r = L·W
    stack: object | None = None             # SlotStack (option)
    chamber_volume_m3: float | None = None  # option chambre compressible
    pallet_length_m: float | None = None    # masse d'air du clapet (option)
    patm: float = 101325.0
    gamma: float = 1.4

    @property
    def stiffness(self):
        return self.mass_kg * (2.0 * math.pi * self.f0_hz) ** 2

    @property
    def perimeter(self):
        return self.length_m + self.width_m if self.perimeter_m is None else self.perimeter_m

    @property
    def force_area(self):
        return self.length_m * self.width_m if self.force_area_m2 is None else self.force_area_m2

    def with_(self, **kw):
        return replace(self, **kw)


def adachi_c4(K_p=35.0, **kw):
    """L'anche Do4 de l'article (tableau 1), clapet `K_p` (35 ou 150)."""
    return AirMassReedParams(K_p=float(K_p), **kw)


def from_modal(mp, length_m, width_m, **kw):
    """Paramètres depuis un premier mode réduit (`languette.ParametresModaux` :
    `f_hz`, `m_eff`, `gamma`, normalisés au déplacement du bout).

    Réduction modale cohérente : masse `m_eff`, force `gamma·p_r` (γ = ∫ b φ,
    φ(bout) = 1). L'article prend M = 2/3 de la masse et la force sur toute
    l'aire L·W ; pour une lame uniforme les deux donnent S_r/M à 4 % près
    (1,50/(ρ e) contre 1,57/(ρ e)). `length_m`, `width_m` : L et W de l'aire
    de passage (4) ; le reste (jeu, levée, ζ, K_p, K_r...) en mots-clés."""
    return AirMassReedParams(f0_hz=float(mp.f_hz), mass_kg=float(mp.m_eff),
                             force_area_m2=float(mp.gamma), length_m=float(length_m),
                             width_m=float(width_m), **kw)


def from_languette(lang, **kw):
    """Paramètres depuis une `languette.Languette` (Euler-Bernoulli exact,
    mode 1) : L = longueur, W = largeur au bout."""
    from .languette import parametres_modaux
    mp = parametres_modaux(lang)
    b_bout = float(lang.profil(np.array([lang.L * (1 - 1e-9)]))[0][0])
    return from_modal(mp, lang.L, b_bout, **kw)


# ---------------------------------------------------------------------------
# Cœur numérique (Python pur, compilé par numba si possible)
# ---------------------------------------------------------------------------
# Tableau de paramètres `P` :
#  0 ω0²   1 2ζω0   2 S_r/M   3 x_repos   4 périmètre   5 a²   6 ρ   7 d_coef
#  8 c_p = K_p ρ/(2 S_c²)   9 c_r = K_r ρ/2   10 pile ? (0/1)   11 D   12 z_repos
#  13 e   14 compressible ? (0/1)   15 γ P_atm / V   16 L_p = ρ ℓ_p / S_c
_NP = 17


def _hauteur(x, P):
    if P[10] > 0.5:
        y = P[3] - x                    # axe de slot_stack : le sens de l'air
        zc = P[12] + y
        zu = zc - 0.5 * P[13]
        zd = zc + 0.5 * P[13]
        if zd <= 0.0:
            return -zd
        if zu >= P[11]:
            return zu - P[11]
        return 0.0
    return x if x > 0.0 else 0.0


def _aire(x, P):
    h = _hauteur(x, P)
    return P[4] * math.sqrt(h * h + P[5])


def _deriv(s, p0, P, out):
    x = s[0]
    v = s[1]
    U = s[2]
    S = _aire(x, P)
    pr = P[9] * U * abs(U) / (S * S)
    out[0] = v
    out[1] = -P[0] * (x - P[3]) - P[1] * v - P[2] * pr
    g = math.sqrt(math.pi * S) / (P[6] * P[7])      # S / (ρ d)
    if P[14] > 0.5:
        p = s[3]
        Up = s[4]
        out[2] = g * (p - pr)
        out[3] = P[15] * (Up - U)
        out[4] = (p0 - p - P[8] * Up * abs(Up)) / P[16]
    else:
        out[2] = g * (p0 - P[8] * U * abs(U) - pr)
    return pr


def _integrer(s, p0s, sub, dt, P, X, Uo, dUo, pch, pro):
    n = p0s.shape[0]
    m = s.shape[0]
    k1 = np.zeros(m)
    k2 = np.zeros(m)
    k3 = np.zeros(m)
    k4 = np.zeros(m)
    tmp = np.zeros(m)
    ok = True
    for i in range(n):
        p0 = p0s[i]
        for _ in range(sub):
            _deriv(s, p0, P, k1)
            for j in range(m):
                tmp[j] = s[j] + 0.5 * dt * k1[j]
            _deriv(tmp, p0, P, k2)
            for j in range(m):
                tmp[j] = s[j] + 0.5 * dt * k2[j]
            _deriv(tmp, p0, P, k3)
            for j in range(m):
                tmp[j] = s[j] + dt * k3[j]
            _deriv(tmp, p0, P, k4)
            for j in range(m):
                s[j] = s[j] + dt / 6.0 * (k1[j] + 2.0 * k2[j] + 2.0 * k3[j] + k4[j])
        for j in range(m):
            if not math.isfinite(s[j]):
                ok = False
        if not ok:
            return i
        pr = _deriv(s, p0, P, k1)
        X[i] = s[0]
        Uo[i] = s[2]
        dUo[i] = k1[2]
        pro[i] = pr
        if P[14] > 0.5:
            pch[i] = s[3]
        else:
            pch[i] = p0 - P[8] * s[2] * abs(s[2])
    return n


NUMBA = False
if not os.environ.get('BANC_SANS_NUMBA'):
    try:                                    # accélération optionnelle
        from numba import njit
        _hauteur = njit(cache=True)(_hauteur)
        _aire = njit(cache=True)(_aire)
        _deriv = njit(cache=True)(_deriv)
        _integrer = njit(cache=True)(_integrer)
        NUMBA = True
    except Exception:                       # pragma: no cover - selon le poste
        NUMBA = False


# ---------------------------------------------------------------------------
# Résultat
# ---------------------------------------------------------------------------

def mean_frequency(x, fs):
    """Fréquence moyenne (Hz) d'un signal périodique : passages par zéro
    montants (interpolés) sur un nombre ENTIER de périodes. C'est la
    « vérité » d'une simulation : la fréquence du déplacement de la lame."""
    x = np.asarray(x, float)
    x = x - 0.5 * (x.max() + x.min())
    i = np.nonzero((x[:-1] < 0.0) & (x[1:] >= 0.0))[0]
    if i.size < 3:
        return float('nan')
    t = i + x[i] / (x[i] - x[i + 1])
    return float((i.size - 1) * fs / (t[-1] - t[0]))


@dataclass
class AirMassResult:
    t: np.ndarray
    tip: np.ndarray            # x (m), positif vers la chambre
    flow: np.ndarray           # U (m³/s)
    dflow: np.ndarray          # dU/dt (m³/s²)
    chamber_pressure: np.ndarray   # p (Pa)
    reed_pressure: np.ndarray      # p_r (Pa)
    fs: float
    params: AirMassReedParams = field(repr=False, default=None)
    final_state: np.ndarray = None

    @property
    def radiated(self):
        """Pression rayonnée (Pa), éq. (7) : `ρ ΔL/S_r · dU/dt`."""
        Sr = self.params.force_area
        return self.params.rho * math.sqrt(Sr / math.pi) / Sr * self.dflow

    def tail(self, frac=0.5):
        return self.t >= self.t[-1] * (1.0 - frac)

    def frequency(self, frac=0.5):
        m = self.tail(frac)
        return mean_frequency(self.tip[m], self.fs)

    def amplitude(self, frac=0.5):
        """Demi-course crête à crête (m) du bout en régime établi."""
        m = self.tail(frac)
        return 0.5 * float(np.ptp(self.tip[m]))

    def peak_to_peak(self, frac=0.5):
        m = self.tail(frac)
        return float(np.ptp(self.tip[m]))

    def oscillates(self, frac=0.25, tol_m=10e-6):
        return self.peak_to_peak(frac) > tol_m


# ---------------------------------------------------------------------------
# Le modèle
# ---------------------------------------------------------------------------

class AirMassReedModel:
    """Anche à un degré de liberté + débit comme variable d'état (Adachi)."""

    def __init__(self, params: AirMassReedParams | None = None):
        self.p = params or AirMassReedParams()
        self.compressible = self.p.chamber_volume_m3 is not None
        self.n_state = 5 if self.compressible else 3
        self._P = self._pack()

    # ---- paramètres ---------------------------------------------------------
    def _pack(self):
        p = self.p
        w0 = 2.0 * math.pi * p.f0_hz
        P = np.zeros(_NP)
        P[0] = w0 * w0
        P[1] = 2.0 * p.zeta * w0
        P[2] = p.force_area / p.mass_kg
        P[3] = p.x_rest_m
        P[4] = p.perimeter
        P[5] = p.gap_m ** 2
        P[6] = p.rho
        P[7] = p.d_coef
        P[8] = p.K_p * p.rho / (2.0 * p.chamber_section_m2 ** 2)
        P[9] = p.K_r * p.rho / 2.0
        if p.stack is not None:
            P[10] = 1.0
            P[11] = p.stack.depth_m
            P[12] = p.stack.rest_center_m
            P[13] = p.stack.tongue_m
        if self.compressible:
            P[14] = 1.0
            P[15] = p.gamma * p.patm / p.chamber_volume_m3
            lp = (p.pallet_length_m if p.pallet_length_m is not None
                  else 0.5 * math.sqrt(p.chamber_section_m2 / math.pi))
            P[16] = p.rho * lp / p.chamber_section_m2
        return P

    def area(self, x):
        return float(_aire(float(x), self._P))

    def deriv(self, state, p0):
        out = np.zeros(self.n_state)
        _deriv(np.asarray(state, float), float(p0), self._P, out)
        return out

    # ---- équilibre et stabilité --------------------------------------------
    def _pr_static(self, x, p0):
        """p_r à l'équilibre pour une position x (débit établi, dU/dt = 0)."""
        S = self.area(x)
        cp, cr = self._P[8], self._P[9]
        return p0 * cr / (cp * S * S + cr) if p0 > 0 else 0.0

    def equilibrium(self, p0, n_iter=200):
        """État stationnaire `[x, 0, U, (p, U)]` pour une pression de soufflet
        p0 (Pa). Force de la lame = p_r·S_r ; dichotomie sur x entre la
        poussée maximale (p_r = p0) et la levée de repos."""
        P = self._P
        lo = P[3] - P[2] * p0 / P[0]
        hi = P[3]

        def g(x):
            return P[0] * (x - P[3]) + P[2] * self._pr_static(x, p0)
        for _ in range(n_iter):
            mid = 0.5 * (lo + hi)
            if g(mid) > 0.0:
                hi = mid
            else:
                lo = mid
        x = 0.5 * (lo + hi)
        S = self.area(x)
        U = math.sqrt(max(p0, 0.0) / (P[8] + P[9] / (S * S)))
        st = np.zeros(self.n_state)
        st[0], st[2] = x, U
        if self.compressible:
            st[3] = p0 - P[8] * U * U
            st[4] = U
        return st

    def jacobian(self, state, p0):
        n = self.n_state
        J = np.zeros((n, n))
        f0 = self.deriv(state, p0)
        scale = np.array([1e-4, 1e-1, 1e-4, 1e2, 1e-4])[:n]
        for k in range(n):
            d = 1e-7 * max(scale[k], abs(state[k]))
            s2 = np.array(state, float)
            s2[k] += d
            s1 = np.array(state, float)
            s1[k] -= d
            J[:, k] = (self.deriv(s2, p0) - self.deriv(s1, p0)) / (2 * d)
        return J

    def growth_rate(self, p0):
        """(taux de croissance max (1/s), fréquence associée (Hz)) du mode le
        moins stable à l'équilibre. Positif : l'anche démarre seule."""
        ev = np.linalg.eigvals(self.jacobian(self.equilibrium(p0), p0))
        osc = ev[np.abs(ev.imag) > 1.0]
        if osc.size == 0:
            return float('-inf'), float('nan')
        i = int(np.argmax(osc.real))
        return float(osc[i].real), float(abs(osc[i].imag) / (2 * math.pi))

    def instability_band(self, p_lo=1.0, p_hi=2e4, n_scan=60, n_iter=40):
        """Bande de pression (Pa) où l'équilibre est instable : `(p_bas,
        p_haut)` (None si absent). Au-delà de p_haut la lame est poussée dans
        la plaque à l'équilibre (S ne dépend plus de x) : l'équilibre redevient
        stable, mais un cycle de grande amplitude peut y survivre (attaque)."""
        ps = np.geomspace(p_lo, p_hi, int(n_scan))
        sg = [self.growth_rate(q)[0] > 0 for q in ps]

        def bis(a, b, want_b):
            for _ in range(n_iter):
                m = math.sqrt(a * b)
                if (self.growth_rate(m)[0] > 0) == want_b:
                    b = m
                else:
                    a = m
            return b
        bas = haut = None
        for i in range(len(ps) - 1):
            if not sg[i] and sg[i + 1] and bas is None:
                bas = bis(ps[i], ps[i + 1], True)
            elif sg[i] and not sg[i + 1] and bas is not None and haut is None:
                haut = bis(ps[i], ps[i + 1], False)
        return bas, haut

    def hopf_threshold(self, **kw):
        """Pression de démarrage (Pa) par stabilité linéaire, ou None."""
        return self.instability_band(**kw)[0]

    # ---- simulation ---------------------------------------------------------
    def rest_state(self):
        """Lame au repos, air immobile : l'instant où le clapet s'ouvre."""
        st = np.zeros(self.n_state)
        st[0] = self.p.x_rest_m
        return st

    def simulate(self, dur, p0=1000.0, fs=44100.0, oversample=8, state0=None,
                 start='repos', kick_m=1e-6):
        """Intègre (RK4) et renvoie un `AirMassResult`.

        `p0` : pression de soufflet (Pa), nombre, tableau d'un élément par
        échantillon de sortie, ou fonction du temps (soufflet qui monte).
        `start` : 'repos' (clapet ouvert d'un coup, lame au repos : l'attaque
        physique) ou 'equilibre' (équilibre statique + `kick_m` sur x : pour
        lire un seuil sans attaque). `state0` reprend un état exact.
        """
        n = int(round(dur * fs))
        t = np.arange(n) / fs
        if callable(p0):
            p0s = np.asarray([float(p0(ti)) for ti in t], float)
        else:
            p0s = np.broadcast_to(np.asarray(p0, float), (n,)).astype(float).copy()
        sub = max(1, int(oversample))
        dt = 1.0 / (fs * sub)
        if state0 is not None:
            s = np.array(state0, float)
        elif start == 'equilibre':
            s = self.equilibrium(float(p0s[0]))
            s[0] += kick_m
        else:
            s = self.rest_state()
        X = np.zeros(n); U = np.zeros(n); dU = np.zeros(n)
        pc = np.zeros(n); pr = np.zeros(n)
        done = _integrer(s, p0s, sub, dt, self._P, X, U, dU, pc, pr)
        if done < n:
            raise FloatingPointError(
                f"divergence numérique à t = {done / fs:.4f} s : augmente `oversample`")
        return AirMassResult(t, X, U, dU, pc, pr, fs, self.p, final_state=s.copy())

    def steady(self, p0, dur=0.6, fs=44100.0, oversample=8, frac=0.4, **kw):
        """Régime établi à pression fixe : dict(f, amplitude, crête-crête, joue)."""
        r = self.simulate(dur, p0, fs=fs, oversample=oversample, **kw)
        return dict(p0=float(p0), f=r.frequency(frac), amp=r.amplitude(frac),
                    ptp=r.peak_to_peak(frac), plays=r.oscillates(frac), result=r)

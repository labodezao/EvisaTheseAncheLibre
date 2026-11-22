"""Anche **fermée par le souffle**, avec un **volume amont fini** et une source
à résistance interne — pour prévoir l'effet du volume derrière l'anche.

Pourquoi ce module
------------------
`coupled_reeds.CoupledReedsModel` a la bonne loi pour une anche d'accordéon
ou de mélodica (`ReedSetting`, `_area`, `_series` : le souffle POUSSE la
languette dans la fente, le passage se ferme, elle ressort de l'autre côté),
mais son soufflet impose la pression `P_s` : il n'y a pas de volume amont ni
de source qui débite moins quand la pression monte. `reed_oscillator.
FreeReedModel`, lui, a un volume (la chambre) mais la loi inverse : le souffle
OUVRE l'anche. Prévoir avec lui l'effet du volume donne le contraire de
l'atelier (voir `docs/audit_anche_fermee_volume_amont.md`).

Ce module ajoute, à la loi de `coupled_reeds` (la même fonction `gap`, la
même section en série avec la fente, la même force `Δp·part·Γ`) :

- un **volume amont** `V_u` (la cloche, le sommier) entre la source et l'anche ;
- une **source** `P0` à **résistance interne** `R_s` : `q = (P0 − p_u)/R_s` ;
- l'aval : un volume `V_d` et un orifice (masse d'air + perte de charge) ;
  en option un second étage (canal `V_n` et clapet) pour se comparer à
  `CoupledReedsModel` ;
- en option un **tuyau en ligne** de N cellules (compliance, inertance,
  résistance de Poiseuille) entre la source et le volume amont, et un
  **ballast** (volume ajouté à la source) ;
- l'**équilibre statique**, le **jacobien numérique**, la **bande
  d'instabilité** (franchissements par stabilité linéaire, pas par
  tâtonnement) et une **simulation** RK4.

Une anche, un mode. La lame se donne par `Blade` : lame uniforme équivalente
(`Blade.uniform`, `Blade.for_note`) ou directement `m`, `k`, `Γ` du mode 1
(lame à profil, mesurée ou issue des éléments finis).

Hypothèses
----------
- Pression uniforme dans chaque volume (constantes localisées).
- Un seul mode de lame ; la section utile ne dépend que de la hauteur au bout
  (côtés comptés par `side_fraction`, comme `ReedSetting`).
- Écoulement quasi stationnaire (Bernoulli) dans la section ; pas d'inertie
  de l'air dans la fente ni de l'écoulement amont local.
- Le volume balayé par la lame (`Γ·ẋ`) est compté dans le bilan (`sweep`,
  1 par défaut comme `CoupledReedsModel`).

Paramètres SUPPOSÉS (aucun n'est mesuré ; aucun n'est réglé pour un résultat)
-------------------------------------------------------------------------
- levée 0,4 mm, épaisseur de plaque 1,0 mm, jeu latéral 30 µm
  (`CENTRAL_LIFT_M`, `CENTRAL_PLATE_M`, `CENTRAL_CLEARANCE_M`) ;
- résistance de source `R_s` = 3·10⁶ Pa·s/m³ (`CENTRAL_SOURCE_RESISTANCE`) ;
- aval : `V_d` = 1 cm³, orifice 25 mm² sur 6 mm ;
- lame : laiton uniforme (E = 100 GPa, ρ = 8500 kg/m³), largeur 3 mm,
  épaisseur équivalente choisie pour que la lame de 24 mm joue le Fa3 ;
- amortissement ζ = 0,004 (défaut du dépôt) ; tuyau : N = 24 cellules,
  vitesse du son 325 m/s.

Limites
-------
- Pression uniforme dans la cloche : aucun mode acoustique de la cloche.
- Un seul mode de lame. Le Fa3 du mélodica n'est pas concluant : avec la
  lame uniforme équivalente il ne parle à aucun volume et se plaque vers
  500 Pa ; la lame réelle, amincie à la racine, reste à modéliser.
- Tuyau en cellules : avec lui le réseau a des modes à basse fréquence
  (23-50 Hz) qui n'ont rien d'une note ; ils sont rapportés tels quels.
- L'amplitude peut dépasser la levée dans certains cas : non validé.
- Par défaut (`gap_inertia=None`) le mécanisme de Ricot, Caussé et Misdariis
  (2005), l'inertie de l'air amont près de la fente, est absent : voir
  « Inertie de la fente » pour l'option `gap_inertia="ricot"`.

Inertie de la fente (option `gap_inertia="ricot"`)
-------------------------------------------------
Ricot, Caussé & Misdariis, JASA 117(4), 2279-2290 (2005), DOI
10.1121/1.1852546. Par défaut le débit dans la fente est quasi stationnaire
(`Q = α·a·√(2Δp/ρ)`) ; avec l'option, il devient une variable d'état `Q_r`
et l'air amont, accéléré près de la fente, impose

    L_r · dQ_r/dt = Δp − (ρ/2)·u·|u| ,   u = Q_r / (α·a) ,   Δp = p_u − p_d

(éq. 5 de l'article, passée de 2D à 3D : `q_2D = Q_r / longueur de fente`).
`L_r = ρ·K0 / w_eff`, où `w_eff` est la longueur de fente efficace de la
section (`a_eff = w_eff·√(h² + jeu²)`, largeur de fente `e = √(h² + jeu²)`).
`a` est la section équivalente de la loi existante (fente en série avec
l'ouverture de la plaque) : la limite `L_r → 0` rend exactement la loi
quasi stationnaire, ce qui est vérifié par les tests.

`K0` : soit un nombre fixe (`k0=4.5`, la valeur du calcul de l'article, sa
section V), soit `k0=None` : formule de l'article `K0(t) = ln(2·x_B/e(t))/π`
(éq. 5), `x_B` = `inertia_reach_m`, distance du point B où la pression est
supposée constante et l'air au repos. **`inertia_reach_m` = 5 mm est SUPPOSÉ**
(l'article dit seulement que le choix de B est arbitraire et que l'influence
de K0 devient faible au-delà d'une certaine valeur). L'éq. 5 est bien
`K0(t)·dq/dt` (pas `d(K0·q)/dt`). Garde numérique : K0 ≥ 1e-3.

La pression qui pousse la lame n'est plus `Δp` mais la pression de face
`Δp_face = Δp − L_r·dQ_r/dt = (ρ/2)·u·|u|` (éq. 18-19), dans la même
expression de force qu'avant (même `part` série, même Γ). Le facteur `(1 − A1)`
et les termes `A2`, `A3` de l'éq. 8 ne sont PAS ajoutés : l'article montre
(fig. 11) que la force d'inertie est négligeable et que A1, proportionnel à
e², ne participe pas à l'excitation (éq. 20). Les bilans de volume amont et
aval utilisent `Q_r`.

Le système est raide (constante de temps de `Q_r` de l'ordre de
`L_r·Q/(2·Δp)`, 1e-9 à 1e-5 s) : avec cette option l'intégration est un
TR-BDF2 (ordre 2, L-stable, Newton à jacobien numérique), pas le RK4.

`added_air_mass(l, h, rho)` : masse d'air ajoutée par face de la lame
(éq. 9, Morse & Ingard). Non appliquée : la masse effective mesurée dans l'air
(fréquence propre) la contient déjà, l'article le dit (éq. 10 et suite).

Validation : avec un volume amont très grand et `R_s` très petit, le seuil
(13,875 contre 13,874 Pa), le plaquage (472,046 Pa), la fréquence (173,18 Hz)
et l'amplitude à 300 Pa (1,693 mm) rejoignent ceux de `CoupledReedsModel`
(`tests/test_upstream_reed.py`).

Numba, s'il est installé, accélère l'intégration ; sinon le même code tourne
en Python pur, plus lentement.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .coupled_reeds import Orifice, ReedSetting
from .reed_oscillator import FreeReedModel, Slot

try:  # numba est un extra facultatif du dépôt
    from numba import njit
except ImportError:  # pragma: no cover
    def njit(*args, **kwargs):
        if args and callable(args[0]):
            return args[0]
        return lambda f: f

# ---- paramètres supposés (centraux) ----------------------------------------
CENTRAL_LIFT_M = 0.4e-3
CENTRAL_PLATE_M = 1.0e-3
CENTRAL_CLEARANCE_M = 30e-6
CENTRAL_SOURCE_RESISTANCE = 3e6          # Pa·s/m³
CENTRAL_DOWN_VOLUME_M3 = 1e-6
CENTRAL_ORIFICE = Orifice(25e-6, 6e-3)
BRASS_E_PA, BRASS_RHO = 100e9, 8500.0
REF_NOTE_HZ, REF_LENGTH_M, REF_WIDTH_M = 174.61, 24e-3, 3e-3   # Fa3, lame de 24 mm
ZETA = 0.004
RHO_AIR = 1.2
GAMMA_PATM = 1.4e5                       # γ·P_atm : raideur de l'air (Pa)
SOUND_SPEED = 325.0
AIR_VISCOSITY = 1.8e-5
N_CELLS = 24


@dataclass
class Blade:
    """Lame réduite à son mode 1 : masse, raideur, projection de la pression.

    `gamma` : force modale par pascal (m²), `phi_tip` : déformée au bout
    (déplacement du bout = `phi_tip`·x). Pour une lame à profil, donner
    directement `m`, `k`, `gamma` (mode 1 normalisé au bout, `phi_tip = 1`).
    `thickness_m` sert de défaut à l'épaisseur de languette du réglage.
    """
    m: float
    k: float
    gamma: float
    phi_tip: float = 1.0
    length_m: float = REF_LENGTH_M
    width_m: float = REF_WIDTH_M
    zeta: float = ZETA
    thickness_m: float | None = None

    @property
    def f0_hz(self):
        return math.sqrt(self.k / self.m) / (2.0 * math.pi)

    @property
    def damping(self):
        return 2.0 * self.zeta * math.sqrt(self.k * self.m)

    @classmethod
    def uniform(cls, length_m, width_m, thickness_m, e_pa=BRASS_E_PA,
                rho=BRASS_RHO, zeta=ZETA):
        """Lame uniforme encastrée-libre (modes de `modal`, via `FreeReedModel`)."""
        sec = np.array([[length_m, rho, width_m, thickness_m, e_pa]])
        r = FreeReedModel(sections=sec, n_modes=1, zeta=zeta, slot=Slot(width_m=width_m))
        return cls(m=float(r.M[0, 0]), k=float(r.K[0, 0]), gamma=float(r.gamma[0]),
                   phi_tip=float(r.phi_tip[0]), length_m=float(r.L), width_m=width_m,
                   zeta=zeta, thickness_m=thickness_m)

    @classmethod
    def for_note(cls, f_hz, e_pa=BRASS_E_PA, rho=BRASS_RHO, width_m=REF_WIDTH_M,
                 ref_f_hz=REF_NOTE_HZ, ref_length_m=REF_LENGTH_M, zeta=ZETA):
        """Lame uniforme équivalente d'une note.

        L'épaisseur est celle qui fait jouer `ref_f_hz` à la lame de
        `ref_length_m` (premier mode encastré-libre : f = 0,1615·t/L²·√(E/ρ)) ;
        elle est gardée pour toutes les notes et la longueur varie en 1/√f.
        """
        t = ref_f_hz * ref_length_m ** 2 / (0.1615 * math.sqrt(e_pa / rho))
        length = ref_length_m * math.sqrt(ref_f_hz / f_hz)
        return cls.uniform(length, width_m, t, e_pa, rho, zeta)


def added_air_mass(l, h, rho=RHO_AIR):
    """Masse d'air ajoutée par une face d'une lame rectangulaire `l` × `h` (m)
    dans un écran (Morse & Ingard ; Ricot et al. 2005, éq. 9) :
    `8/(9π)·ρ·l·h·(l² + l·h + h²)/(l + h)` (kg). Non appliquée par le
    modèle : la fréquence propre mesurée dans l'air la contient déjà ; elle
    sert à la comparer à la masse de la lame. Deux faces : le double."""
    return 8.0 / (9.0 * math.pi) * rho * l * h * (l * l + l * h + h * h) / (l + h)


@dataclass
class Crossing:
    """Un franchissement de la stabilité linéaire.

    `kind` : 'demarrage' (stable -> instable) ou 'fin' (instable -> stable ;
    la lame est alors plaquée). `p0_pa` : pression de source. `f_hz` : fréquence
    de la valeur propre, du côté instable. `y_sur_levee` : position statique
    du bout rapportée à la levée (1 = bout au niveau de la plaque).
    `sous_borne` : instable dès `p_lo`, le seuil est en dessous.
    """
    kind: str
    p0_pa: float
    f_hz: float
    y_sur_levee: float
    sous_borne: bool = False


@dataclass
class Run:
    """Résultat de `simulate`. `status` : 'etabli', 'non etabli', 'plaquee',
    "n'oscille pas", 'divergence' ou 'equilibre introuvable'."""
    status: str
    amplitude_m: float = float('nan')     # demi-crête-à-crête du bout
    f_hz: float = float('nan')            # passages par zéro
    f_fft_hz: float = float('nan')
    y_mean_m: float = float('nan')
    pu_mean_pa: float = float('nan')
    pu_amp_pa: float = float('nan')
    t_end_s: float = float('nan')


# ---- indices du vecteur de paramètres (compatible numba) --------------------
(P_M, P_K, P_C, P_G, P_PHI, P_ALPHA, P_WEFF, P_ASLOT, P_CL, P_LIFT, P_PLATE, P_TONG,
 P_RHO, P_KAIR, P_CU, P_CD, P_LE, P_CDA1, P_RS, P_P0, P_SWEEP, P_CC, P_LC, P_RC,
 P_C0, P_CN, P_L2, P_CDA2, P_K0, P_XB, P_NP) = range(31)
K0_FLOOR = 1e-3                          # garde numérique de K0 géométrique


@njit(cache=True)
def _gap(y, par):
    z_d = y - par[P_LIFT]
    z_u = z_d - par[P_TONG]
    if z_d < 0.0:
        return -z_d
    if z_u > par[P_PLATE]:
        return z_u - par[P_PLATE]
    return 0.0


@njit(cache=True)
def _area_series(x, par):
    """Section équivalente (m²) et part de la chute prise par l'écart : la
    même loi que `CoupledReedsModel._area` et `_series`."""
    h = _gap(par[P_PHI] * x, par)
    su = par[P_WEFF] * math.sqrt(h * h + par[P_CL] ** 2)
    inv = 1.0 / (su * su) + 1.0 / (par[P_ASLOT] ** 2)
    a = 1.0 / math.sqrt(inv)
    return a, (a / su) ** 2


@njit(cache=True)
def _gap_inertance(x, par):
    """`L_r = ρ·K0/w_eff` (kg/m⁴) à la position `x` ; `K0` fixe si
    `par[P_K0] >= 0`, sinon `ln(2·x_B/e)/π` avec `e = √(h² + jeu²)`."""
    k0 = par[P_K0]
    if k0 < 0.0:
        h = _gap(par[P_PHI] * x, par)
        e = math.sqrt(h * h + par[P_CL] ** 2)
        k0 = max(math.log(2.0 * par[P_XB] / e) / math.pi, K0_FLOOR)
    return par[P_RHO] * k0 / par[P_WEFF]


@njit(cache=True)
def _deriv(s, par, fl, out):
    """État : [ẋ, x, p_u, p_d, q_e, (p_n, q_p), (q_1..q_N, p_1..p_N), (Q_r)]."""
    n = fl[1]
    xd = s[0]
    x = s[1]
    pu = s[2]
    pd = s[3]
    qe = s[4]
    rho = par[P_RHO]
    a, part = _area_series(x, par)
    dp = pu - pd
    if fl[3]:
        ns = s.shape[0]
        qr = s[ns - 1]
        u = qr / (par[P_ALPHA] * a)
        dpf = 0.5 * rho * u * abs(u)              # pression de face (éq. 18-19)
        out[ns - 1] = (dp - dpf) / _gap_inertance(x, par)
        out[0] = (dpf * part * par[P_G] - par[P_K] * x - par[P_C] * xd) / par[P_M]
    else:
        qr = par[P_ALPHA] * a * math.sqrt(2.0 * dp / rho) if dp > 0.0 else 0.0
        out[0] = (dp * part * par[P_G] - par[P_K] * x - par[P_C] * xd) / par[P_M]
    out[1] = xd
    sw = par[P_SWEEP] * par[P_G] * xd
    off = 7 if fl[2] else 5
    if fl[0]:
        qin = s[off + n - 1]
    else:
        qin = (par[P_P0] - pu) / par[P_RS]
    out[2] = (qin - qr - sw) / par[P_CU]
    out[3] = (qr + sw - qe) / par[P_CD]
    pn = s[5] if fl[2] else 0.0
    s1 = par[P_CDA1]
    out[4] = (pd - pn - rho * qe * abs(qe) / (2.0 * s1 * s1)) / par[P_LE]
    if fl[2]:
        qp = s[6]
        s2 = par[P_CDA2]
        out[5] = (qe - qp) / par[P_CN]
        out[6] = (pn - rho * qp * abs(qp) / (2.0 * s2 * s2)) / par[P_L2]
    if fl[0]:
        for j in range(n):
            pdn = s[off + n + j + 1] if j < n - 1 else pu
            out[off + j] = (s[off + n + j] - pdn - par[P_RC] * s[off + j]) / par[P_LC]
        out[off + n] = ((par[P_P0] - s[off + n]) / par[P_RS] - s[off]) / par[P_C0]
        for j in range(1, n):
            out[off + n + j] = (s[off + j - 1] - s[off + j]) / par[P_CC]


@njit(cache=True)
def _scales(fl, ns):
    """Échelle de chaque variable d'état (pas des différences finies)."""
    scale = np.zeros(ns)
    scale[0], scale[1] = 0.1, 1e-4
    scale[2:4], scale[4] = 100.0, 1e-5
    off = 5
    if fl[2]:
        scale[5], scale[6] = 100.0, 1e-5
        off = 7
    if fl[0]:
        scale[off:off + fl[1]] = 1e-5
        scale[off + fl[1]:off + 2 * fl[1]] = 100.0
    if fl[3]:
        scale[ns - 1] = 1e-5
    return scale


@njit(cache=True)
def _newton_stage(y, base, c, dt, jac, par, fl, scale, f, mat, res):
    """Résout `y = base + c·dt·f(y)` par Newton (jacobien figé)."""
    ns = y.shape[0]
    for i in range(ns):
        for j in range(ns):
            mat[i, j] = -c * dt * jac[i, j]
        mat[i, i] += 1.0
    for _ in range(10):
        _deriv(y, par, fl, f)
        big = 0.0
        for i in range(ns):
            res[i] = y[i] - base[i] - c * dt * f[i]
        d = np.linalg.solve(mat, res)
        for i in range(ns):
            y[i] -= d[i]
            big = max(big, abs(d[i]) / scale[i])
        if big < 1e-9:
            break


@njit(cache=True)
def _run_implicit(s, par, fl, dt, n, rec):
    """TR-BDF2 (γ = 2 − √2) : ordre 2, L-stable. Jacobien numérique (différences
    avant, pas 1e-6 de l'échelle) recalculé à chaque pas."""
    ns = s.shape[0]
    g = 2.0 - math.sqrt(2.0)
    scale = _scales(fl, ns)
    f0 = np.zeros(ns)
    f = np.zeros(ns)
    ft = np.zeros(ns)
    jac = np.zeros((ns, ns))
    mat = np.zeros((ns, ns))
    res = np.zeros(ns)
    base = np.zeros(ns)
    s1 = np.zeros(ns)
    s2 = np.zeros(ns)
    a1 = 1.0 / (g * (2.0 - g))
    a0 = (1.0 - g) ** 2 / (g * (2.0 - g))
    c2 = (1.0 - g) / (2.0 - g)
    for i in range(n):
        _deriv(s, par, fl, f0)
        for j in range(ns):
            h = 1e-6 * scale[j]
            old = s[j]
            s[j] = old + h
            _deriv(s, par, fl, ft)
            s[j] = old
            for r in range(ns):
                jac[r, j] = (ft[r] - f0[r]) / h
        for j in range(ns):
            base[j] = s[j] + 0.5 * g * dt * f0[j]
            s1[j] = s[j]
        _newton_stage(s1, base, 0.5 * g, dt, jac, par, fl, scale, f, mat, res)
        for j in range(ns):
            base[j] = a1 * s1[j] - a0 * s[j]
            s2[j] = s1[j]
        _newton_stage(s2, base, c2, dt, jac, par, fl, scale, f, mat, res)
        for j in range(ns):
            s[j] = s2[j]
        rec[i, 0] = par[P_PHI] * s[1]
        rec[i, 1] = s[2]
        rec[i, 2] = s[3]
    return s


@njit(cache=True)
def _run(s, par, fl, dt, n, rec):
    if fl[3]:
        return _run_implicit(s, par, fl, dt, n, rec)
    ns = s.shape[0]
    k1 = np.zeros(ns)
    k2 = np.zeros(ns)
    k3 = np.zeros(ns)
    k4 = np.zeros(ns)
    tmp = np.zeros(ns)
    for i in range(n):
        _deriv(s, par, fl, k1)
        for j in range(ns):
            tmp[j] = s[j] + 0.5 * dt * k1[j]
        _deriv(tmp, par, fl, k2)
        for j in range(ns):
            tmp[j] = s[j] + 0.5 * dt * k2[j]
        _deriv(tmp, par, fl, k3)
        for j in range(ns):
            tmp[j] = s[j] + dt * k3[j]
        _deriv(tmp, par, fl, k4)
        for j in range(ns):
            s[j] += dt / 6.0 * (k1[j] + 2 * k2[j] + 2 * k3[j] + k4[j])
        rec[i, 0] = par[P_PHI] * s[1]
        rec[i, 1] = s[2]
        rec[i, 2] = s[3]
    return s


@njit(cache=True)
def _static_at(x, par, fl, p0):
    """(Δp, q, part) pour un x donné, à débit constant dans tout le réseau.

    P0 = Δp + R·q + pertes d'orifice, avec q = α·a·√(2Δp/ρ) : équation du
    second degré en √Δp, résolue en forme fermée."""
    a, part = _area_series(x, par)
    r_tot = par[P_RS] + (fl[1] * par[P_RC] if fl[0] else 0.0)
    rho = par[P_RHO]
    c = par[P_ALPHA] * a * math.sqrt(2.0 / rho)
    kl = rho / (2.0 * par[P_CDA1] ** 2)
    if fl[2]:
        kl += rho / (2.0 * par[P_CDA2] ** 2)
    qa = 1.0 + kl * c * c
    qb = r_tot * c
    u = (-qb + math.sqrt(qb * qb + 4.0 * qa * p0)) / (2.0 * qa)
    return u * u, c * u, part


@njit(cache=True)
def _eq_roots(par, fl, p0, ngrid, ymax):
    roots = np.zeros(12)
    nr = 0
    xs = ymax / par[P_PHI] / ngrid
    dp, q, part = _static_at(0.0, par, fl, p0)
    gprev = dp * part * par[P_G]
    xprev = 0.0
    for i in range(1, ngrid + 1):
        x = i * xs
        dp, q, part = _static_at(x, par, fl, p0)
        g = dp * part * par[P_G] - par[P_K] * x
        if gprev * g <= 0.0 and nr < 12:
            lo = xprev
            hi = x
            glo = gprev
            for _ in range(60):
                mid = 0.5 * (lo + hi)
                dpm, qm, pm = _static_at(mid, par, fl, p0)
                gm = dpm * pm * par[P_G] - par[P_K] * mid
                if glo * gm <= 0.0:
                    hi = mid
                else:
                    lo = mid
                    glo = gm
            roots[nr] = 0.5 * (lo + hi)
            nr += 1
        gprev = g
        xprev = x
    return roots[:nr]


def _zero_cross_freq(t, y):
    y = y - y.mean()
    idx = np.where((y[:-1] < 0) & (y[1:] >= 0))[0]
    if len(idx) < 6:
        return float('nan')
    tc = t[idx] - y[idx] * (t[idx + 1] - t[idx]) / (y[idx + 1] - y[idx])
    return (len(tc) - 1) / (tc[-1] - tc[0])


def _fft_peak(y, dt):
    y = y - y.mean()
    n = len(y)
    nfft = 1 << int(np.ceil(np.log2(n)) + 2)
    spec = np.abs(np.fft.rfft(y * np.hanning(n), nfft))
    i = int(np.argmax(spec[1:]) + 1)
    d = 0.0
    if 1 <= i < len(spec) - 1:
        a, b, c = np.log(spec[i - 1:i + 2] + 1e-300)
        den = a - 2 * b + c
        d = 0.5 * (a - c) / den if den != 0 else 0.0
    return (i + d) / (nfft * dt)


class UpstreamReed:
    """Une anche fermée par le souffle, derrière un volume amont fini.

    ::

        P0 ──R_s── [volume amont V_u] ──anche── [V_d] ──orifice── dehors
        (source)    (cloche, sommier)             (aval)

    avec en option un tuyau de N cellules entre la source et V_u (le ballast
    s'ajoute au volume de la source) et un second étage aval (canal `V_n` puis
    un orifice de clapet) pour se comparer à `CoupledReedsModel`.

    Paramètres : `blade` (`Blade`), `setting` (`ReedSetting`, par défaut les
    cotes SUPPOSÉES centrales, épaisseur de languette = celle de la lame),
    `upstream_volume_m3`, `source_resistance`, `downstream_volume_m3`,
    `orifice`, `pipe` = (longueur, diamètre) en m ou None, `ballast_m3`,
    `stage2` = (V_n, orifice du trou, orifice du clapet) ou None, `sweep`.

    `gap_inertia="ricot"` : inertie de l'air amont près de la fente (voir
    « Inertie de la fente » en tête de module) ; `k0` : nombre fixe (4,5 de
    l'article) ou `None` pour `ln(2·x_B/e)/π` avec `inertia_reach_m` = `x_B`
    (SUPPOSÉ, 5 mm). Sans l'option, `k0` et `inertia_reach_m` ne servent pas.
    """

    def __init__(self, blade: Blade, setting: ReedSetting | None = None,
                 upstream_volume_m3=30e-6, source_resistance=CENTRAL_SOURCE_RESISTANCE,
                 downstream_volume_m3=CENTRAL_DOWN_VOLUME_M3,
                 orifice: Orifice | None = None, pipe=None, ballast_m3=0.0,
                 stage2=None, sweep=1.0, rho=RHO_AIR, gamma_patm=GAMMA_PATM,
                 n_cells=N_CELLS, gap_inertia=None, k0=4.5, inertia_reach_m=5e-3):
        if gap_inertia not in (None, "ricot"):
            raise ValueError("`gap_inertia` : None ou \"ricot\"")
        if setting is None:
            if blade.thickness_m is None:
                raise ValueError("`setting` à donner : l'épaisseur de la languette est inconnue")
            setting = ReedSetting(lift_m=CENTRAL_LIFT_M, tongue_m=blade.thickness_m,
                                  plate_m=CENTRAL_PLATE_M, clearance_m=CENTRAL_CLEARANCE_M)
        self.blade, self.setting = blade, setting
        self.pipe = pipe
        par = np.zeros(P_NP)
        par[P_M], par[P_K], par[P_C] = blade.m, blade.k, blade.damping
        par[P_G], par[P_PHI] = blade.gamma, blade.phi_tip
        par[P_ALPHA] = setting.alpha
        par[P_WEFF] = blade.width_m + 2 * setting.side_fraction * blade.length_m
        par[P_ASLOT] = (blade.width_m + 2 * setting.clearance_m) * (blade.length_m + setting.clearance_m)
        par[P_CL], par[P_LIFT] = setting.clearance_m, setting.lift_m
        par[P_PLATE], par[P_TONG] = setting.plate_m, setting.tongue_m
        par[P_RHO], par[P_KAIR] = rho, gamma_patm
        par[P_CU] = upstream_volume_m3 / gamma_patm
        par[P_CD] = downstream_volume_m3 / gamma_patm
        o1 = (orifice or CENTRAL_ORIFICE) if stage2 is None else stage2[1]
        par[P_LE] = o1.inertance(rho)
        par[P_CDA1] = o1.cd * o1.area_m2
        par[P_RS], par[P_SWEEP] = source_resistance, sweep
        par[P_K0] = -1.0 if k0 is None else float(k0)
        par[P_XB] = inertia_reach_m
        fl = np.zeros(4, dtype=np.int64)
        fl[3] = 1 if gap_inertia == "ricot" else 0
        if pipe is not None:
            length, diam = pipe
            surf = math.pi * (diam / 2) ** 2
            dl = length / n_cells
            par[P_LC] = rho * dl / surf
            par[P_CC] = surf * dl / (rho * SOUND_SPEED ** 2)
            par[P_RC] = 8 * AIR_VISCOSITY * dl / (math.pi * (diam / 2) ** 4)
            fl[0] = 1
        fl[1] = n_cells
        par[P_C0] = par[P_CC] + ballast_m3 / gamma_patm
        if stage2 is not None:
            vn, _, o2 = stage2
            par[P_CN] = vn / gamma_patm
            par[P_L2] = o2.inertance(rho)
            par[P_CDA2] = o2.cd * o2.area_m2
            fl[2] = 1
        self._par, self._fl = par, fl

    # ---- équilibre -----------------------------------------------------------
    @property
    def lift_m(self):
        return self.setting.lift_m

    def _n_state(self):
        fl = self._fl
        return (7 if fl[2] else 5) + (2 * fl[1] if fl[0] else 0) + int(fl[3])

    def gap_inertance(self, x):
        """`L_r` (kg/m⁴) pour un déplacement modal `x` (m)."""
        return float(_gap_inertance(x, self._par))

    def equilibrium(self, p0):
        """État d'équilibre statique à la pression de source `p0` (racine de
        plus petit x) et nombre de racines ; `(None, 0)` s'il n'y en a pas."""
        par, fl = self._par.copy(), self._fl
        par[P_P0] = p0
        ymax = par[P_LIFT] + par[P_TONG] + par[P_PLATE] + 0.5e-3
        roots = _eq_roots(par, fl, p0, 6000, ymax)
        if len(roots) == 0:
            return None, 0
        x = float(roots[0])
        dp, q, _ = _static_at(x, par, fl, p0)
        s = np.zeros(self._n_state())
        s[1], s[4] = x, q
        if fl[3]:
            s[-1] = q                      # à l'équilibre dQ_r/dt = 0 : Δp = (ρ/2)·u²
        rho = par[P_RHO]
        pn = rho * q * q / (2 * par[P_CDA2] ** 2) if fl[2] else 0.0
        pd = pn + rho * q * q / (2 * par[P_CDA1] ** 2)
        pu = pd + dp
        s[3], s[2] = pd, pu
        if fl[2]:
            s[5], s[6] = pn, q
        if fl[0]:
            n = fl[1]
            off = 7 if fl[2] else 5
            s[off:off + n] = q
            for j in range(n):
                s[off + n + j] = pu + (n - j) * par[P_RC] * q
        return s, len(roots)

    def jacobian(self, s, p0):
        """Jacobien numérique (différences centrées, pas relatif à l'échelle
        de chaque grandeur) de l'état `s`."""
        par, fl = self._par.copy(), self._fl
        par[P_P0] = p0
        ns = len(s)
        scale = _scales(fl, ns)
        jac = np.zeros((ns, ns))
        f1, f2 = np.zeros(ns), np.zeros(ns)
        for j in range(ns):
            h = 1e-5 * scale[j]
            sp, sm = s.copy(), s.copy()
            sp[j] += h
            sm[j] -= h
            _deriv(sp, par, fl, f1)
            _deriv(sm, par, fl, f2)
            jac[:, j] = (f1 - f2) / (2 * h)
        return jac

    def growth(self, p0):
        """`(max Re, f_Hz, y_bout_m, n_racines)` de la valeur propre de plus
        grande partie réelle à l'équilibre, ou `None` sans équilibre.
        Positif : l'équilibre est instable (la lame démarre)."""
        s, nr = self.equilibrium(p0)
        if s is None:
            return None
        ev = np.linalg.eigvals(self.jacobian(s, p0))
        i = int(np.argmax(ev.real))
        return (float(ev[i].real), abs(float(ev[i].imag)) / (2 * math.pi),
                float(self._par[P_PHI] * s[1]), nr)

    def instability_band(self, p_lo=20.0, p_hi=4000.0, n_scan=60, n_bisect=40):
        """Franchissements de la stabilité linéaire entre `p_lo` et `p_hi` (Pa).

        Balayage géométrique de `n_scan` pressions, puis dichotomie sur le
        changement de signe de la plus grande partie réelle. Renvoie une
        liste de `Crossing` dans l'ordre des pressions : 'demarrage' puis,
        quand la lame se plaque, 'fin'. Instable dès `p_lo` : un 'demarrage'
        à `p_lo` avec `sous_borne=True`.
        """
        ps = np.geomspace(p_lo, p_hi, n_scan)
        vals = [self.growth(p) for p in ps]

        def sg(v):
            return None if v is None else v[0] > 0

        out = []
        if sg(vals[0]):
            out.append(Crossing('demarrage', float(p_lo), vals[0][1],
                                vals[0][2] / self.lift_m, sous_borne=True))
        for i in range(n_scan - 1):
            a, b = sg(vals[i]), sg(vals[i + 1])
            if a is None or b is None or a == b:
                continue
            lo, hi = ps[i], ps[i + 1]
            for _ in range(n_bisect):
                mid = math.sqrt(lo * hi)
                vm = self.growth(mid)
                if vm is None:
                    break
                if sg(vm) == a:
                    lo = mid
                else:
                    hi = mid
            pc = math.sqrt(lo * hi)
            v = self.growth(pc * (1.0005 if b else 0.9995))   # côté instable
            if v is None:
                continue
            out.append(Crossing('demarrage' if b else 'fin', pc, v[1], v[2] / self.lift_m))
        return out

    # ---- simulation ----------------------------------------------------------
    def trace(self, p0, t_end, dt=2e-6, kick_tip_m=1e-6, s0=None):
        """Intègre de 0 à `t_end` depuis l'équilibre poussé de `kick_tip_m` (ou
        depuis l'état `s0`) ; renvoie `(t, bout_m, p_u, p_d, état_final)`."""
        par, fl = self._par.copy(), self._fl
        par[P_P0] = p0
        if s0 is None:
            s, _ = self.equilibrium(p0)
            if s is None:
                raise ValueError("pas d'équilibre")
            s = s.copy()
            s[1] += kick_tip_m / par[P_PHI]
        else:
            s = np.array(s0, dtype=float)
        n = int(round(t_end / dt))
        rec = np.zeros((n, 3))
        s = _run(s, par, fl, dt, n, rec)
        return dt * np.arange(1, n + 1), rec[:, 0], rec[:, 1], rec[:, 2], s

    def simulate(self, p0, dt=2e-6, chunk=0.25, tmax=4.0, kick_tip_m=1e-6):
        """Intègre (RK4) depuis l'équilibre poussé de `kick_tip_m` au bout.

        Par tranches de `chunk` secondes ; s'arrête quand l'amplitude et la pression
        amont moyenne varient de moins de 2 % d'une tranche à l'autre
        ('etabli'), ou quand le kick s'éteint ('plaquee' si le bout moyen est
        à la levée, sinon "n'oscille pas")."""
        par, fl = self._par.copy(), self._fl
        par[P_P0] = p0
        s, _ = self.equilibrium(p0)
        if s is None:
            return Run('equilibre introuvable')
        s = s.copy()
        s[1] += kick_tip_m / par[P_PHI]
        n = int(round(chunk / dt))
        hist, t0, status = [], 0.0, 'non etabli'
        while t0 < tmax - 1e-12:
            rec = np.zeros((n, 3))
            s = _run(s, par, fl, dt, n, rec)
            if not np.all(np.isfinite(s)):
                return Run('divergence', t_end_s=t0)
            y, pu = rec[:, 0], rec[:, 1]
            t = t0 + dt * np.arange(1, n + 1)
            h = dict(A=0.5 * (y.max() - y.min()), ymean=y.mean(), pu_mean=pu.mean(),
                     pu_amp=0.5 * (pu.max() - pu.min()), f=_zero_cross_freq(t, y),
                     f_fft=_fft_peak(y, dt), t_end=t[-1])
            hist.append(h)
            t0 = t[-1]
            if len(hist) >= 2:
                a0, a1 = hist[-2]['A'], hist[-1]['A']
                if a1 < a0 and a1 < 1.2 * kick_tip_m:
                    status = 'plaquee' if hist[-1]['ymean'] >= 0.999 * par[P_LIFT] else "n'oscille pas"
                    break
                dpu = abs(hist[-1]['pu_mean'] - hist[-2]['pu_mean'])
                if a1 > 1e-5 and abs(a1 - a0) / a1 < 0.02 and dpu / max(abs(hist[-1]['pu_mean']), 1e-9) < 0.02:
                    status = 'etabli'
                    break
        h = hist[-1]
        return Run(status, h['A'], h['f'], h['f_fft'], h['ymean'], h['pu_mean'],
                   h['pu_amp'], h['t_end'])

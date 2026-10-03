"""La languette d'une anche : une seule description, trois calculs.

Une languette est décrite par **tronçons**, de l'encastrement (le pied de la
fente, là où la languette quitte la plaque) jusqu'au bout. Chaque tronçon a
une longueur, une largeur et une épaisseur **au début et à la fin** (elles
varient linéairement entre les deux : anche grattée, languette qui s'affine),
et un matériau. Une masse au bout est un tronçon de plus (épais, en laiton,
etc.), ou une masse ponctuelle.

C'est le format de `reedgui` / `km.py` d'Ewen (2020 : « longueur, densité,
largeur, épaisseur, module d'Young » par tronçon), étendu aux tronçons
variables. `Languette.depuis_matrice` lit son `matrix.txt` tel quel.

Trois calculs sur la MÊME description (c'est la vérification croisée) :

1. `euler_bernoulli` — poutre d'Euler-Bernoulli **exacte** par matrices de
   transfert (tronçons constants exacts ; un tronçon variable est découpé en
   marches fines). Pour une poutre uniforme, redonne `material.resonance_frequency`.
2. `rayleigh_ritz` — la méthode de `km.py` (Ewen, 2020) : projection sur les
   modes de la poutre encastrée uniforme, matrices M et K intégrées tronçon par
   tronçon, étendue à N modes (3 à 5 et plus). Coefficients sigma calculés
   exactement (km.py les arrondissait à 4 chiffres, ce qui abîme les modes 4-5).
3. Elmer (éléments finis 3D) : `research/fem/anche/languette_modes.py`, qui lit
   la même description.

Le pont vers le modèle semi-analytique (`coupled_reeds`) : `LanguetteModale`
porte la masse, la raideur et la forme modales du premier mode (normalisées au
bout : un déplacement modal de 1 = 1 m au bout), et `reglage()` le réglage
d'écoulement (levée, plaque, jeu). Que ces grandeurs viennent de Rayleigh-Ritz
ou d'Elmer, le modèle d'auto-oscillation ne voit pas la différence.

Hypothèses : flexion pure (Euler-Bernoulli : pas de cisaillement ni d'inertie
de rotation, valable tant que l'épaisseur est petite devant la longueur d'onde
de flexion) ; la largeur compte dans la masse et la raideur, mais pour une
largeur constante elle s'annule dans la fréquence (c'est ce qu'Ewen avait
remarqué) ; elle ne s'annule plus quand la languette s'affine, ni pour la
torsion, ni pour l'écoulement dans la fente. La torsion et la flexion dans le
plan ne sont vues que par Elmer.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

# Matériaux : (module d'Young en Pa, masse volumique en kg/m3, coefficient de Poisson).
# Valeurs de manuel (ordre de grandeur, ±3 % sur E selon la nuance et le traitement) :
# acier à ressort au carbone (C75, 1095) 200 à 210 GPa ; inox 190 à 200 ; laiton 97 à 110.
MATERIAUX = {
    "acier": dict(E=2.10e11, rho=7800.0, nu=0.29),
    "inox": dict(E=1.93e11, rho=7900.0, nu=0.29),
    "laiton": dict(E=1.00e11, rho=8500.0, nu=0.34),
    "bronze": dict(E=1.10e11, rho=8800.0, nu=0.34),
    "plomb": dict(E=1.60e10, rho=11340.0, nu=0.44),
    "cire": dict(E=1.0e8, rho=950.0, nu=0.45),
}


def materiau(nom, E=None, rho=None, nu=None):
    """Propriétés d'un matériau (dict E, rho, nu), surchargées si données.

    `nom` : un nom de la liste (acier, laiton...), ou une saisie libre
    « 200 GPa / 7850 » (module d'Young en GPa, masse volumique en kg/m3)."""
    cle = str(nom).strip().lower()
    if cle in MATERIAUX:
        base = dict(MATERIAUX[cle])
    else:
        import re
        m = re.fullmatch(r"\s*([\d.,]+)\s*gpa\s*/\s*([\d.,]+)\s*(?:kg/m3)?\s*", cle)
        if not m:
            raise ValueError(f"matériau inconnu : {nom!r} (connus : {', '.join(MATERIAUX)}, "
                             "ou « 200 GPa / 7850 »)")
        base = dict(E=float(m.group(1).replace(",", ".")) * 1e9,
                    rho=float(m.group(2).replace(",", ".")), nu=0.3)
    if E is not None:
        base["E"] = float(E)
    if rho is not None:
        base["rho"] = float(rho)
    if nu is not None:
        base["nu"] = float(nu)
    return base


@dataclass
class Troncon:
    """Un tronçon de languette. Unités SI (m). Largeur et épaisseur au début et
    à la fin du tronçon (côté encastrement, côté bout), linéaires entre les deux."""
    longueur: float
    largeur: tuple
    epaisseur: tuple
    materiau: str = "acier"
    E: float | None = None
    rho: float | None = None
    nu: float | None = None

    def __post_init__(self):
        b = self.largeur if isinstance(self.largeur, (tuple, list)) else (self.largeur, self.largeur)
        t = self.epaisseur if isinstance(self.epaisseur, (tuple, list)) else (self.epaisseur, self.epaisseur)
        self.largeur = (float(b[0]), float(b[1]))
        self.epaisseur = (float(t[0]), float(t[1]))
        self.longueur = float(self.longueur)
        m = materiau(self.materiau, self.E, self.rho, self.nu)
        self.E, self.rho, self.nu = m["E"], m["rho"], m["nu"]

    @property
    def constant(self):
        return self.largeur[0] == self.largeur[1] and self.epaisseur[0] == self.epaisseur[1]


@dataclass
class Languette:
    """Une languette : tronçons de l'encastrement au bout, masses ponctuelles
    éventuelles `[(x_m, masse_kg), ...]` (x depuis l'encastrement)."""
    troncons: list
    masses: list = field(default_factory=list)
    nom: str = "languette"

    # ---- construction -------------------------------------------------------
    @classmethod
    def uniforme(cls, longueur, largeur, epaisseur, mat="acier", **kw):
        return cls([Troncon(longueur, largeur, epaisseur, mat)], **kw)

    @classmethod
    def depuis_matrice(cls, matrice, nom="reedgui"):
        """Le format de reedgui / km.py : lignes `[longueur, densité, largeur,
        épaisseur, E]` en SI (tronçons constants). `matrice` : tableau ou chemin
        d'un `matrix.txt` (séparateur virgule)."""
        if isinstance(matrice, (str, bytes)) or hasattr(matrice, "__fspath__"):
            matrice = np.loadtxt(matrice, delimiter=",", ndmin=2)
        sec = np.atleast_2d(np.asarray(matrice, float))
        tr = [Troncon(r[0], r[2], r[3], "acier", E=r[4], rho=r[1]) for r in sec]
        return cls(tr, nom=nom)

    def matrice(self, n_sous=1):
        """Vers le format reedgui / `modal.py` : `[longueur, densité, largeur,
        épaisseur, E]` ; un tronçon variable est découpé en `n_sous` marches
        (valeurs au milieu de chaque marche)."""
        lignes = []
        for tr in self.troncons:
            n = 1 if tr.constant else max(1, int(n_sous))
            for k in range(n):
                u = (k + 0.5) / n
                b = tr.largeur[0] + u * (tr.largeur[1] - tr.largeur[0])
                t = tr.epaisseur[0] + u * (tr.epaisseur[1] - tr.epaisseur[0])
                lignes.append([tr.longueur / n, tr.rho, b, t, tr.E])
        return np.array(lignes)

    def adoucie(self, delta=0.2e-3):
        """La même languette, chaque marche (largeur ou épaisseur qui saute d'un
        tronçon au suivant) remplacée par une rampe de longueur `delta` prise à
        moitié sur chaque voisin. Une vraie languette n'a pas de marche franche ;
        le maillage structuré d'Elmer en a besoin."""
        tr = [Troncon(t.longueur, t.largeur, t.epaisseur, t.materiau, t.E, t.rho, t.nu) for t in self.troncons]
        out = []
        for i, t in enumerate(tr):
            out.append(t)
            if i + 1 < len(tr):
                n = tr[i + 1]
                if (t.largeur[1], t.epaisseur[1]) != (n.largeur[0], n.epaisseur[0]):
                    h = 0.5 * delta
                    if t.longueur <= 2 * h or n.longueur <= 2 * h:
                        raise ValueError("tronçon trop court pour adoucir la marche")
                    bm = 0.5 * (t.largeur[1] + n.largeur[0]); em = 0.5 * (t.epaisseur[1] + n.epaisseur[0])
                    u = 1 - h / t.longueur
                    b_av = t.largeur[0] + u * (t.largeur[1] - t.largeur[0])
                    e_av = t.epaisseur[0] + u * (t.epaisseur[1] - t.epaisseur[0])
                    t.longueur -= h
                    t.largeur, t.epaisseur = (t.largeur[0], b_av), (t.epaisseur[0], e_av)
                    out.append(Troncon(h, (b_av, bm), (e_av, em), t.materiau, t.E, t.rho, t.nu))
                    u = h / n.longueur
                    b_ap = n.largeur[0] + u * (n.largeur[1] - n.largeur[0])
                    e_ap = n.epaisseur[0] + u * (n.epaisseur[1] - n.epaisseur[0])
                    out.append(Troncon(h, (bm, b_ap), (em, e_ap), n.materiau, n.E, n.rho, n.nu))
                    n.longueur -= h
                    n.largeur, n.epaisseur = (b_ap, n.largeur[1]), (e_ap, n.epaisseur[1])
        return Languette(out, list(self.masses), self.nom)

    # ---- géométrie ----------------------------------------------------------
    @property
    def L(self):
        return float(sum(t.longueur for t in self.troncons))

    @property
    def bords(self):
        return np.concatenate([[0.0], np.cumsum([t.longueur for t in self.troncons])])

    def profil(self, x):
        """Largeur b(x), épaisseur t(x), masse linéique mu(x), rigidité EI(x)."""
        x = np.atleast_1d(np.asarray(x, float))
        e = self.bords
        idx = np.clip(np.searchsorted(e, x, side="right") - 1, 0, len(self.troncons) - 1)
        b = np.empty_like(x); t = np.empty_like(x); mu = np.empty_like(x); EI = np.empty_like(x)
        for i, tr in enumerate(self.troncons):
            m = idx == i
            if not m.any():
                continue
            u = (x[m] - e[i]) / tr.longueur
            b[m] = tr.largeur[0] + u * (tr.largeur[1] - tr.largeur[0])
            t[m] = tr.epaisseur[0] + u * (tr.epaisseur[1] - tr.epaisseur[0])
            mu[m] = tr.rho * b[m] * t[m]
            EI[m] = tr.E * b[m] * t[m] ** 3 / 12.0
        return b, t, mu, EI

    def masse(self):
        """Masse totale de la partie libre (kg), masses ponctuelles comprises."""
        x, w = self._quadrature()
        return float(np.sum(w * self.profil(x)[2]) + sum(m for _, m in self.masses))

    def _quadrature(self, n_gauss=24, n_sous=8, n_sous_constant=1):
        """Points et poids de Gauss-Legendre, par tronçon (exact aux marches)."""
        g, gw = np.polynomial.legendre.leggauss(n_gauss)
        xs, ws = [], []
        e = self.bords
        for i, tr in enumerate(self.troncons):
            n = n_sous_constant if tr.constant else n_sous
            sub = np.linspace(e[i], e[i + 1], n + 1)
            for a, c in zip(sub[:-1], sub[1:]):
                xs.append(0.5 * (c - a) * g + 0.5 * (a + c))
                ws.append(0.5 * (c - a) * gw)
        return np.concatenate(xs), np.concatenate(ws)


# =============================================================================
# 1. Euler-Bernoulli exact (matrices de transfert)
# =============================================================================

def _marches(lang: Languette, n_sous=40):
    """Tronçons constants (longueur, mu, EI) ; les variables en marches fines."""
    out = []
    e = lang.bords
    for i, tr in enumerate(lang.troncons):
        n = 1 if tr.constant else n_sous
        for k in range(n):
            xm = e[i] + (k + 0.5) / n * tr.longueur
            _, _, mu, EI = lang.profil([xm])
            out.append((tr.longueur / n, float(mu[0]), float(EI[0]), e[i] + k / n * tr.longueur))
    # une marche coupée en deux à chaque masse ponctuelle qui tombe dedans
    for xm, _ in lang.masses:
        coupe = []
        for (l, mu, EI, x0) in out:
            if x0 + 1e-12 < xm < x0 + l - 1e-12:
                coupe += [(xm - x0, mu, EI, x0), (x0 + l - xm, mu, EI, xm)]
            else:
                coupe.append((l, mu, EI, x0))
        out = coupe
    return out


def _transfert(lang, w, marches):
    """Matrice de transfert 4x4 de l'encastrement au bout, état
    [w, w', EI w'', EI w'''], à la pulsation w (rad/s)."""
    T = np.eye(4)
    masses = sorted(lang.masses)
    im = 0
    for (l, mu, EI, x0) in marches:
        while im < len(masses) and masses[im][0] <= x0 + 1e-12:
            P = np.eye(4); P[3, 0] = masses[im][1] * w * w
            T = P @ T; im += 1
        beta = (mu * w * w / EI) ** 0.25
        def B(x):
            ch, sh, c, s = math.cosh(beta * x), math.sinh(beta * x), math.cos(beta * x), math.sin(beta * x)
            b2, b3 = beta ** 2, beta ** 3
            return np.array([[ch, sh, c, s],
                             [beta * sh, beta * ch, -beta * s, beta * c],
                             [EI * b2 * ch, EI * b2 * sh, -EI * b2 * c, -EI * b2 * s],
                             [EI * b3 * sh, EI * b3 * ch, EI * b3 * s, -EI * b3 * c]])
        T = B(l) @ np.linalg.inv(B(0.0)) @ T
    while im < len(masses):
        P = np.eye(4); P[3, 0] = masses[im][1] * w * w
        T = P @ T; im += 1
    return T


def euler_bernoulli(lang: Languette, n_modes=5, f_max=None, n_sous=40, n_balayage=2500):
    """Fréquences propres de flexion (Hz), encastré au pied, libre au bout.

    Racines de det(T[2:4, 2:4]) = 0 (moment et effort tranchant nuls au bout,
    pour un état [0, 0, M0, V0] au pied), cherchées par balayage puis dichotomie.
    Rayleigh-Ritz (bornes supérieures) fixe la plage du balayage.
    """
    f_rr = rayleigh_ritz(lang, n_modes=n_modes, n_base=n_modes + 3)[0]
    f_max = f_max or 1.5 * float(f_rr[-1])
    marches = _marches(lang, n_sous)

    def det(f):
        T = _transfert(lang, 2 * math.pi * f, marches)
        d = T[2, 2] * T[3, 3] - T[2, 3] * T[3, 2]
        # mise à l'échelle (les termes croissent en cosh) : on garde le signe
        n = abs(T[2, 2] * T[3, 3]) + abs(T[2, 3] * T[3, 2]) + 1e-300
        return d / n

    fs = np.geomspace(0.05 * float(f_rr[0]), f_max, n_balayage)
    vals = np.array([det(f) for f in fs])
    racines = []
    for i in range(len(fs) - 1):
        if np.sign(vals[i]) != np.sign(vals[i + 1]):
            a, b = fs[i], fs[i + 1]
            fa = vals[i]
            for _ in range(60):
                c = 0.5 * (a + b)
                fc = det(c)
                if np.sign(fc) == np.sign(fa):
                    a, fa = c, fc
                else:
                    b = c
            racines.append(0.5 * (a + b))
        if len(racines) >= n_modes:
            break
    return np.array(racines)


def forme_euler_bernoulli(lang: Languette, f_hz, x, n_sous=40):
    """Déformée exacte (Euler-Bernoulli) à la fréquence propre `f_hz`, aux
    abscisses `x`, normalisée à 1 au bout."""
    w = 2 * math.pi * f_hz
    marches = _marches(lang, n_sous)
    T = _transfert(lang, w, marches)
    A = T[2:4, 2:4]
    # vecteur [M0, V0] du noyau de A (le plus petit vecteur singulier)
    _, _, vt = np.linalg.svd(A)
    z = np.array([0.0, 0.0, vt[-1, 0], vt[-1, 1]])
    x = np.atleast_1d(np.asarray(x, float))
    out = np.full(x.shape, np.nan)
    masses = sorted(lang.masses)
    im = 0
    for (l, mu, EI, x0) in marches:
        while im < len(masses) and masses[im][0] <= x0 + 1e-12:
            z = z.copy(); z[3] += masses[im][1] * w * w * z[0]; im += 1
        beta = (mu * w * w / EI) ** 0.25
        B0inv = np.linalg.inv(np.array([[1, 0, 1, 0], [0, beta, 0, beta],
                                        [EI * beta ** 2, 0, -EI * beta ** 2, 0],
                                        [0, EI * beta ** 3, 0, -EI * beta ** 3]], float))
        a = B0inv @ z
        m = (x >= x0 - 1e-15) & (x <= x0 + l + 1e-15)
        if m.any():
            s = beta * (x[m] - x0)
            out[m] = a[0] * np.cosh(s) + a[1] * np.sinh(s) + a[2] * np.cos(s) + a[3] * np.sin(s)
        s = beta * l
        z = np.array([a[0] * math.cosh(s) + a[1] * math.sinh(s) + a[2] * math.cos(s) + a[3] * math.sin(s),
                      beta * (a[0] * math.sinh(s) + a[1] * math.cosh(s) - a[2] * math.sin(s) + a[3] * math.cos(s)),
                      EI * beta ** 2 * (a[0] * math.cosh(s) + a[1] * math.sinh(s) - a[2] * math.cos(s) - a[3] * math.sin(s)),
                      EI * beta ** 3 * (a[0] * math.sinh(s) + a[1] * math.cosh(s) + a[2] * math.sin(s) - a[3] * math.cos(s))])
    return out / z[0]


def fleche_statique(lang: Languette, x, force=1.0):
    """Flèche (m) sous une force `force` (N) au bout : la « Déformée » de
    reedgui / fleche.py (2021), par double intégration de M(x)/EI(x).
    `raideur_bout = force / flèche(L)` se mesure avec un poids et une photo."""
    xs = np.linspace(0.0, lang.L, 4001)
    _, _, _, EI = lang.profil(xs)
    courbure = force * (lang.L - xs) / EI
    pente = np.concatenate([[0.0], np.cumsum(0.5 * (courbure[1:] + courbure[:-1]) * np.diff(xs))])
    fl = np.concatenate([[0.0], np.cumsum(0.5 * (pente[1:] + pente[:-1]) * np.diff(xs))])
    return np.interp(np.asarray(x, float), xs, fl)


# =============================================================================
# 2. Rayleigh-Ritz (km.py étendu)
# =============================================================================

def beta_l(n):
    """Racine n de cos(x)·cosh(x) = -1 (poutre encastrée-libre)."""
    x = (2 * n - 1) * math.pi / 2
    for _ in range(60):
        f = math.cos(x) * math.cosh(x) + 1
        d = -math.sin(x) * math.cosh(x) + math.cos(x) * math.sinh(x)
        x -= f / d
    return x


def sigma(n):
    """sigma_n = (cosh bL + cos bL) / (sinh bL + sin bL), exact."""
    b = beta_l(n)
    return (math.cosh(b) + math.cos(b)) / (math.sinh(b) + math.sin(b))


def base_poutre(n, L, x, derivee=0):
    """Forme du mode n de la poutre encastrée-libre uniforme (et ses dérivées),
    normalisée à 2 au bout comme dans km.py."""
    b = beta_l(n)
    k = b / L
    s = sigma(n)
    kx = k * np.asarray(x, float)
    # Forme stable : cosh - s.sinh = (e^kx (1-s) + e^-kx (1+s)) / 2, et
    # e^kx (1-s) = (sin b - cos b - e^-b) . e^kx / (sinh b + sin b), calculé
    # sans soustraire deux grands nombres (sinon les modes au-delà de 8 à 10
    # perdent tous leurs chiffres).
    E = np.exp(kx - b) * 2.0 / (1.0 - math.exp(-2 * b) + 2 * math.sin(b) * math.exp(-b))
    hyp = 0.5 * ((math.sin(b) - math.cos(b) - math.exp(-b)) * E + np.exp(-kx) * (1 + s))
    if derivee == 0:
        return hyp - np.cos(kx) + s * np.sin(kx)
    if derivee == 2:
        return k ** 2 * (hyp + np.cos(kx) - s * np.sin(kx))
    raise ValueError("derivee 0 ou 2")


@dataclass
class ModesRR:
    f_hz: np.ndarray            # fréquences propres (Hz)
    M: np.ndarray               # matrices réduites
    K: np.ndarray
    vecteurs: np.ndarray        # colonnes : coefficients des modes sur la base
    L: float
    n_base: int

    def forme(self, mode, x):
        """Déformée du mode `mode` (1, 2, ...) en x, normalisée à 1 au bout."""
        c = self.vecteurs[:, mode - 1]
        phi = sum(c[i] * base_poutre(i + 1, self.L, x) for i in range(self.n_base))
        tip = sum(c[i] * base_poutre(i + 1, self.L, self.L) for i in range(self.n_base))
        return phi / tip


def rayleigh_ritz(lang: Languette, n_modes=5, n_base=None):
    """Fréquences (Hz) et modes par Rayleigh-Ritz sur `n_base` modes de poutre
    uniforme (défaut : `n_modes`, comme km.py). Renvoie `(f_hz, ModesRR)`.
    Les fréquences sont des bornes supérieures ; plus de base = plus juste."""
    n_base = int(n_base or n_modes)
    if n_base > 40:
        raise ValueError("au-delà de 40 modes de base, la matrice de masse perd sa précision")
    L = lang.L
    # assez de points pour les modes de base les plus ondulés (n_base/2 arches par tronçon)
    x, wq = lang._quadrature(n_sous=max(8, n_base), n_sous_constant=max(1, n_base // 2))
    _, _, mu, EI = lang.profil(x)
    P = np.array([base_poutre(i + 1, L, x) for i in range(n_base)])
    P2 = np.array([base_poutre(i + 1, L, x, 2) for i in range(n_base)])
    M = (P * (wq * mu)) @ P.T
    K = (P2 * (wq * EI)) @ P2.T
    for xm, m in lang.masses:
        p = np.array([base_poutre(i + 1, L, xm) for i in range(n_base)])
        M += m * np.outer(p, p)
    try:
        from scipy.linalg import eigh
        w2, V = eigh(K, M)
    except ImportError:                                    # numpy seul
        Lc = np.linalg.cholesky(M)
        Li = np.linalg.inv(Lc)
        w2, U = np.linalg.eigh(Li @ K @ Li.T)
        V = Li.T @ U
    o = np.argsort(w2)
    w2, V = w2[o], V[:, o]
    f = np.sqrt(np.clip(w2, 0, None)) / (2 * math.pi)
    modes = ModesRR(f, M, K, V, L, n_base)
    return f[:n_modes], modes


# =============================================================================
# Le pont vers le modèle semi-analytique
# =============================================================================

@dataclass
class ParametresModaux:
    """Premier mode réduit à un oscillateur, déplacement modal = déplacement du bout.

    m_eff (kg), k_eff (N/m), gamma (m2) : force modale = gamma x différence de
    pression ; phi_moyen : moyenne de la déformée sur la longueur (la « part des
    côtés » de `ReedSetting.side_fraction`)."""
    f_hz: float
    m_eff: float
    k_eff: float
    gamma: float
    phi_moyen: float
    source: str = "rayleigh-ritz"


def parametres_modaux(lang: Languette, f_hz=None, forme=None, source=None):
    """Masse, raideur et projection modales du mode 1.

    `forme(x)` : déformée normalisée au bout ; `f_hz` : la fréquence à garder.
    Défaut : Euler-Bernoulli exact (fréquence et déformée). Avec la forme et la
    fréquence d'Elmer, ce sont les paramètres « éléments finis ».
    """
    if f_hz is None:
        f_hz = float(euler_bernoulli(lang, n_modes=1)[0])
        source = source or "euler-bernoulli"
    if forme is None:
        f_eb = f_hz
        forme = lambda x: forme_euler_bernoulli(lang, f_eb, x)
    x, wq = lang._quadrature()
    b, _, mu, _ = lang.profil(x)
    phi = np.asarray(forme(x), float)
    m_eff = float(np.sum(wq * mu * phi ** 2) + sum(m * float(forme(np.array([xm]))[0]) ** 2
                                                   for xm, m in lang.masses))
    gamma = float(np.sum(wq * b * phi))
    phi_moy = float(np.sum(wq * phi) / lang.L)
    k_eff = m_eff * (2 * math.pi * f_hz) ** 2
    return ParametresModaux(float(f_hz), m_eff, k_eff, gamma, phi_moy, source or "éléments finis")


class LanguetteModale:
    """Une languette à un mode, au format attendu par `CoupledReedsModel`
    (attributs M, K, zeta, gamma, phi_tip, slot, L) : on y branche des
    paramètres modaux venus de Rayleigh-Ritz ou d'Elmer."""

    def __init__(self, p: ParametresModaux, L, largeur_fente, zeta=0.004):
        from .reed_oscillator import Slot
        self.M = np.array([[p.m_eff]])
        self.K = np.array([[p.k_eff]])
        self.zeta = float(zeta)
        self.gamma = np.array([p.gamma])
        self.phi_tip = np.array([1.0])
        self.L = float(L)
        self.slot = Slot(width_m=float(largeur_fente))
        self.parametres = p


def reglage(levee, plaque, epaisseur_bout, largeur_fente, largeur_bout, phi_moyen=0.39):
    """Le réglage d'écoulement de `coupled_reeds` (anche fermée par le souffle) :
    levée du bout au repos, épaisseur de plaque, épaisseur du bout, jeu latéral
    = (largeur de fente - largeur du bout) / 2 (au moins 10 µm). Unités : m."""
    from .coupled_reeds import ReedSetting
    jeu = max(10e-6, 0.5 * (largeur_fente - largeur_bout))
    return ReedSetting(lift_m=levee, plate_m=plaque, tongue_m=epaisseur_bout,
                       clearance_m=jeu, side_fraction=phi_moyen)

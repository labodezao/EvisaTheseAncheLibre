"""Analyse modale d'une anche **multi-tronçon** (Euler-Bernoulli encastré-libre).

Port de `matkm`/`km` (MATLAB/sympy du dossier Drive « anches models ») : l'anche
est découpée en tronçons de géométrie propre (longueur, densité, largeur,
épaisseur, module d'Young). On projette sur les déformées modales du cantilever
uniforme φ_i, on assemble les matrices de masse `M` et de raideur `K` par
intégration des φ_i (masse) et φ_i″ (raideur, ∝ E·b·h³/12) sur chaque tronçon,
puis on résout le problème aux valeurs propres généralisé `K x = ω² M x`.

Prédit les **fréquences propres** — à comparer à la FRF mesurée (`frf.py`) et à
`material.youngs_modulus`. Colonnes d'un tronçon : `[longueur, densité, largeur,
épaisseur, E]`.
"""
from __future__ import annotations

import numpy as np

# Compat numpy 1.x/2.x (`trapz` renommé `trapezoid`).
_trapz = getattr(np, "trapezoid", getattr(np, "trapz", None))

# Racines caractéristiques encastré-libre (β_n·L) et σ_n associés.
BETA_L = (1.87510407, 4.69409113, 7.85475744, 10.99554073, 14.13716839)
SIGMA = (0.7341, 1.0185, 0.9992, 1.0, 1.0)


def bl_sigma(n: int):
    """(β_n·L, σ_n) du mode `n` (1-indexé) ; au-delà de 5, asymptotique."""
    if 1 <= n <= 5:
        return BETA_L[n - 1], SIGMA[n - 1]
    return (2 * n - 1) * np.pi / 2, 1.0


def _phi(k, sigma, x):
    """Déformée modale φ(x) du cantilever (k = β/L)."""
    return (np.cosh(k * x) - np.cos(k * x)
            - sigma * (np.sinh(k * x) - np.sin(k * x)))


def _phi2(k, sigma, x):
    """Dérivée seconde φ″(x) (analytique)."""
    return k ** 2 * (np.cosh(k * x) + np.cos(k * x)
                     - sigma * (np.sinh(k * x) + np.sin(k * x)))


def _solve_bande(A: np.ndarray, rhs: np.ndarray, bw: int = 3) -> np.ndarray:
    """Résout A y = rhs, A de largeur de bande `bw` (poutre d'Hermite : 3). Rapide et sans
    BLAS (le dense mal conditionné est ~100 fois plus lent). Repli : `np.linalg.solve`."""
    try:
        from scipy.linalg import solve_banded
    except ImportError:
        return np.linalg.solve(A, rhs)
    n = A.shape[0]
    ab = np.zeros((2 * bw + 1, n))
    for d in range(-bw, bw + 1):
        diag = np.diagonal(A, offset=d)
        if d >= 0:
            ab[bw - d, d:] = diag
        else:
            ab[bw - d, :n + d] = diag
    return solve_banded((bw, bw), ab, rhs)


def _modes_fem(sec: np.ndarray, n_modes: int, n_el: int):
    """Modes propres de la lame à tronçons : éléments finis de poutre d'Euler-Bernoulli
    (éléments de Hermite, maillage aligné sur les sauts de section), encastrée en x = 0.

    Rend `(xi, V, M, K, gam, tip)` : abscisses réduites des nœuds, déformées modales
    (nœuds x [flèche/L, pente], une par colonne), masse et raideur modales PHYSIQUES
    (diagonales), `gam_j = ∫ b ψ_j dx`, `tip_j = ψ_j(L)`. Chaque mode est normalisé par
    ψ_j(L) = φ_j(L), la valeur du mode du cantilever uniforme de même rang (ce que les
    appelants utilisent déjà), et orienté positif au bout.
    """
    L = float(sec[:, 0].sum())
    lens = np.round(sec[:, 0] / L, 12)   # rapports de longueurs : insensibles au bruit du dernier chiffre
    # éléments par tronçon : au moins 6 ; au moins 30 par mode demandé en tout
    n_tot = max(int(n_el), 30 * n_modes)
    ne = np.maximum(6, np.ceil(np.round(n_tot * lens, 6)).astype(int))   # arrondi : maillage invariant par homothétie
    rho, b, h, E = sec[:, 1], sec[:, 2], sec[:, 3], sec[:, 4]
    EI, rA = E * b * h ** 3 / 12.0, rho * b * h
    EI0, rA0 = EI.max(), rA.max()
    # éléments : (longueur réduite, EI réduit, rhoA réduit, largeur)
    elems = []
    for s in range(sec.shape[0]):
        elems += [(lens[s] / ne[s], EI[s] / EI0, rA[s] / rA0, b[s])] * int(ne[s])
    n = len(elems)
    N = 2 * (n + 1)
    Kg = np.zeros((N, N))
    Mg = np.zeros((N, N))
    for e, (he, ei, ra, _) in enumerate(elems):
        ke = ei / he ** 3 * np.array([[12, 6 * he, -12, 6 * he],
                                      [6 * he, 4 * he ** 2, -6 * he, 2 * he ** 2],
                                      [-12, -6 * he, 12, -6 * he],
                                      [6 * he, 2 * he ** 2, -6 * he, 4 * he ** 2]])
        me = ra * he / 420.0 * np.array([[156, 22 * he, 54, -13 * he],
                                         [22 * he, 4 * he ** 2, 13 * he, -3 * he ** 2],
                                         [54, 13 * he, 156, -22 * he],
                                         [-13 * he, -3 * he ** 2, -22 * he, 4 * he ** 2]])
        d = slice(2 * e, 2 * e + 4)
        Kg[d, d] += ke
        Mg[d, d] += me
    Kc, Mc = Kg[2:, 2:], Mg[2:, 2:]          # encastrement : flèche et pente nulles en x = 0
    try:
        from scipy.linalg import eigh
        _, U = eigh(Kc, Mc, subset_by_index=[0, n_modes - 1])
    except ImportError:                      # repli numpy (Cholesky de M)
        Li = np.linalg.inv(np.linalg.cholesky(Mc))
        _, Y = np.linalg.eigh(Li @ Kc @ Li.T)
        U = (Li.T @ Y)[:, :n_modes]
    # Affinage : le problème est mal conditionné (rapport des raideurs et des tailles de
    # mailles ~ 1e11) : le solveur généralisé perd jusqu'à 1e-4 sur la plus basse fréquence
    # (mesuré : 15,5913 à 15,5960 Hz selon le bruit du dernier chiffre des longueurs). Itérations
    # de Rayleigh (quotient quadratique en l'erreur du vecteur) ; l'énergie de flexion est
    # calculée en sommes de carrés par élément (pas vᵀKv, qui perd 1e-7 par annulation).
    he_a = np.array([e[0] for e in elems])
    ei_a = np.array([e[1] for e in elems])

    def k_energy(Vf):
        w, th = Vf[0::2], Vf[1::2]
        a = (w[1:] - w[:-1]) / he_a[:, None]
        da, db = th[:-1] - a, th[1:] - a
        return (ei_a / he_a)[:, None] * 4.0 * (da ** 2 + da * db + db ** 2)

    U = np.array(U, dtype=float)
    for j in range(n_modes):
        v = U[:, j]
        for _ in range(3):
            vf = np.concatenate([[0.0, 0.0], v])[:, None]
            rq = k_energy(vf).sum() / (v @ Mc @ v)
            try:
                y = _solve_bande(Kc - rq * Mc, Mc @ v)
            except np.linalg.LinAlgError:
                break
            if not np.all(np.isfinite(y)):
                break
            v = y / np.abs(y).max()
        U[:, j] = v
    V = np.zeros((N, n_modes))
    V[2:, :] = U
    xi = np.concatenate([[0.0], np.cumsum([e[0] for e in elems])])
    # normalisation : ψ_j(L) = L·V[flèche du bout] = φ_j(L)
    T = np.array([_phi(bl_sigma(j + 1)[0] / L, bl_sigma(j + 1)[1], L) for j in range(n_modes)])
    V = V * (T / (L * V[-2, :]))[None, :]
    Mm = rA0 * L ** 3 * (V[2:].T @ Mc @ V[2:])
    Km = np.diag(EI0 / L * k_energy(V).sum(axis=0))
    # hors-diagonale : nul au bruit près (modes propres) ; on le met à zéro
    Mm, Km = np.diag(np.diag(Mm)), np.diag(np.diag(Km))
    gam = np.zeros(n_modes)
    for e, (he, _, _, be) in enumerate(elems):
        wa, ta, wb, tb = V[2 * e], V[2 * e + 1], V[2 * e + 2], V[2 * e + 3]
        gam += be * L ** 2 * (he * (wa + wb) / 2.0 + he ** 2 * (ta - tb) / 12.0)
    return xi, V, Mm, Km, gam, V[-2, :] * L


_cache: dict = {}


def _modes(sections, n_modes: int, n_quad: int):
    sec = np.atleast_2d(np.asarray(sections, dtype="float64"))
    key = (sec.tobytes(), sec.shape, int(n_modes), int(n_quad))
    if key not in _cache:
        if len(_cache) > 64:
            _cache.clear()
        _cache[key] = _modes_fem(sec, int(n_modes), max(int(n_quad) // 4, 1))
    return _cache[key]


def assemble(sections, n_modes: int = 2, n_quad: int = 400):
    """Assemble (M, K) sur `n_modes` déformées modales de la lame à tronçons.

    `sections` : lignes `[longueur, densité, largeur, épaisseur, E]`.

    Les coordonnées sont celles des VRAIES déformées propres ψ_j de la lame en tronçons
    (éléments finis d'Euler-Bernoulli, `_modes_fem`), normalisées par ψ_j(L) = φ_j(L) :
    même normalisation au bout que les modes du cantilever uniforme, auxquels elles se
    réduisent sur une lame uniforme. M et K sont donc diagonales. Avant le 22/11/2026, la
    base était celle de l'uniforme (Rayleigh-Ritz), qui converge mal quand la raideur
    saute : +153 % sur le mode 1 d'une lame à deux épaisseurs avec 1 mode, +3 à +11 % avec 6.
    `gamma`, `phi_tip` et la forme dans cette base : `mode_gamma_tip`, `mode_shapes`.
    `n_quad` règle la finesse du maillage (n_quad/4 éléments au total).
    """
    _, _, M, K, _, _ = _modes(sections, n_modes, n_quad)
    return M.copy(), K.copy()


def mode_gamma_tip(sections, n_modes: int = 2, n_quad: int = 400):
    """(gamma, phi_tip) dans la base de `assemble` : γ_j = ∫ b ψ_j dx (projection d'une
    pression uniforme), φ_tip_j = ψ_j(L)."""
    _, _, _, _, gam, tip = _modes(sections, n_modes, n_quad)
    return gam.copy(), tip.copy()


def mode_shapes(sections, x, n_modes: int = 2, n_quad: int = 400):
    """Déformées ψ_j(x), `(n_modes, len(x))`, par interpolation de Hermite (x en mètres)."""
    xi, V, _, _, _, _ = _modes(sections, n_modes, n_quad)
    sec = np.atleast_2d(np.asarray(sections, dtype="float64"))
    L = float(sec[:, 0].sum())
    x = np.atleast_1d(np.asarray(x, dtype="float64"))
    t = np.clip(x / L, 0.0, 1.0)
    e = np.clip(np.searchsorted(xi, t, side="right") - 1, 0, len(xi) - 2)
    he = xi[e + 1] - xi[e]
    s = (t - xi[e]) / he
    h00 = 2 * s ** 3 - 3 * s ** 2 + 1
    h10 = (s ** 3 - 2 * s ** 2 + s) * he
    h01 = -2 * s ** 3 + 3 * s ** 2
    h11 = (s ** 3 - s ** 2) * he
    return L * (V[2 * e].T * h00 + V[2 * e + 1].T * h10 + V[2 * e + 2].T * h01 + V[2 * e + 3].T * h11)


def natural_frequencies(sections, n_modes: int = 2):
    """Fréquences propres (Hz) de l'anche multi-tronçon."""
    from scipy.linalg import eigh
    M, K = assemble(sections, n_modes)
    w2 = eigh(K, M, eigvals_only=True)
    w2 = np.clip(w2, 0, None)
    return np.sqrt(w2) / (2.0 * np.pi)


def natural_frequencies_np(sections, n_modes: int = 2):
    """Idem sans scipy : résout `M⁻¹K` (M définie positive)."""
    M, K = assemble(sections, n_modes)
    w2 = np.linalg.eigvals(np.linalg.solve(M, K))
    w2 = np.sort(np.real(w2))
    w2 = np.clip(w2, 0, None)
    return np.sqrt(w2) / (2.0 * np.pi)

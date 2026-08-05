"""Modèle non linéaire **anche + cavité + socle** (port compact du MATLAB
`RK4ode45cavity_reed_socket` du dossier Drive « anches models »).

L'anche (N modes, matrices `M`,`K` de `modal`) est chargée par la surpression
de cavité `ΔP`. La cavité échange de l'air : débit d'entrée imposé, **débit de
sortie de Bernoulli** modulé par l'ouverture (position du bout de l'anche), et
balayage volumique par le mouvement de l'anche. La pression suit une loi
**adiabatique**. Le couplage pression→anche→ouverture→débit→pression produit
l'**auto-oscillation** (bifurcation de Hopf) et les portraits de phase
(Position, Vitesse, Accélération).

Intégration **RK4**. Sorties : position/vitesse/accélération du bout, pression,
volume — à passer à `phase_space`, `bifurcation`, `stochastic`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import modal

# Défauts issus du MATLAB (SI).
SECTIONS_DEFAULT = np.array([
    [29.22e-3, 7800, 4.8e-3, 0.40e-3, 2.1e11],
    [15.12e-3, 7800, 4.8e-3, 0.045e-3, 2.1e11],
    [10.35e-3, 7800, 4.8e-3, 0.70e-3, 2.1e11],
])


@dataclass
class Cavity:
    length: float = 35e-3
    width: float = 15e-3
    height: float = 15e-3
    gap: float = 9e-3          # distance lame/cavité (ouverture au repos)
    patm: float = 1e5
    gamma: float = 1.4
    rho: float = 1.2
    cd: float = 0.65           # coefficient de décharge


@dataclass
class Result:
    t: np.ndarray
    position: np.ndarray       # bout de l'anche
    velocity: np.ndarray
    acceleration: np.ndarray
    pressure: np.ndarray
    volume: np.ndarray


class ReedModel:
    def __init__(self, sections=None, cavity: Cavity | None = None,
                 n_modes: int = 2, zeta: float = 0.01, n_quad: int = 400):
        self.sec = np.asarray(SECTIONS_DEFAULT if sections is None else sections, float)
        self.cav = cavity or Cavity()
        self.N = n_modes
        self.M, self.K = modal.assemble(self.sec, n_modes, n_quad)
        self.Minv = np.linalg.inv(self.M)
        self.L = float(self.sec[:, 0].sum())
        self.b = float(np.mean(self.sec[:, 2]))
        # Projection pression→mode et tip : γ_i = ∫ φ_i·b dx ; φ_tip_i = φ_i(L).
        edges = np.concatenate([[0.0], np.cumsum(self.sec[:, 0])])
        gamma = np.zeros(n_modes)
        for s in range(self.sec.shape[0]):
            x = np.linspace(edges[s], edges[s + 1], n_quad)
            for i in range(n_modes):
                k, sg = modal.bl_sigma(i + 1)[0] / self.L, modal.bl_sigma(i + 1)[1]
                gamma[i] += self.sec[s, 2] * modal._trapz(modal._phi(k, sg, x), x)
        self.gamma = gamma
        self.phi_tip = np.array([modal._phi(modal.bl_sigma(i + 1)[0] / self.L,
                                            modal.bl_sigma(i + 1)[1], self.L)
                                 for i in range(n_modes)])
        # Amortissement modal proportionnel.
        w = np.sqrt(np.clip(np.linalg.eigvals(self.Minv @ self.K).real, 0, None))
        self.C = self.M @ np.diag(2 * zeta * w)
        self.V0 = self.cav.length * self.cav.width * self.cav.height

    def _deriv(self, state, q_in, volume):
        N = self.N
        dq, q = state[:N], state[N:2 * N]
        V = state[2 * N]
        c = self.cav
        P = c.patm * (self.V0 / max(V, 1e-9)) ** c.gamma
        dP = P - c.patm
        y = float(self.phi_tip @ q)          # position du bout
        area = self.b * max(c.gap + y, 1e-6)  # ouverture (Bernoulli)
        q_out = np.sign(dP) * c.cd * area * np.sqrt(2 * abs(dP) / c.rho)
        q_reed = float(self.gamma @ dq)      # balayage volumique de l'anche
        dV = q_in - q_out + q_reed
        F = dP * self.gamma                  # force modale
        ddq = self.Minv @ (F - self.K @ q - self.C @ dq)
        d = np.empty_like(state)
        d[:N] = ddq
        d[N:2 * N] = dq
        d[2 * N] = dV
        return d, ddq

    def simulate(self, dur: float, fs: float, q_in: float = 3e-5,
                 q0=None) -> Result:
        """Intègre le modèle (RK4). `q_in` : débit d'entrée (m³/s)."""
        n = int(dur * fs)
        dt = 1.0 / fs
        N = self.N
        s = np.zeros(2 * N + 1)
        s[2 * N] = self.V0
        if q0 is not None:
            s[N:2 * N] = q0
        pos = np.zeros(n); vel = np.zeros(n); acc = np.zeros(n)
        pres = np.zeros(n); vol = np.zeros(n)
        for i in range(n):
            d1, ddq = self._deriv(s, q_in, s[2 * N])
            d2, _ = self._deriv(s + 0.5 * dt * d1, q_in, s[2 * N])
            d3, _ = self._deriv(s + 0.5 * dt * d2, q_in, s[2 * N])
            d4, _ = self._deriv(s + dt * d3, q_in, s[2 * N])
            s = s + (dt / 6.0) * (d1 + 2 * d2 + 2 * d3 + d4)
            pos[i] = self.phi_tip @ s[N:2 * N]
            vel[i] = self.phi_tip @ s[:N]
            acc[i] = self.phi_tip @ ddq
            P = self.cav.patm * (self.V0 / max(s[2 * N], 1e-9)) ** self.cav.gamma
            pres[i] = P; vol[i] = s[2 * N]
        t = np.arange(n) / fs
        return Result(t, pos, vel, acc, pres, vol)

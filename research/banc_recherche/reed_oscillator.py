"""Anche libre auto-oscillante, **alimentée en débit** — modèle jouable.

Reformulation de `reed_model.py` après l'audit (`docs/audit_modele_anche.md`),
conçue pour **auto-osciller** et rester dans des plages physiques, afin de
servir de moteur de synthèse et de support au recalage de modèle.

Ce qui change par rapport à `reed_model.py`, et pourquoi :

1. **La pression est la variable d'état**, pas le volume. Une cavité rigide a
   un volume fixe ; c'est la masse d'air qui varie. L'ancienne loi
   `P = patm·(V₀/V)^γ` avec `V` croissant à l'entrée d'air faisait *chuter*
   la pression : on injectait de l'air et la cavité se mettait en dépression.

2. **L'ouverture est asymétrique.** Une anche libre ne débite que dans un
   sens — l'autre demi-course est fermée par la soupape de cuir, ce pourquoi
   pousser et tirer emploient deux anches distinctes. Une ouverture
   symétrique `S = b·|y|` module la fente deux fois par période et sort une
   note à l'octave supérieure.

3. **L'aire est bornée des deux côtés** : fermeture nette (avec une fuite
   résiduelle, que toute plaque réelle possède) et saturation une fois la
   languette sortie de la fente. C'est la fermeture qui **sature le cycle
   limite** et crée la richesse harmonique ; sans elle rien ne borne
   l'amplitude.

4. **Amortissement modal correct** : `C = M Φ diag(2ζω) Φᵀ M`, symétrique par
   construction (cf. la correction apportée à `reed_model.py`).

5. **Intégration suréchantillonnée.** Le couplage anche/cavité est raide
   (`γP/V₀ ≈ 10¹⁰ Pa/m³`) ; à 44,1 kHz un RK4 explicite diverge.

Le seuil d'oscillation est **prédit** par analyse de stabilité linéaire
(`hopf_threshold`) et non cherché par tâtonnement : on linéarise autour de
l'équilibre statique et on repère où une paire de valeurs propres traverse
l'axe imaginaire. C'est la bifurcation de Hopf que mesurent `seuil.py` et
`bifurcation.py` au banc — le modèle et la mesure parlent enfin de la même
grandeur.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import modal
from .reed_model import SECTIONS_DEFAULT


@dataclass
class Chamber:
    """Chambre d'anche alimentée en débit."""
    volume_m3: float = 7.9e-6      # volume de la chambre (≈ 35×15×15 mm)
    patm: float = 1e5
    gamma: float = 1.4             # exposant adiabatique de l'air
    rho: float = 1.2
    cd: float = 0.65               # coefficient de décharge de la fente


@dataclass
class Slot:
    """Fente et languette : la géométrie qui module le débit."""
    width_m: float = 4.8e-3        # largeur de la fente
    rest_offset_m: float = 0.10e-3 # décalage de la languette au repos
    max_open_m: float = 0.50e-3    # ouverture au-delà de laquelle l'aire sature
    leak_m: float = 2.0e-6         # fuite résiduelle fente fermée (plaque réelle)


@dataclass
class OscillationResult:
    t: np.ndarray
    tip: np.ndarray                # déplacement du bout (m)
    pressure: np.ndarray           # surpression de chambre (Pa)
    opening: np.ndarray            # hauteur d'ouverture (m)
    flow_out: np.ndarray           # débit sortant (m³/s)


class FreeReedModel:
    """Anche libre multi-tronçon couplée à une chambre alimentée en débit."""

    def __init__(self, sections=None, chamber: Chamber | None = None,
                 slot: Slot | None = None, n_modes: int = 2, zeta: float = 0.004):
        self.sec = np.asarray(SECTIONS_DEFAULT if sections is None else sections, float)
        self.ch = chamber or Chamber()
        self.slot = slot or Slot()
        self.N = int(n_modes)
        self.zeta = float(zeta)

        self.M, self.K = modal.assemble(self.sec, self.N)
        self.Minv = np.linalg.inv(self.M)
        self.L = float(self.sec[:, 0].sum())

        # Projection pression -> force modale, et déformée au bout.
        edges = np.concatenate([[0.0], np.cumsum(self.sec[:, 0])])
        gamma = np.zeros(self.N)
        for s in range(self.sec.shape[0]):
            x = np.linspace(edges[s], edges[s + 1], 400)
            for i in range(self.N):
                k, sg = modal.bl_sigma(i + 1)[0] / self.L, modal.bl_sigma(i + 1)[1]
                gamma[i] += self.sec[s, 2] * modal._trapz(modal._phi(k, sg, x), x)
        self.gamma = gamma
        self.phi_tip = np.array([
            modal._phi(modal.bl_sigma(i + 1)[0] / self.L,
                       modal.bl_sigma(i + 1)[1], self.L) for i in range(self.N)])

        w2, Phi = self._eig()
        self.omega = np.sqrt(np.clip(w2, 0.0, None))
        self.C = self.M @ Phi @ np.diag(2 * self.zeta * self.omega) @ Phi.T @ self.M

    # ---- base propre --------------------------------------------------------
    def _eig(self):
        try:
            from scipy.linalg import eigh
            w2, Phi = eigh(self.K, self.M)
        except Exception:
            vals, vecs = np.linalg.eigh(self.M)
            half = vecs @ np.diag(1.0 / np.sqrt(np.clip(vals, 1e-300, None))) @ vecs.T
            w2, U = np.linalg.eigh(half @ self.K @ half)
            Phi = half @ U
        o = np.argsort(w2)
        return w2[o], Phi[:, o]

    @property
    def f_modes(self):
        """Fréquences propres de l'anche (Hz)."""
        return self.omega / (2 * np.pi)

    # ---- géométrie de l'ouverture ------------------------------------------
    def opening(self, tip):
        """Hauteur d'ouverture effective (m) pour un déplacement du bout.

        **Asymétrique** : seul le déplacement qui sort la languette de la
        fente ouvre le passage. Bornée en bas par la fuite résiduelle, en
        haut par la saturation de fente.
        """
        s = self.slot
        return np.clip(tip + s.rest_offset_m, s.leak_m, s.max_open_m)

    def _flow_out(self, p, h):
        """Débit à travers la fente (Bernoulli). La soupape bloque le retour :
        pas de débit inverse — c'est l'asymétrie de l'anche libre."""
        if p <= 0.0:
            return 0.0
        return self.ch.cd * self.slot.width_m * h * np.sqrt(2.0 * p / self.ch.rho)

    # ---- dynamique ----------------------------------------------------------
    def deriv(self, state, q_in):
        """Dérivée de l'état `[q̇ (N), q (N), p]`. `p` = surpression (Pa)."""
        N = self.N
        dq, q, p = state[:N], state[N:2 * N], state[2 * N]

        tip = float(self.phi_tip @ q)
        h = float(self.opening(tip))
        q_out = self._flow_out(p, h)
        q_reed = float(self.gamma @ dq)      # volume balayé par la languette

        # Anche : la surpression de chambre pousse la languette hors de la fente.
        ddq = self.Minv @ (p * self.gamma - self.K @ q - self.C @ dq)

        # Chambre rigide, isentropique : la pression suit le bilan de débit.
        # Le balayage de l'anche agrandit la chambre -> il la dépressurise.
        stiff = self.ch.gamma * (self.ch.patm + p) / self.ch.volume_m3
        dp = stiff * (q_in - q_out - q_reed)

        out = np.empty_like(state)
        out[:N] = ddq
        out[N:2 * N] = dq
        out[2 * N] = dp
        return out

    # ---- équilibre statique -------------------------------------------------
    def equilibrium(self, q_in, tol=1e-12, n_iter=200):
        """État stationnaire : languette immobile, débit sortant = débit entrant.

        Résolu par point fixe sur la pression : `p` fixe l'ouverture via la
        déflexion statique, l'ouverture fixe le débit, le débit fixe `p`.
        """
        p = 100.0
        for _ in range(n_iter):
            q_stat = np.linalg.solve(self.K, p * self.gamma)
            tip = float(self.phi_tip @ q_stat)
            h = float(self.opening(tip))
            # p tel que le débit sortant égale le débit entrant
            denom = self.ch.cd * self.slot.width_m * h
            p_new = 0.5 * self.ch.rho * (q_in / denom) ** 2 if denom > 0 else p
            if abs(p_new - p) < tol * max(1.0, abs(p)):
                p = p_new
                break
            p = 0.5 * p + 0.5 * p_new       # sous-relaxation : le point fixe est raide
        q_stat = np.linalg.solve(self.K, p * self.gamma)
        state = np.zeros(2 * self.N + 1)
        state[self.N:2 * self.N] = q_stat
        state[2 * self.N] = p
        return state

    # ---- stabilité linéaire : le seuil de Hopf -----------------------------
    def jacobian(self, state, q_in, eps=1e-9):
        """Jacobienne numérique du champ de vecteurs autour de `state`."""
        n = state.size
        J = np.zeros((n, n))
        f0 = self.deriv(state, q_in)
        for k in range(n):
            d = eps * max(1.0, abs(state[k]))
            s2 = state.copy()
            s2[k] += d
            J[:, k] = (self.deriv(s2, q_in) - f0) / d
        return J

    def growth_rate(self, q_in):
        """Taux de croissance maximal (partie réelle) à l'équilibre, et la
        fréquence associée. Positif = l'équilibre est instable, donc l'anche
        démarre : c'est la condition d'auto-oscillation."""
        st = self.equilibrium(q_in)
        ev = np.linalg.eigvals(self.jacobian(st, q_in))
        i = int(np.argmax(ev.real))
        return float(ev[i].real), float(abs(ev[i].imag) / (2 * np.pi)), st[2 * self.N]

    def hopf_threshold(self, q_lo=1e-7, q_hi=1e-3, n_iter=60):
        """Débit d'entrée seuil `q_on` où l'équilibre devient instable.

        Dichotomie sur le signe du taux de croissance. Renvoie
        `(q_on, p_on, f_on)` — débit, surpression et fréquence au seuil —
        ou `None` si aucun changement de signe dans l'intervalle.
        """
        r_lo = self.growth_rate(q_lo)[0]
        r_hi = self.growth_rate(q_hi)[0]
        if r_lo > 0 or r_hi < 0:
            return None
        for _ in range(n_iter):
            q_mid = np.sqrt(q_lo * q_hi)        # dichotomie géométrique
            if self.growth_rate(q_mid)[0] < 0:
                q_lo = q_mid
            else:
                q_hi = q_mid
        r, f, p = self.growth_rate(q_hi)
        return float(q_hi), float(p), float(f)

    # ---- simulation ---------------------------------------------------------
    def simulate(self, dur, fs=44100.0, q_in=1e-5, oversample=8, state0=None):
        """Intègre le modèle (RK4 suréchantillonné) et renvoie les signaux.

        `oversample` : le couplage anche/chambre est raide ; à 44,1 kHz seul
        un RK4 explicite diverge. 8 suffit aux valeurs par défaut.
        """
        N = self.N
        n = int(dur * fs)
        sub = max(1, int(oversample))
        dt = 1.0 / (fs * sub)

        s = self.equilibrium(q_in) if state0 is None else np.array(state0, float)
        s[:N] += 1e-6                    # petite impulsion : on cherche si ça diverge

        tip = np.zeros(n); pres = np.zeros(n); op = np.zeros(n); fo = np.zeros(n)
        for i in range(n):
            for _ in range(sub):
                k1 = self.deriv(s, q_in)
                k2 = self.deriv(s + 0.5 * dt * k1, q_in)
                k3 = self.deriv(s + 0.5 * dt * k2, q_in)
                k4 = self.deriv(s + dt * k3, q_in)
                s = s + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
                if not np.isfinite(s).all():
                    raise FloatingPointError(
                        "divergence numérique : augmente `oversample`")
            y = float(self.phi_tip @ s[N:2 * N])
            h = float(self.opening(y))
            tip[i] = y; pres[i] = s[2 * N]; op[i] = h
            fo[i] = self._flow_out(s[2 * N], h)
        return OscillationResult(np.arange(n) / fs, tip, pres, op, fo)

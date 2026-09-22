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

6. **La languette ne comprime pas sa chambre.** C'est la différence entre
   battante et libre, et elle tient dans `Slot.sweep_coupling`. Une anche
   battante ferme l'ouverture : son balayage `Γ·ẏ` est un vrai piston. Une
   anche libre est *dans* sa fente : ce qu'elle déplace transite par la fente
   elle-même, que `opening()` module déjà. Le compter deux fois ajoutait une
   raideur d'air parasite et faisait chanter une anche de 102 Hz à 119 Hz —
   +267 cents, une tierce mineure.

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
    """Chambre d'anche alimentée en débit.

    `volume_m3` est le **volume acoustique effectif** : la chambre
    géométrique, plus ce que le canal du sommier et le couplage au réservoir
    du soufflet ajoutent de compliance. Le défaut est la chambre géométrique
    de l'anche de référence (35 × 15 × 15 mm ≈ 7,9 cm³) ; c'est une cote que
    tu peux mesurer, et un point de départ honnête.

    Il a longtemps fallu le gonfler à 40 cm³ pour que le modèle démarre. Ce
    n'était pas de la physique, c'était le symptôme d'un terme de balayage
    qui n'avait pas lieu d'être (cf. `Slot.sweep_coupling`) : une fois celui-
    ci retiré, la chambre réelle suffit largement.

    Il reste un paramètre de recalage, et il compte : plus elle est petite,
    plus le ressort d'air raidit l'ensemble et plus la note monte au-dessus
    de la fréquence propre de la lame (+30 cents à 7,9 cm³, +9 cents à
    40 cm³ pour l'anche de référence). **Mesurer ce décalage, c'est mesurer
    le volume effectif** — et ton accordeur le lit au dixième de cent.
    """
    volume_m3: float = 7.9e-6      # chambre géométrique 35 x 15 x 15 mm
    patm: float = 1e5
    gamma: float = 1.4             # exposant adiabatique de l'air
    rho: float = 1.2
    cd: float = 0.65               # coefficient de décharge de la fente


@dataclass
class Source:
    """Alimentation en débit, avec **impédance interne finie**.

    Une source de débit idéale imposerait `q_in` quoi qu'il arrive, y compris
    quand la languette ferme la fente : la pression y ferait alors un coup de
    bélier sans limite, et l'amplitude de l'anche croîtrait indéfiniment.

    Une turbine réelle, comme un soufflet réel, débite **moins** quand la
    pression monte : `q = q₀ − p/R`. C'est cette pente qui borne l'amplitude.
    `R` est la pente de la caractéristique (p, q) de ta source — celle que le
    balayage du facteur `Section` de `Mesures.py` permet de mesurer
    directement. `inf` redonne la source idéale.
    """
    impedance_pa_s_m3: float = 2.0e8     # à recaler sur la caractéristique mesurée


@dataclass
class Slot:
    """Fente et languette : la géométrie qui module le débit.

    `sweep_coupling` — **la languette comprime-t-elle la chambre ?**

    C'est la différence entre une anche battante et une anche libre, et elle
    ne se voit nulle part ailleurs dans les équations.

    Une anche **battante** (clarinette, hautbois) est plaquée sur la table :
    elle *ferme* l'ouverture. C'est un vrai piston dans la paroi de la
    cavité, et le volume qu'elle balaie, `Γ·ẏ`, comprime bel et bien l'air
    qui s'y trouve. Coefficient **1**.

    Une anche **libre** est *dans* sa fente, à quelques dizaines de microns
    de jeu. Quand elle s'écarte, ce qu'elle libère d'un côté de la plaque est
    repris dans l'instant par la fente elle-même — qui est exactement là où
    elle se trouve. Elle ne comprime rien : elle **module une ouverture**, ce
    dont `opening()` rend déjà compte. Compter en plus son balayage, c'est
    compter son déplacement deux fois. Coefficient **0**.

    Ce n'est pas un détail de second ordre. Le terme fantôme ajoutait une
    raideur d'air `γ·P_atm·Γ²/V₀` en série avec celle de la lame et faisait
    chanter une anche de 102,1 Hz à 119,2 Hz — **+267 cents, une tierce
    mineure**. Il obligeait aussi à gonfler la chambre à 40 cm³ pour obtenir
    un démarrage, là où la chambre géométrique (7,9 cm³) suffit une fois le
    terme retiré. Deux symptômes, une seule cause.

    Une anche libre réelle n'est pas exactement à 0 — la levée la place un
    peu hors du plan de la plaque, et la languette a une épaisseur — mais
    l'écart est du second ordre. C'est un paramètre à recaler au banc, et le
    décalage de justesse en est la mesure la plus directe, puisque la
    fréquence de jeu en dépend au premier ordre.
    """
    width_m: float = 4.8e-3        # largeur de la fente
    rest_offset_m: float = 0.10e-3 # décalage de la languette au repos
    max_open_m: float = 0.50e-3    # ouverture au-delà de laquelle l'aire sature
    leak_m: float = 2.0e-6         # fuite résiduelle fente fermée (plaque réelle)
    sweep_coupling: float = 0.0    # 0 = anche libre (dans la fente), 1 = battante


@dataclass
class OscillationResult:
    t: np.ndarray
    tip: np.ndarray                # déplacement du bout (m)
    pressure: np.ndarray           # surpression de chambre (Pa)
    opening: np.ndarray            # hauteur d'ouverture (m)
    flow_out: np.ndarray           # débit sortant (m³/s)
    final_state: np.ndarray = None  # état final, pour enchaîner une simulation

    @property
    def radiated(self):
        """Proxy du son rayonné en champ lointain : `dq/dt`.

        Une anche libre rayonne par le **débit modulé** à travers la fente,
        pas par la pression de chambre — et en champ lointain le rayonnement
        d'une source de débit suit sa dérivée. C'est cette grandeur qu'il faut
        écouter et dont il faut prendre le spectre.
        """
        dt = self.t[1] - self.t[0] if self.t.size > 1 else 1.0
        return np.gradient(self.flow_out) / dt


class FreeReedModel:
    """Anche libre multi-tronçon couplée à une chambre alimentée en débit."""

    def __init__(self, sections=None, chamber: Chamber | None = None,
                 slot: Slot | None = None, source: Source | None = None,
                 n_modes: int = 2, zeta: float = 0.004):
        self.sec = np.asarray(SECTIONS_DEFAULT if sections is None else sections, float)
        self.ch = chamber or Chamber()
        self.slot = slot or Slot()
        self.src = source or Source()
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
    def source_flow(self, q_command, p):
        """Débit réellement fourni : `q₀ − p/R`. Une turbine débite moins
        quand la pression monte — c'est ce qui empêche le coup de bélier
        illimité lorsque la languette ferme la fente.

        **Non borné à zéro, délibérément.** La soupape de cuir bloque le retour
        à travers la *fente* (cf. `_flow_out`), pas à travers la *source* : si
        la pression de chambre dépasse ce que le soufflet pousse, de l'air
        reflue en comprimant celui du soufflet, et c'est physique. Un `max(0,·)`
        planterait dans le champ de vecteurs un coude qui n'existe pas et
        déformerait le cycle limite près du pic de pression.

        Mesuré sur l'anche de référence, de 1,2× à 10× le seuil : le terme
        `p/R` **plafonne entre 5 et 39 %** de la consigne et n'en approche
        jamais 100 %, sur un facteur 8 de nuance. Le débit fourni reste positif
        sur 100 % des échantillons. C'est cohérent : plus on pousse, plus la
        pression monte, mais `R` la borne proportionnellement — le rapport se
        stabilise au lieu de diverger. L'inversion de signe n'est donc pas un
        cas limite rare, c'est un cas que le modèle ne produit pas.

        Si elle survenait, ce serait le signe d'une simulation qui diverge — et
        la borner à zéro ne ferait que le masquer."""
        R = self.src.impedance_pa_s_m3
        if not np.isfinite(R):
            return q_command
        return q_command - p / R

    def deriv(self, state, q_in):
        """Dérivée de l'état `[q̇ (N), q (N), p]`. `p` = surpression (Pa).

        `q_in` est la **consigne** de la source ; le débit réellement fourni
        tient compte de son impédance interne (cf. `source_flow`).
        """
        N = self.N
        dq, q, p = state[:N], state[N:2 * N], state[2 * N]

        tip = float(self.phi_tip @ q)
        h = float(self.opening(tip))
        q_out = self._flow_out(p, h)
        # Balayage de la languette. Pour une anche **libre** il ne charge pas
        # la compliance de la chambre (cf. `Slot.sweep_coupling`) : le volume
        # qu'elle déplace transite par la fente qu'elle module.
        q_reed = self.slot.sweep_coupling * float(self.gamma @ dq)
        q_in = self.source_flow(q_in, p)

        # Anche : la surpression de chambre pousse la languette hors de la fente.
        ddq = self.Minv @ (p * self.gamma - self.K @ q - self.C @ dq)

        # Chambre rigide, isentropique : la pression suit le bilan de débit.
        # `q_reed` est nul pour une anche libre — voir ci-dessus.
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
            # p tel que le débit sortant égale le débit **réellement fourni**
            # par la source (qui débite moins quand la pression monte)
            denom = self.ch.cd * self.slot.width_m * h
            q_eff = max(self.source_flow(q_in, p), 0.0)
            p_new = 0.5 * self.ch.rho * (q_eff / denom) ** 2 if denom > 0 else p
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
        démarre : c'est la condition d'auto-oscillation.

        **Ce qui entretient, ce qui dissipe.** En linéarisant autour de
        l'équilibre, le débit sortant rétroagit sur la languette avec un
        retard fixé par la compliance de la chambre. Ce déphasage donne à la
        force de pression une composante en phase avec la **vitesse** :

            anti-amortissement  ≈  Γ · a · (∂q_out/∂y) / [(a·∂q_out/∂p)² + ω²]

        avec `a = γ_air·P_atm/V₀` la raideur du ressort d'air. L'anche démarre
        quand ce terme dépasse son amortissement propre `2ζω·m`.

        Une version antérieure retranchait à droite un terme `Γ·a·∂q_out/∂p`,
        la réaction du ressort d'air au **balayage** de la languette. Il
        n'existe pas pour une anche libre (cf. `Slot.sweep_coupling`) : la
        languette est dans sa fente, elle ne comprime rien. C'est lui qui
        rendait le démarrage si difficile qu'il fallait un volume de chambre
        cinq fois trop grand, et qui remontait la note de 267 cents.

        Conséquence à ne pas manquer : si l'ouverture **sature** (languette
        soufflée hors de la fente), alors `∂h/∂y = 0`, donc `∂q_out/∂y = 0` —
        le terme d'entretien s'annule et l'oscillation cesse, quelle que soit
        la pression. C'est l'étouffement, et c'est ce qui borne la bande
        d'instabilité par le haut (cf. `instability_band`).
        """
        st = self.equilibrium(q_in)
        ev = np.linalg.eigvals(self.jacobian(st, q_in))
        i = int(np.argmax(ev.real))
        return float(ev[i].real), float(abs(ev[i].imag) / (2 * np.pi)), st[2 * self.N]

    def _bisect(self, q_a, q_b, want_positive_at_b, n_iter=50):
        """Dichotomie géométrique sur le changement de signe du taux."""
        for _ in range(n_iter):
            q_mid = np.sqrt(q_a * q_b)
            pos = self.growth_rate(q_mid)[0] > 0
            if pos == want_positive_at_b:
                q_b = q_mid
            else:
                q_a = q_mid
        return q_b

    def instability_band(self, q_lo=1e-7, q_hi=1e-2, n_scan=40):
        """Bande de débit où l'anche s'auto-entretient.

        L'instabilité n'est **pas** un demi-axe : elle est bornée des deux
        côtés. En dessous du seuil bas, il n'y a pas assez d'énergie pour
        démarrer. Au-dessus du seuil haut, la languette est soufflée
        grande ouverte, l'ouverture **sature**, `∂h/∂y` s'annule — elle ne
        module plus le débit et l'oscillation s'éteint. C'est
        l'**étouffement** que tout accordéoniste connaît en poussant trop
        fort.

        Renvoie `(seuil_bas, seuil_haut)`, chacun `(q, p, f)` ou `None`.
        """
        qs = np.geomspace(q_lo, q_hi, int(n_scan))
        signs = [self.growth_rate(q)[0] > 0 for q in qs]

        bas = haut = None
        for i in range(len(qs) - 1):
            if not signs[i] and signs[i + 1] and bas is None:
                q = self._bisect(qs[i], qs[i + 1], True)
                r, f, p = self.growth_rate(q)
                bas = (float(q), float(p), float(f))
            elif signs[i] and not signs[i + 1] and bas is not None and haut is None:
                q = self._bisect(qs[i], qs[i + 1], False)
                r, f, p = self.growth_rate(q)
                haut = (float(q), float(p), float(f))
        return bas, haut

    def hopf_threshold(self, q_lo=1e-7, q_hi=1e-2, n_scan=40):
        """Seuil de démarrage `(q_on, p_on, f_on)`, ou `None` s'il n'y en a pas.

        C'est le seuil **bas** de `instability_band` : la grandeur que
        `seuil.py` et `bifurcation.py` mesurent au banc.
        """
        bas, _ = self.instability_band(q_lo, q_hi, n_scan)
        return bas

    # ---- hystérésis : le seuil d'extinction --------------------------------
    def extinction_threshold(self, q_on=None, start_mult=2.5, mults=None,
                             fs=44100.0, dur=2.5, oversample=16, tol_mm=0.05):
        """Seuil d'**extinction** `p_off`, et rapport d'hystérésis `p_on/p_off`.

        On établit d'abord un cycle limite bien au-dessus du seuil, puis on
        **repart de cet état exact** en baissant la consigne. Si l'oscillation
        persiste en dessous du seuil de démarrage, la bifurcation est
        **sous-critique** : `p_on > p_off`, avec hystérésis. C'est le
        comportement attendu d'une anche réelle, et c'est ce que `seuil.py`
        mesure au banc par rampe montante puis descendante.

        Le point crucial est la **reprise exacte de l'état** : reconstruire
        approximativement l'état modal à partir du seul déplacement du bout
        est sous-déterminé (N modes pour un scalaire) et donne une réponse
        fausse — testé, ça concluait à tort au supercritique.

        Renvoie `{p_on, p_off, ratio, q_off}` ; `p_off` vaut `nan` si
        l'oscillation ne survit à aucune des consignes essayées.
        """
        if q_on is None:
            bas = self.hopf_threshold()
            if bas is None:
                return dict(p_on=float('nan'), p_off=float('nan'),
                            ratio=float('nan'), q_off=float('nan'))
            q_on = bas[0]
        p_on = float(self.equilibrium(q_on)[2 * self.N])

        base = self.simulate(dur, fs=fs, q_in=q_on * start_mult, oversample=oversample)
        n_tail = int(0.2 * dur * fs)

        if mults is None:
            mults = (0.95, 0.90, 0.85, 0.82, 0.79, 0.76, 0.70)

        q_off = p_off = float('nan')
        for m in mults:
            r = self.simulate(dur, fs=fs, q_in=q_on * m, oversample=oversample,
                              state0=base.final_state)
            course_mm = float(np.ptp(r.tip[-n_tail:])) * 1e3
            if course_mm <= tol_mm:
                break
            q_off = q_on * m
            p_off = float(self.equilibrium(q_off)[2 * self.N])

        ratio = p_on / p_off if np.isfinite(p_off) and p_off > 0 else float('nan')
        return dict(p_on=p_on, p_off=p_off, ratio=ratio, q_off=q_off)

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

        if state0 is None:
            s = self.equilibrium(q_in)
            s[:N] += 1e-6                # petite impulsion pour révéler une instabilité
        else:
            # reprise exacte : surtout ne rien perturber, sinon on ne peut pas
            # tester l'hystérésis (la persistance du cycle sous le seuil).
            s = np.array(state0, dtype=float)

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
        return OscillationResult(np.arange(n) / fs, tip, pres, op, fo,
                                 final_state=s.copy())

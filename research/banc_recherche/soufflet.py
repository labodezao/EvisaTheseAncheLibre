"""Étage soufflet : du geste du musicien à la pression du soufflet.

Ce qui manquait. Le chapitre « Le soufflet » de la thèse le dit en une phrase
(`docs/these_parties_2_a_5_fr.md`, l. 1168-1170) : « Le soufflet a aussi une
souplesse propre et la main derrière ; […] aucun n'est dans un modèle. » Les
modèles recevaient une commande de jeu **constante** (`HybridVoice.simulate`,
`level`) ou une rampe de 20 ms posée sans mesure (l. 1152). Rien ne bornait ce
qu'un bras peut faire. Un MIDI rejoué pouvait donc faire bouger le soufflet
plus vite qu'une main.

Cet étage se place **en amont** de la voix. Il ne dépend pas du choix de
l'excitateur (l'audit du 11/11/2026 garde ouvert le remplacement de
`FreeReedExciter`) : il rend une pression, et `niveau_pour` la traduit dans la
commande de n'importe quelle voix à source finie.

La chaîne
---------
::

    geste : expression 0..1 et sens (+1 poussé, -1 tiré),
            ou pression demandée signée p_dem(t), en Pa
      │
      ▼  bras : bande du geste (passe-bas causal), puis pente bornée en montée
      │         et en descente, temps mort au changement de sens
    p_bras(t) = F/S                      (04_soufflet_fr.md, l. 17)
      │
      ▼  main et air : source à résistance interne (q = q0 - p/R, l. 11),
      │  vitesse de main bornée, souplesse de l'air, fuites, débit des anches
      │      C dp/dt = sat((p_bras - p)/R_bras, ±S·v_max) - Q_anches(p) - Q_fuite(p)
    p(t), pression commune à toutes les notes
      │
      ▼  niveau_pour(exciter, p) : |p|/R_passage (équivalent de Norton) en m³/s
    level(t) de la voix (`HybridVoice.simulate`, `live.Synth`)

Le bras travaille dans une coordonnée w, logarithmique au-dessus d'un genou
p_genou et linéaire au-dessous (`Soufflet._w`). Au-dessus du genou, une pente
bornée en w est une pente bornée en dB : c'est l'unité des pentes mesurées, là
où une anche parle. Au-dessous, elle devient une pente en Pa/s : la force du
bras passe par zéro en un temps fini, ce qu'un logarithme pur interdirait. Le
changement de sens est donc un passage par w = 0, suivi du temps mort.

Les constantes
--------------
Chacune est dans `BORNES`, avec sa valeur, son unité, son statut et sa source
(fichier et ligne). Statuts : *mesuré*, *calculé*, *à confirmer* (écrit dans
une source, pas mesuré), *non décidé* (ni mesuré ni écrit : la valeur est
**provisoire** et le dit). Les pentes et la bande viennent de l'outil audio
vers MIDI d'Ewen, mesurées sur le niveau sonore commun de notes tenues :
`data/soufflet_20261120/LISEZMOI.md`. Leur passage du niveau sonore à la
pression demande une loi niveau-pression que personne n'a mesurée (`gamma`).

Ce que l'étage ne fait pas : la note. L'attaque (τ de 54 ms sur le H6), la
fermeture de soupape et l'extinction appartiennent à chaque note, jamais au
soufflet (même relevé). Le modèle de voix n'a qu'une lame : au tiré, c'est
l'autre lame de la plaque qui parle (soupape, these l. 849-853) ; la voix
reçoit donc |p|.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .hybrid import CELERITE, RHO

L_MIN = 1.0e-3 / 60.0        # 1 L/min en m³/s

_D04 = "research/docs/design_practical/04_soufflet_fr.md"
_TH = "research/docs/these_parties_2_a_5_fr.md"
_DATA = "research/data/soufflet_20261120/LISEZMOI.md"
_AP = "research/docs/apports_these.md"
_V_AIR = 0.010               # m³, volume provisoire (voir BORNES)

#: Statuts permis (registre `docs/apports_these.md`, plus « non décidé »).
STATUTS = ("mesuré", "calculé", "à confirmer", "non décidé")

#: Les bornes retenues. Une valeur « non décidé » est provisoire et le dit.
BORNES = {
    "bande_geste_hz": dict(
        valeur=8.0, unite="Hz (-3 dB)", statut="mesuré",
        source=f"{_DATA} (outil audio vers MIDI, rapport v3c l. 247-248 : "
               "niveau commun de 78 et 12 paires de notes tenues, corrélé de "
               "0,5 à 8 Hz, 0,00 au-dessus)",
        note="mesuré sur le son, appliqué ici au bras par un passe-bas causal "
             "d'ordre 2 critique ; l'outil MIDI lisse par une gaussienne "
             "symétrique (non causale)"),
    "geste_bras_max_hz": dict(
        valeur=[4.0, 6.0], unite="Hz", statut="à confirmer",
        source="Neilson P. D. (1972), Medical & Biological Engineering, "
               "doi:10.1007/BF02474193, cité par le rapport v3c l. 261-262 "
               "(résumé seulement, non relu ici)",
        note="oscillation volontaire du coude ; non utilisée dans le calcul, "
             "plus basse que la bande mesurée"),
    "pente_montee_db_s": dict(
        valeur=120.0, unite="dB/s", statut="mesuré",
        source=f"{_DATA} (rapport v3c l. 249 et 271 : 99e centile pendant les "
               "tenues, 122 et 76 dB/s)",
        note="mesurée sur le niveau sonore pendant les tenues, hors attaques "
             "et fins : pente de jeu, pas la limite du bras"),
    "pente_descente_db_s": dict(
        valeur=190.0, unite="dB/s", statut="mesuré",
        source=f"{_DATA} (rapport v3c l. 249 et 271 : 159 et 186 dB/s)",
        note="idem"),
    "gamma_niveau_pression": dict(
        valeur=1.0, unite="dB de son par dB de pression", statut="non décidé",
        source="absente de 04_soufflet_fr.md, du chapitre « Le soufflet » et "
               "du rapport v3c",
        note="provisoire : 1 dB de son = 1 dB de pression ; règle le passage "
             "des pentes mesurées (dB de son) aux pentes de pression"),
    "pression_genou_pa": dict(
        valeur=300.0, unite="Pa", statut="non décidé",
        source=f"{_TH} l. 1166-1168 (seuils d'un vrai instrument : une "
               "centaine à un millier de Pa)",
        note="provisoire : milieu géométrique de 100 à 1000 Pa. Au-dessus, la "
             "pente mesurée en dB s'applique ; au-dessous (pas de son à "
             "mesurer), elle devient une pente en Pa/s"),
    "temps_mort_inversion_s": dict(
        valeur=0.02, unite="s", statut="non décidé",
        source="rapport v3c l. 266 et 303 : durée d'une inversion, rien de "
               f"sourcé ; {_TH} l. 959-962 (la soupape se soulève et retombe "
               "à chaque changement de sens, sans durée)",
        note="provisoire : même ordre que la montée de 20 ms du modèle à deux "
             f"anches, elle aussi sans mesure ({_TH} l. 1152)"),
    "pression_de_jeu_pa": dict(
        valeur=[500.0, 3000.0], unite="Pa, dans les deux signes",
        statut="à confirmer",
        source=f"{_TH} l. 1165-1166 (« de l'ordre de »)"),
    "surface_efficace_m2": dict(
        valeur=0.03, unite="m²", statut="à confirmer",
        source=f"{_D04} l. 33 (fenêtre de 150 à 400 cm² à 1000 Pa, calculée "
               "sur des chiffres ronds) ; se mesure par S = mg/p, l. 19",
        note="provisoire : 300 cm², dans la fenêtre"),
    "vitesse_main_max_m_s": dict(
        valeur=0.5, unite="m/s", statut="non décidé",
        source=f"{_D04} l. 33 (chiffres ronds : course 0,4 m, phrase 4 s, "
               "soit 0,1 m/s en moyenne)",
        note="provisoire : 5 fois la vitesse moyenne des chiffres ronds ; à "
             "mesurer en filmant la course avec une règle"),
    "resistance_bras_pa_s_m3": dict(
        valeur=1.4e5, unite="Pa·s/m³", statut="non décidé",
        source=f"{_D04} l. 9-13 et {_TH} l. 141-148 (q = q0 - p/R, R non "
               f"mesuré au soufflet) ; {_AP} section C (turbine du banc 2023 : "
               "0,5 à 1,4·10⁶, unité à confirmer)",
        note="provisoire : R·C = 10 ms. Borne calculée : R ≤ 8,686/(190·C) "
             "= 6,5·10⁵ pour que l'air seul ne ralentisse pas la descente "
             "mesurée de 190 dB/s ; la turbine du banc serait trop lente"),
    "volume_air_m3": dict(
        valeur=_V_AIR, unite="m³", statut="non décidé",
        source="audit du 14/11/2026 (MODELE-EWEN § 2.7 : 10 L, « cotes non "
               f"mesurées ») ; {_AP} l. 122 emploie 2 L",
        note="provisoire : 10 L, comme l'outil audio vers MIDI"),
    "souplesse_air_m3_pa": dict(
        valeur=_V_AIR / (RHO * CELERITE ** 2), unite="m³/Pa",
        statut="calculé",
        source="V/(ρc²), ρ et c de research/banc_recherche/hybrid.py l. 62-63",
        note="7,1·10⁻⁸ pour 10 L (adiabatique) ; isotherme : +40 %, à "
             "confirmer"),
    "souplesse_plis_m3_pa": dict(
        valeur=0.0, unite="m³/Pa", statut="non décidé",
        source=f"{_D04} l. 19 (les plis cèdent sous la pression) ; {_TH} "
               "l. 1168-1170 (se mesure au manomètre)",
        note="provisoire : 0"),
    "fuite_l_min_a_500pa": dict(
        valeur=1.0, unite="L/min à 500 Pa", statut="à confirmer",
        source=f"{_D04} l. 51 et {_TH} l. 1147-1149 (critère proposé, "
               "soufflet seul fermé ; un trou rond d'un peu plus de 1 mm)"),
    "contraction_fuite": dict(
        valeur=0.61, unite="-", statut="à confirmer",
        source=f"{_TH} l. 869-872 (loi d'orifice, 0,61 dans les modèles pour "
               "un jet à arête vive)"),
    "debit_anche_l_min": dict(
        valeur=10.0, unite="L/min à 1000 Pa", statut="à confirmer",
        source=f"{_D04} l. 33 (chiffre rond d'un forte) et l. 37 (les "
               "modèles donnent 6 à 24 L/min, jugés trop grands)",
        note="la pression de référence de 1000 Pa est celle de la fenêtre "
             "calculée l. 33"),
    "exposant_debit_anche": dict(
        valeur=0.5, unite="-", statut="calculé",
        source="loi d'orifice à ouverture fixe (q_out de FreeReedExciter, "
               "research/banc_recherche/hybrid.py l. 591)",
        note="le banc 2023 mesure 0,55 à 0,76 selon le dossier (audit du "
             "15/11/2026, non versé) : à confirmer"),
    "resistance_passage_voix": dict(
        valeur="celle de la voix", unite="Pa·s/m³", statut="à confirmer",
        source="pour l'accordéon, R suit la note : "
               "hybrid.ACCORDEON_SOURCE_REF × (f/110)² = 1,5·10⁷ à 110 Hz "
               "(provisoire, 24/11/2026 ; défaut de la classe FreeReedExciter "
               "resté à 2·10⁸) ; reed_oscillator.Source = 5·10⁶ (l. 122, « une "
               "restriction d'environ 8 mm², un canal de sommier »)",
        note="niveau_pour lit la résistance de la voix : la valeur de "
             "référence (1,5·10⁷ contre 5·10⁶ et 2·10⁸) reste à trancher par "
             "la mesure (rampe de pression étalonnée), pas ici"),
}


def souplesse_air(volume_m3):
    """Souplesse acoustique d'un volume d'air, V/(ρc²), en m³/Pa (adiabatique)."""
    return float(volume_m3) / (RHO * CELERITE ** 2)


def section_fuite(debit_l_min=1.0, pression_pa=500.0, contraction=0.61):
    """Section d'un orifice qui laisse passer `debit_l_min` à `pression_pa`.

    q = Cd·A·sqrt(2p/ρ). Avec le critère du livret (1 L/min à 500 Pa) et
    Cd = 0,61 : 9,5·10⁻⁷ m², un trou rond de 1,1 mm (these l. 1149 : « un peu
    plus de 1 mm »).
    """
    q = float(debit_l_min) * L_MIN
    return q / (float(contraction) * np.sqrt(2.0 * float(pression_pa) / RHO))


def pression_demandee(expression, sens=1.0, p_max=3000.0, gamma=1.0):
    """Commande d'expression (0..1, le CC 11 / 127) et sens → pression signée.

    Le rendu de l'outil audio vers MIDI joue le CC 11 en gain (cc/127)² ; un
    niveau sonore qui suit p^gamma demande donc p = p_max·e^(2/gamma).
    `p_max` : haut de la plage de jeu (these l. 1165, à confirmer) ; `gamma`
    non décidé (voir `BORNES`).
    """
    e = np.clip(np.asarray(expression, dtype='float64'), 0.0, 1.0)
    s = np.sign(np.asarray(sens, dtype='float64'))
    s = np.where(s == 0, 1.0, s)
    return s * float(p_max) * e ** (2.0 / float(gamma))


def niveau_pour(exciter, p):
    """Pression du soufflet → commande de jeu de la voix, dans son unité.

    Une anche libre se commande en débit de soufflet (m³/s) derrière une
    résistance R (`q_src = level - p_chambre/R`, hybrid.py l. 594-596). Une
    pression P derrière R, c'est la même source vue par Norton : level = P/R,
    donc q_src = (P - p_chambre)/R. R est alors la résistance du passage du
    soufflet à la lame. Une source parfaite (R infini) n'a pas de pression à
    recevoir : on le refuse au lieu d'inventer.

    Le modèle de voix n'a qu'une lame ; au tiré, c'est l'autre lame de la
    plaque qui parle : la voix reçoit |p|.
    """
    p = np.abs(np.asarray(p, dtype='float64'))
    unite = getattr(exciter, 'control_unit', '')
    if unite == "Pa":
        return p
    if unite == "m³/s":
        r = float(getattr(exciter, 'source_impedance', np.inf))
        if not np.isfinite(r) or r <= 0:
            raise ValueError("source parfaite (R infini) : une pression de "
                             "soufflet ne s'y traduit pas en débit")
        return p / r
    raise ValueError(f"commande en « {unite} » : pas une voix à soufflet")


@dataclass
class SouffletResultat:
    """Ce qui sort de l'étage, au pas de contrôle."""
    t: np.ndarray
    demande: np.ndarray       # pression demandée par le geste (Pa, signée)
    p_bras: np.ndarray        # F/S, ce que le bras impose (Pa, signée)
    p: np.ndarray             # pression dans le soufflet (Pa, signée)
    v_main: np.ndarray        # vitesse de la main (m/s, + = poussé)
    course: np.ndarray        # déplacement cumulé de la main (m)
    q_fuite: np.ndarray       # débit de fuite (m³/s)
    fs: float

    def niveau_db(self, ref=1.0):
        """Niveau de pression, 20·log10(|p|/ref)."""
        return 20.0 * np.log10(np.maximum(np.abs(self.p), 1e-9) / ref)


def _val(cle):
    return BORNES[cle]["valeur"]


@dataclass
class Soufflet:
    """Le soufflet et le bras qui le tient. Défauts : `BORNES`.

    Toutes les valeurs « non décidé » sont provisoires ; les changer ne
    demande que de passer le paramètre.
    """
    bande_hz: float = _val("bande_geste_hz")
    montee_db_s: float = _val("pente_montee_db_s")
    descente_db_s: float = _val("pente_descente_db_s")
    gamma: float = _val("gamma_niveau_pression")
    p_genou_pa: float = _val("pression_genou_pa")
    temps_mort_s: float = _val("temps_mort_inversion_s")
    surface_m2: float = _val("surface_efficace_m2")
    v_main_max: float = _val("vitesse_main_max_m_s")
    r_bras: float = _val("resistance_bras_pa_s_m3")
    volume_m3: float = _val("volume_air_m3")
    souplesse_plis: float = _val("souplesse_plis_m3_pa")
    fuite_l_min_500pa: float = _val("fuite_l_min_a_500pa")
    contraction: float = _val("contraction_fuite")
    debit_anche_l_min: float = _val("debit_anche_l_min")
    p_ref_debit: float = 1000.0
    exposant_debit: float = _val("exposant_debit_anche")
    p_lam: float = 1.0          # Pa : sous ce seuil les lois d'orifice sont
    #                             prolongées par une droite (numérique : leur
    #                             pente est infinie en zéro)
    _etat: dict = field(default_factory=dict, repr=False)

    def __post_init__(self):
        self.reset()

    # -- grandeurs dérivées ----------------------------------------------------
    @property
    def souplesse(self):
        """C = V/(ρc²) + souplesse des plis, en m³/Pa."""
        return souplesse_air(self.volume_m3) + float(self.souplesse_plis)

    @property
    def tau_air(self):
        """R_bras·C : le temps que met l'air à suivre le bras."""
        return self.r_bras * self.souplesse

    @property
    def k_montee(self):
        """Pente de montée dans la coordonnée w (1/s)."""
        return self.montee_db_s * np.log(10.0) / 20.0 / self.gamma

    @property
    def k_descente(self):
        return self.descente_db_s * np.log(10.0) / 20.0 / self.gamma

    def reset(self, p0=0.0):
        """Soufflet au repos (ou à la pression `p0`)."""
        self._etat = dict(f1=float(p0), f2=float(p0), w=self._w(p0),
                          signe=float(np.sign(p0)), zero_t=-np.inf, t=0.0,
                          p=float(p0), x=0.0)

    # -- lois ------------------------------------------------------------------
    def _w(self, p):
        """Coordonnée du bras : linéaire sous le genou, logarithmique au-dessus.

        w = |p|/p_g sous p_g, 1 + ln(|p|/p_g) au-dessus, signée ; continue et
        de pente continue au genou. Une pente bornée en w est donc une pente
        exacte en dB au-dessus du genou, une pente en Pa/s au-dessous.
        """
        a = abs(p) / self.p_genou_pa
        return float(np.sign(p) * (a if a <= 1.0 else 1.0 + np.log(a)))

    def _p(self, w):
        a = abs(w)
        return float(np.sign(w) * self.p_genou_pa
                     * (a if a <= 1.0 else np.exp(a - 1.0)))

    def _orifice(self, p, q_ref, p_ref, n):
        """q = q_ref·(|p|/p_ref)^n, signé, droit sous p_lam."""
        a = abs(p)
        if a >= self.p_lam:
            q = q_ref * (a / p_ref) ** n
        else:
            q = q_ref * (self.p_lam / p_ref) ** n * a / self.p_lam
        return np.sign(p) * q

    def debit_anches(self, p, n_anches=1.0):
        """Débit que prennent `n_anches` anches ouvertes, en m³/s."""
        return float(n_anches) * self._orifice(
            p, self.debit_anche_l_min * L_MIN, self.p_ref_debit,
            self.exposant_debit)

    def debit_fuite(self, p):
        """Fuite du soufflet : orifice dimensionné par le critère du livret."""
        q500 = self.fuite_l_min_500pa * L_MIN
        return self._orifice(p, q500, 500.0, 0.5)

    def _flux(self, p, p_bras, n_anches):
        """Débit net qui entre dans le volume d'air (m³/s)."""
        q_main = (p_bras - p) / self.r_bras
        q_max = self.surface_m2 * self.v_main_max
        q_main = min(max(q_main, -q_max), q_max)
        return q_main - self.debit_anches(p, n_anches) - self.debit_fuite(p)

    # -- un pas ----------------------------------------------------------------
    def _bras(self, p_dem, dt):
        """Passe-bas du geste, puis pente bornée et temps mort. Rend p_bras."""
        e = self._etat
        # passe-bas critique d'ordre 2 : deux pôles réels égaux, -3 dB à bande_hz
        w0 = 2.0 * np.pi * self.bande_hz / np.sqrt(np.sqrt(2.0) - 1.0)
        a = 1.0 - np.exp(-w0 * dt)
        e['f1'] += a * (p_dem - e['f1'])
        e['f2'] += a * (e['f1'] - e['f2'])
        cible = self._w(e['f2'])
        w = e['w']
        t = e['t']
        if w == 0.0:
            s_cible = np.sign(cible)
            inversion = (s_cible != 0 and e['signe'] != 0
                         and s_cible != e['signe'])
            if inversion and t - e['zero_t'] < self.temps_mort_s:
                return 0.0                       # temps mort : force nulle
            w = float(np.clip(cible, -self.k_montee * dt, self.k_montee * dt))
        elif np.sign(cible) != np.sign(w):       # vers zéro, puis l'autre sens
            pas = self.k_descente * dt
            if abs(w) <= pas:
                e['signe'] = float(np.sign(w))
                e['zero_t'] = t
                w = 0.0
            else:
                w -= np.sign(w) * pas
        elif abs(cible) > abs(w):
            w += np.sign(w) * min(abs(cible) - abs(w), self.k_montee * dt)
        else:
            w -= np.sign(w) * min(abs(w) - abs(cible), self.k_descente * dt)
        if w != 0.0:
            e['signe'] = float(np.sign(w))
        elif e['w'] != 0.0 and e['zero_t'] < t:
            e['zero_t'] = t
        e['w'] = w
        return self._p(w)

    def _dorifice(self, p, q_ref, p_ref, n):
        """Pente dq/dp de `_orifice` (positive)."""
        a = abs(p)
        if a >= self.p_lam:
            return n * q_ref * (a / p_ref) ** n / a
        return q_ref * (self.p_lam / p_ref) ** n / self.p_lam

    def _dflux(self, p, p_bras, n_anches):
        """Pente du flux net en p (négative ou nulle)."""
        d = 0.0
        if abs((p_bras - p) / self.r_bras) < self.surface_m2 * self.v_main_max:
            d -= 1.0 / self.r_bras
        d -= float(n_anches) * self._dorifice(
            p, self.debit_anche_l_min * L_MIN, self.p_ref_debit,
            self.exposant_debit)
        d -= self._dorifice(p, self.fuite_l_min_500pa * L_MIN, 500.0, 0.5)
        return d

    def _air(self, p_bras, n_anches, dt):
        """Euler implicite de C dp/dt = flux(p).

        flux décroît avec p, donc g(p1) = C(p1 - p0)/dt - flux(p1) croît : une
        seule racine, encadrée entre p0 et p0 + dt·flux(p0)/C. Newton, repli
        sur la bissection s'il sort de l'encadrement.
        """
        e = self._etat
        c = self.souplesse
        p0 = e['p']
        f0 = self._flux(p0, p_bras, n_anches)
        borne = p0 + dt * f0 / c
        lo, hi = (p0, borne) if borne >= p0 else (borne, p0)
        x = borne
        for _ in range(50):
            g = c * (x - p0) / dt - self._flux(x, p_bras, n_anches)
            if g > 0:
                hi = x
            else:
                lo = x
            dg = c / dt - self._dflux(x, p_bras, n_anches)
            x_new = x - g / dg
            if not lo <= x_new <= hi:
                x_new = 0.5 * (lo + hi)
            if abs(x_new - x) < 1e-7 or hi - lo < 1e-7:
                x = x_new
                break
            x = x_new
        p1 = x
        q_main = c * (p1 - p0) / dt + self.debit_anches(p1, n_anches)             + self.debit_fuite(p1)
        e['p'] = p1
        v = q_main / self.surface_m2
        e['x'] += v * dt
        return p1, v

    def pas(self, p_dem, dt, n_anches=1.0):
        """Avance d'un pas `dt` vers la demande `p_dem` (Pa, signée).

        Rend (p, p_bras, v_main). C'est l'interface temps réel (`live.Synth`).
        """
        p_bras = self._bras(float(p_dem), dt)
        p, v = self._air(p_bras, n_anches, dt)
        self._etat['t'] += dt
        return p, p_bras, v

    def simuler(self, demande, fs=2000.0, n_anches=1.0):
        """Rejoue une pression demandée (tableau, Pa, signée) au pas 1/fs."""
        demande = np.asarray(demande, dtype='float64')
        n = demande.size
        na = np.broadcast_to(np.asarray(n_anches, dtype='float64'), (n,))
        dt = 1.0 / float(fs)
        self.reset()
        p = np.zeros(n)
        pb = np.zeros(n)
        v = np.zeros(n)
        x = np.zeros(n)
        qf = np.zeros(n)
        for i in range(n):
            p[i], pb[i], v[i] = self.pas(demande[i], dt, na[i])
            x[i] = self._etat['x']
            qf[i] = self.debit_fuite(p[i])
        return SouffletResultat(t=np.arange(n) * dt, demande=demande,
                                p_bras=pb, p=p, v_main=v, course=x,
                                q_fuite=qf, fs=float(fs))


def jouer(voix, demande, fs=44100.0, fs_soufflet=2000.0, n_anches=1.0,
          soufflet=None, **kw):
    """Le modèle physique entier : geste → soufflet → voix.

    `demande` : pression demandée (Pa, signée) au pas 1/fs_soufflet. Le
    soufflet rend p(t) ; on l'interpole au pas audio, on le traduit dans la
    commande de la voix (`niveau_pour`) et la voix sonne avec ce niveau qui
    varie. Rend (VoiceResult, SouffletResultat).
    """
    s = soufflet if soufflet is not None else Soufflet()
    res_s = s.simuler(demande, fs=fs_soufflet, n_anches=n_anches)
    dur = res_s.t.size / float(fs_soufflet)
    n_audio = int(dur * fs)
    t_audio = np.arange(n_audio) / float(fs)
    p_audio = np.interp(t_audio, res_s.t, res_s.p)
    level = niveau_pour(voix.exciter, p_audio)
    res_v = voix.simulate(dur, fs=fs, level=level, **kw)
    return res_v, res_s


def bornes_json():
    """Les bornes, sous la forme écrite dans `soufflet_modele_physique.json`."""
    out = {}
    for cle, b in BORNES.items():
        out[cle] = dict(valeur=b["valeur"], unite=b["unite"], statut=b["statut"],
                        provisoire=(b["statut"] == "non décidé"),
                        source=b["source"], **({"note": b["note"]}
                                               if "note" in b else {}))
    return out

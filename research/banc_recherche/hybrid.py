"""Modèle physique hybride, généralisé aux instruments auto-entretenus.

`reed_oscillator` modélise **une** chose : l'anche libre de l'accordéon. Ce
module reprend la même physique mais la pose dans le cadre qui la dépasse —
celui de McIntyre, Schumacher & Woodhouse (1983), qui ont montré que l'anche,
l'archet et le jet de flûte ne sont pas trois problèmes mais **un seul** :

    un excitateur non linéaire  ⟷  un résonateur linéaire

L'excitateur ne sait rien faire d'autre que transformer, instantanément, ce
que le résonateur lui présente. Le résonateur ne sait rien faire d'autre que
se souvenir. Toute la vie de l'instrument — le seuil, le cycle limite,
l'hystérésis, le timbre — naît de leur boucle, et de rien d'autre.

C'est vrai de l'anche libre comme du reste, et c'est ce qui rend la
généralisation possible :

| famille                  | excitateur        | résonateur         | couple  |
|--------------------------|-------------------|--------------------|---------|
| accordéon, harmonica     | anche libre       | chambre (ressort)  | (p, q)  |
| clarinette, saxophone    | anche simple      | perce              | (p, q)  |
| cornemuse, bombarde      | anche double      | perce conique      | (p, q)  |
| violon, vielle à roue    | frottement archet | corde + corps      | (v, F)  |

Les deux dernières colonnes disent tout. Un tuyau rend une **pression** quand
on lui injecte un **débit** ; une corde rend une **vitesse** quand on lui
applique une **force**. Effort et flux échangent leurs rôles, mais la
structure mathématique est identique — d'où un seul `Resonator` pour les
quatre familles.

Pourquoi « hybride »
--------------------
Parce qu'on ne prétend pas inverser un son vers un modèle physique complet :
c'est sous-déterminé, et `sample_extract.extract_multi` en fait la
démonstration. On fait la part des choses :

- le **résonateur** est *mesuré* — ses modes sortent de l'analyse du son ;
- la **famille d'excitateur** est *connue a priori* — on sait si on écoute un
  saxophone ou un violon ;
- les **paramètres de l'excitateur** sont *ajustés* sur quelques descripteurs
  robustes (seuil, pente spectrale, temps d'attaque, brillance vs nuance).

Voir `identify.py` pour cette partie-là. Ici, seulement la physique.

Le résonateur de l'accordéon est un cas dégénéré : pas de mode, juste une
compliance (le ressort d'air). C'est pour ça qu'une anche libre joue à sa
propre fréquence alors qu'une anche de saxophone joue à celle du tuyau.
Le tableau ci-dessus contient déjà cette différence.

⚠️ `reed_oscillator.FreeReedModel` reste la **référence validée** pour la
thèse : languette multimodale (Rayleigh-Ritz), seuils par analyse de
stabilité linéaire. `FreeReedExciter` en est une réduction à un mode, pour
que l'accordéon passe par le même tuyau que les autres dans l'interface. Les
deux ne donnent pas les mêmes chiffres et ne le prétendent pas.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

RHO = 1.2          # masse volumique de l'air (kg/m³)
CELERITE = 343.0   # célérité du son (m/s)
GAMMA = 1.4        # coefficient adiabatique
PATM = 101325.0    # pression atmosphérique (Pa)


# =============================================================================
# Résonateur — commun aux quatre familles
# =============================================================================

@dataclass
class Mode:
    """Un mode de résonance : fréquence, acuité, et hauteur du sommet.

    `peak` est la valeur de |Z| (Pa·s/m³, instruments à vent) ou de |Y|
    (m/s/N, cordes frottées) **au sommet** de la résonance. C'est le
    paramétrage le plus direct, parce que c'est précisément ce qu'on lit sur
    une courbe mesurée — et donc ce que `sample_extract` sait rendre.
    """
    freq_hz: float
    q: float = 30.0
    peak: float = 1.0

    @property
    def omega(self):
        return 2.0 * np.pi * self.freq_hz


class Resonator:
    """Banc de modes amortis, plus une compliance optionnelle.

    Chaque mode suit `ẍ + (ω/Q)ẋ + ω²x = u` et contribue `peak·(ω/Q)·ẋ` à la
    réponse — une forme qui s'annule à fréquence nulle, comme il se doit pour
    un tuyau ouvert : souffler un débit continu dans une clarinette n'y
    installe aucune pression continue.

    La `compliance` (m³/Pa) est là pour le cas contraire : une **cavité
    fermée**, où un débit continu fait bel et bien monter la pression. C'est
    le ressort d'air de l'accordéon, et c'est toute la différence entre une
    anche qui impose sa hauteur et une anche qui la subit.

    Passer les deux est licite : un tuyau porté par un réservoir, comme le sac
    d'une cornemuse.
    """

    def __init__(self, modes=None, compliance=None, name=""):
        self.modes = list(modes or [])
        self.compliance = compliance
        self.name = name
        self.n_modes = len(self.modes)
        self.n_state = 2 * self.n_modes + (1 if compliance else 0)

        self.omega = np.array([m.omega for m in self.modes], dtype='float64')
        self.q_fac = np.array([max(m.q, 1e-3) for m in self.modes], dtype='float64')
        self.gain = np.array([m.peak for m in self.modes], dtype='float64') * \
            (self.omega / self.q_fac if self.n_modes else 0.0)

    # -- état : [x (N), ẋ (N), p_cavité] -------------------------------------
    def response(self, state):
        """Ce que le résonateur présente à l'excitateur (Pa, ou m/s)."""
        n = self.n_modes
        out = float(self.gain @ state[n:2 * n]) if n else 0.0
        if self.compliance:
            out += float(state[2 * n])
        return out

    def deriv(self, state, drive):
        """Dérivée de l'état pour une injection `drive` (m³/s, ou N)."""
        n = self.n_modes
        d = np.zeros_like(state)
        if n:
            x, v = state[:n], state[n:2 * n]
            d[:n] = v
            d[n:2 * n] = drive - self.omega ** 2 * x - (self.omega / self.q_fac) * v
        if self.compliance:
            d[2 * n] = drive / self.compliance
        return d

    def __repr__(self):
        f = ", ".join(f"{m.freq_hz:.0f}" for m in self.modes[:4])
        return (f"<Resonator {self.name or '?'} {self.n_modes} modes [{f}…] "
                f"compliance={self.compliance}>")


# -- fabriques de résonateurs -------------------------------------------------

def z_char(bore_diameter_m):
    """Impédance caractéristique `ρc/S` d'une perce de ce diamètre.

    C'est la grandeur qui explique la famille entière. Une perce étroite
    oppose une impédance élevée, donc réagit fort à un petit débit : une
    bombarde (Ø 5 mm) présente **8 fois** l'impédance d'une clarinette
    (Ø 14,6 mm). D'où sa pression de jeu considérable, son anche minuscule et
    raide — et le fait qu'elle porte par-dessus un fest-noz entier.
    """
    return RHO * CELERITE / (np.pi * (float(bore_diameter_m) / 2.0) ** 2)


def bore_modes(f0_hz, n_modes=8, kind='conique', q=35.0, z_peak=2.0e7,
               decay=1.0):
    """Modes d'une perce dont la note fondamentale est `f0_hz`.

    `kind` change **la série harmonique elle-même**, et c'est la différence
    acoustique la plus audible entre une clarinette et un saxophone :

    - `'cylindrique'` — tuyau fermé à l'anche, ouvert au bout : seuls les
      rangs **impairs** résonnent (f0, 3f0, 5f0…). Le son creux de la
      clarinette, et son registre qui saute à la douzième et non à l'octave.
    - `'conique'` — cône : la série **complète** (f0, 2f0, 3f0…). Saxophone,
      bombarde, chalumeau de cornemuse. Registre à l'octave.

    `z_peak` n'est pas un réglage esthétique : c'est **lui qui décide si
    l'instrument parle**. L'anche ne s'entretient que si sa conductance
    négative `|∂q/∂Δp|` dépasse les pertes du résonateur `1/z_peak`. Trop bas,
    on obtient une sinusoïde anémique au lieu d'un son. Les valeurs par défaut
    valent 20 à 30 × l'impédance caractéristique `ρc/S`, ce que donnent les
    mesures d'impédance publiées.

    `decay` étale la décroissance des sommets avec le rang (1/n par défaut) :
    une perce réelle perd ses résonances aiguës par rayonnement et pertes
    visco-thermiques. Ordre de grandeur à recaler sur une mesure d'impédance ;
    `transfer.py` sait la faire.
    """
    n = np.arange(1, int(n_modes) + 1)
    if kind == 'cylindrique':
        ratios = 2 * n - 1
    elif kind == 'conique':
        ratios = n
    else:
        raise ValueError("kind doit valoir 'cylindrique' ou 'conique'")
    return [Mode(freq_hz=float(f0_hz * r), q=float(q),
                 peak=float(z_peak / (i + 1) ** decay))
            for i, r in enumerate(ratios)]


def string_modes(f0_hz, n_modes=16, beta=1.0 / 7.0, mass_kg=3.5e-4, q=500.0,
                 inharmonicity=0.0, q_decay=0.0):
    """Modes d'une corde vue **au point d'archet**, en admittance.

    `beta` est la position de l'archet en fraction de la longueur. Elle entre
    en `sin²(nπβ)` : un mode dont l'archet touche un nœud ne peut pas être
    excité. À β = 1/7, le 7ᵉ partiel s'éteint — c'est audible, et c'est
    pourquoi un violoniste qui déplace son archet change la couleur sans
    changer la note.

    `inharmonicity` (B) raidit la corde : `f_n = n·f0·√(1 + B n²)`. Négligeable
    sur un boyau, sensible sur une corde filée grave.

    `q_decay` fait décroître l'acuité des modes aigus, `Q_n = q / n^q_decay`.
    Une vraie corde perd ses aigus plus vite que ses graves — frottement de
    l'air, pertes internes, absorption au chevalet. Le défaut 0 garde un Q
    uniforme, qui est la simplification sous laquelle les résultats du dépôt
    ont été mesurés ; 0,5 à 1 est plus proche du réel, et c'est ce que
    `identify.py` ajuste sur la pente spectrale d'un son mesuré.
    """
    n = np.arange(1, int(n_modes) + 1, dtype='float64')
    freqs = n * float(f0_hz) * np.sqrt(1.0 + float(inharmonicity) * n ** 2)
    shape = np.sin(n * np.pi * float(beta)) ** 2
    omega = 2 * np.pi * freqs
    qs = float(q) / n ** float(q_decay)
    peaks = 4.0 * shape * qs / (float(mass_kg) * omega)
    return [Mode(freq_hz=float(f), q=float(qq), peak=float(p))
            for f, qq, p in zip(freqs, qs, peaks) if p > 0]


def chamber_compliance(volume_m3):
    """Compliance acoustique d'une cavité fermée : `V / (γ·P_atm)`.

    C'est le ressort d'air. Plus la chambre est petite, plus il est raide —
    et sous un certain volume, il devient si raide que l'anche ne démarre
    plus du tout (cf. `docs/experiences_a_mener.md`, E13).
    """
    return float(volume_m3) / (GAMMA * PATM)


# =============================================================================
# Excitateurs
# =============================================================================

class Exciter:
    """Interface commune. Un excitateur est sans mémoire du résonateur.

    `deriv(state, response, level)` renvoie `(dstate, drive)` :

    - `response` est ce que le résonateur présente (pression, ou vitesse) ;
    - `level` est la **commande de jeu** — pression de bouche, débit de
      soufflet, force d'archet. C'est la nuance, la seule chose que le
      musicien pousse vraiment ;
    - `drive` est ce qu'on réinjecte dans le résonateur (débit, ou force).

    Aucune boucle algébrique : la réponse du résonateur ne dépend que de son
    état, jamais de `drive` à l'instant même. L'intégration explicite suffit
    donc, pourvu qu'on suréchantillonne.
    """
    n_state = 0
    #: nom de la grandeur de commande, pour l'affichage
    control_name = "commande"
    control_unit = ""

    def initial_state(self):
        return np.zeros(self.n_state)

    def deriv(self, state, response, level):
        raise NotImplementedError

    def opening(self, state):
        """Ouverture courante (m), ou `nan` si la notion n'a pas de sens."""
        return float('nan')


@dataclass
class SingleReedExciter(Exciter):
    """Anche simple battante : clarinette, saxophone.

    L'anche est une **soupape commandée par la pression qu'elle règle**. Plus
    on souffle fort, plus elle se ferme ; en se fermant, elle coupe le débit,
    la pression tombe, elle se rouvre. C'est cette contre-réaction qui
    entretient l'oscillation — et son signe est l'inverse de celui de l'anche
    libre, qui s'ouvre sous la pression.

    Une prédiction tombe de ces équations sans qu'on la demande : le seuil de
    jeu vaut **le tiers de la pression de placage** (celle qui fermerait
    l'anche en statique). C'est un résultat classique, et un test.

    `beating=True` autorise l'anche à claquer contre la table (`h ≥ 0`), ce
    qui est le régime normal dès le mezzo-forte et la principale source
    d'harmoniques aigus.
    """
    rest_opening_m: float = 4.0e-4        # h₀, ouverture au repos
    width_m: float = 1.3e-2               # largeur du canal
    freq_hz: float = 2500.0               # fréquence propre de l'anche
    q: float = 4.0                        # amortie par la lèvre
    closing_pressure_pa: float = 4000.0   # pression qui ferme l'anche
    beating: bool = True
    vena_contracta: float = 0.6

    n_state = 2
    control_name = "pression de bouche"
    control_unit = "Pa"

    @property
    def omega(self):
        return 2.0 * np.pi * self.freq_hz

    def opening(self, state):
        h = self.rest_opening_m + state[0]
        return max(h, 0.0) if self.beating else h

    def deriv(self, state, response, level):
        y, dy = state[0], state[1]
        dp = level - response                      # bouche − perce
        w = self.omega

        # l'anche cède sous la différence de pression ; `closing_pressure`
        # fixe la raideur en la rapportant à h₀ — un paramètre qui se mesure.
        acc = -w * w * y - (w / max(self.q, 1e-3)) * dy \
            - (w * w * self.rest_opening_m / self.closing_pressure_pa) * dp

        h = self.opening(np.array([y, dy]))
        q = self.vena_contracta * self.width_m * h * \
            np.sign(dp) * np.sqrt(2.0 * abs(dp) / RHO)
        return np.array([dy, acc]), float(q)


@dataclass
class DoubleReedExciter(SingleReedExciter):
    """Anche double : bombarde, chalumeau de cornemuse, hautbois.

    Mêmes équations que l'anche simple — deux lames symétriques se comportent,
    au premier ordre, comme une lame contre une table. Ce qui change est le
    **réglage** : ouverture au repos plus faible, raideur bien plus grande,
    fréquence propre plus haute. D'où le seuil de pression élevé et le timbre
    criard de la bombarde.

    Honnêteté sur ce que ça ne fait pas : une vraie anche double a une
    dynamique de jet confiné dans le canal entre les lames, qui ajoute une
    perte dépendant du débit. Ce n'est pas modélisé ici. Le modèle rend la
    hauteur, le seuil et l'allure du spectre ; il ne rend pas le grain propre
    du hautbois.
    """
    rest_opening_m: float = 1.2e-4
    width_m: float = 6.0e-3
    freq_hz: float = 3200.0
    q: float = 3.0
    closing_pressure_pa: float = 9000.0

    control_name = "pression de bouche"
    control_unit = "Pa"


@dataclass
class FreeReedExciter(Exciter):
    """Anche libre réduite à un mode : accordéon, harmonica, sheng.

    La languette **traverse** la fente au lieu de battre contre elle, et la
    soupape de cuir interdit le retour : c'est l'asymétrie qui fait tout, et
    c'est pourquoi il faut deux anches par note (poussé, tiré).

    Réduction à un degré de liberté de `reed_oscillator.FreeReedModel`, pour
    que l'accordéon passe par le même chemin que le reste. Pour la thèse,
    c'est `FreeReedModel` qui fait foi : base modale complète, seuils par
    valeurs propres du jacobien.
    """
    freq_hz: float = 102.1
    q: float = 125.0
    width_m: float = 4.8e-3
    rest_offset_m: float = 0.10e-3
    max_open_m: float = 0.50e-3
    leak_m: float = 2.0e-6
    area_m2: float = 9.6e-5              # surface balayée par la languette
    force_area_m2: float = 9.6e-5        # surface sur laquelle la pression agit
    mass_kg: float = 2.0e-4
    vena_contracta: float = 0.7
    source_impedance: float = 2.0e8      # impédance interne du soufflet

    n_state = 2
    control_name = "débit de soufflet"
    control_unit = "m³/s"

    @property
    def omega(self):
        return 2.0 * np.pi * self.freq_hz

    def opening(self, state):
        return float(np.clip(state[0] + self.rest_offset_m,
                             self.leak_m, self.max_open_m))

    def deriv(self, state, response, level):
        y, dy = state[0], state[1]
        p = response
        w = self.omega

        acc = -w * w * y - (w / max(self.q, 1e-3)) * dy \
            + p * self.force_area_m2 / self.mass_kg

        h = self.opening(np.array([y, dy]))
        q_out = (self.vena_contracta * self.width_m * h *
                 np.sqrt(2.0 * p / RHO)) if p > 0 else 0.0

        q_src = level
        if np.isfinite(self.source_impedance):
            q_src = level - p / self.source_impedance

        # débit net entrant dans la chambre : source − fuite par la fente
        # − volume balayé par la languette elle-même
        net = q_src - q_out - self.area_m2 * dy
        return np.array([dy, acc]), float(net)


@dataclass
class BowExciter(Exciter):
    """Frottement d'archet : violon, alto, violoncelle, vielle à roue.

    Le collophane colle puis lâche. Le coefficient de frottement s'effondre
    quand la corde glisse vite par rapport à l'archet, et cette pente négative
    est exactement ce qui rend l'oscillation possible — même rôle que
    l'ouverture modulée d'une anche. Il en sort le mouvement de Helmholtz : un
    coin qui court le long de la corde, une dent de scie en vitesse, donc un
    spectre en 1/n.

    Pour la **vielle à roue**, la seule différence est que `bow_speed` est
    constante : la roue tourne, le musicien ne fait que la manivelle. Pas
    d'accentuation par la vitesse d'archet — d'où le recours au chien, et à la
    manivelle elle-même, pour articuler. Un violon, lui, module les deux.

    ⚠️ Modèle à *courbe de frottement* (friction-curve). Il produit Helmholtz
    et les bons ordres de grandeur, mais il ignore l'hystérésis thermique du
    collophane. Les modèles thermiques rendent mieux le grincement et les
    régimes de transition. Ce n'est pas implémenté ici et ne doit pas être
    revendiqué.
    """
    mu_static: float = 0.8
    mu_dynamic: float = 0.3
    v_char: float = 0.05                 # vitesse de transition coller/glisser
    bow_speed: float = 0.2               # m/s (roue, ou archet)

    n_state = 0
    control_name = "force d'archet"
    control_unit = "N"

    def friction(self, v_rel):
        """μ(v_rel) — s'effondre de μ_s vers μ_d quand le glissement augmente."""
        return np.sign(v_rel) * (self.mu_dynamic +
                                 (self.mu_static - self.mu_dynamic) /
                                 (1.0 + abs(v_rel) / self.v_char))

    def deriv(self, state, response, level):
        v_rel = self.bow_speed - response      # archet − corde
        return np.zeros(0), float(level * self.friction(v_rel))


# =============================================================================
# La voix : excitateur + résonateur
# =============================================================================

@dataclass
class VoiceResult:
    """Ce qui sort d'une simulation."""
    t: np.ndarray
    response: np.ndarray        # pression dans la perce, ou vitesse de corde
    drive: np.ndarray           # débit injecté, ou force d'archet
    opening: np.ndarray
    fs: float
    level: float
    final_state: np.ndarray = None

    @property
    def radiated(self):
        """Proxy du rayonnement en champ lointain.

        Pour un instrument à vent, c'est la **dérivée du débit** sortant : un
        tuyau rayonne par ce qu'il expulse, pas par ce qu'il contient. Pour
        une corde, la vitesse au chevalet fait déjà l'affaire — c'est elle que
        le corps transforme en son.
        """
        return np.gradient(self.drive) * self.fs


class HybridVoice:
    """Un excitateur couplé à un résonateur. C'est tout un instrument."""

    def __init__(self, exciter: Exciter, resonator: Resonator, name=""):
        self.exciter = exciter
        self.resonator = resonator
        self.name = name
        self.n_ex = exciter.n_state
        self.n_res = resonator.n_state

    # -- dynamique ------------------------------------------------------------
    def deriv(self, state, level):
        ex_state = state[:self.n_ex]
        res_state = state[self.n_ex:]
        response = self.resonator.response(res_state)
        d_ex, drive = self.exciter.deriv(ex_state, response, level)
        d_res = self.resonator.deriv(res_state, drive)
        return np.concatenate([d_ex, d_res]), drive, response

    def _rk4(self, state, level, dt):
        def f(s):
            return self.deriv(s, level)[0]
        k1 = f(state)
        k2 = f(state + 0.5 * dt * k1)
        k3 = f(state + 0.5 * dt * k2)
        k4 = f(state + dt * k3)
        return state + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)

    def simulate(self, dur=1.0, fs=44100.0, level=1.0, oversample=8,
                 state0=None, settle=0.0):
        """Fait sonner la voix. `level` est la commande de jeu.

        `oversample` intègre plus fin que la sortie : les non-linéarités
        (anche qui claque, archet qui décroche) sont raides, et
        sous-échantillonner les rate silencieusement — on obtient un son, mais
        pas le bon. `settle` coupe le début, le temps que le cycle limite
        s'installe.
        """
        n_out = int(dur * fs)
        n_settle = int(settle * fs)
        total = n_out + n_settle
        dt = 1.0 / (fs * int(oversample))

        state = np.zeros(self.n_ex + self.n_res) if state0 is None \
            else np.array(state0, dtype='float64')
        if state0 is None and self.n_ex:
            state[1] = 1e-4          # pichenette : sans elle, l'équilibre tient

        resp = np.zeros(total)
        drv = np.zeros(total)
        opn = np.zeros(total)

        for i in range(total):
            for _ in range(int(oversample)):
                state = self._rk4(state, level, dt)
            _, d, r = self.deriv(state, level)
            resp[i], drv[i] = r, d
            opn[i] = self.exciter.opening(state[:self.n_ex])

        sl = slice(n_settle, None)
        return VoiceResult(t=np.arange(n_out) / fs, response=resp[sl],
                           drive=drv[sl], opening=opn[sl], fs=float(fs),
                           level=float(level), final_state=state)

    # -- seuil ----------------------------------------------------------------
    def oscillates(self, level, dur=0.35, fs=22050.0, oversample=8,
                   rel_tol=1e-3):
        """Dit si la voix s'auto-entretient à cette commande.

        On regarde le dernier tiers : un transitoire qui décroît n'est pas une
        oscillation, et c'est l'erreur que j'ai faite une fois en prenant le
        signal entier.
        """
        res = self.simulate(dur, fs=fs, level=level, oversample=oversample)
        n = res.response.size
        if n < 30:
            return False
        tail = res.response[2 * n // 3:]
        ref = np.max(np.abs(res.response)) + 1e-30
        return bool(np.ptp(tail) > rel_tol * ref and np.ptp(tail) > 1e-12)

    def threshold(self, lo, hi, n_iter=18, **kw):
        """Plus petite commande qui fait parler l'instrument, par dichotomie.

        Renvoie `(seuil, fréquence_de_jeu)`, ou `None` si `hi` ne suffit pas —
        ce qui est une information, pas un échec : une chambre trop petite ou
        un archet trop léger ne produisent rien, et il vaut mieux le dire.
        """
        if not self.oscillates(hi, **kw):
            return None
        if self.oscillates(lo, **kw):
            hi = lo                       # déjà au-dessus : on ne sait pas mieux
        else:
            for _ in range(int(n_iter)):
                mid = 0.5 * (lo + hi)
                if self.oscillates(mid, **kw):
                    hi = mid
                else:
                    lo = mid
        res = self.simulate(0.6, fs=22050.0, level=hi * 1.05, oversample=8,
                            settle=0.25)
        return float(hi), playing_frequency(res.response, res.fs)

    def __repr__(self):
        return (f"<HybridVoice {self.name or '?'} "
                f"{type(self.exciter).__name__} + {self.resonator!r}>")


def playing_frequency(signal, fs, fmin=40.0, fmax=4000.0):
    """Fréquence de jeu, par autocorrélation.

    Volontairement pas par `argmax` du spectre : sur une dent de scie ou un
    signal dérivé, le partiel le plus fort n'est pas le fondamental, et
    `argmax` renvoie alors une harmonique avec un aplomb trompeur.

    Deux pièges de l'autocorrélation, tombés dans les deux :

    1. **Le lobe principal.** Près du retard zéro, l'autocorrélation vaut
       encore presque 1 — elle n'a pas fini de décroître. Un `argmax` brut sur
       la fenêtre de retards y trouve son maximum et renvoie n'importe quoi.
       On saute donc le lobe en attendant la première descente sous zéro.
    2. **L'interpolation parabolique.** Elle n'a de sens qu'à un vrai sommet
       (`den < 0`) et ne peut déplacer le pic que d'un demi-échantillon. Sans
       ces deux bornes, elle projette `k` hors de la fenêtre.
    """
    x = np.asarray(signal, dtype='float64')
    x = x - x.mean()
    if x.size < 64 or not np.any(x):
        return float('nan')
    ac = np.correlate(x, x, mode='full')[x.size - 1:]
    if ac[0] <= 0:
        return float('nan')
    ac = ac / ac[0]

    lo = max(int(fs / fmax), 1)
    hi = min(int(fs / fmin), ac.size - 1)
    if hi <= lo + 1:
        return float('nan')

    # sortir du lobe principal avant de chercher quoi que ce soit
    below = np.nonzero(ac[:hi] < 0.0)[0]
    lo = max(lo, int(below[0])) if below.size else lo
    if hi <= lo + 1:
        return float('nan')

    seg = ac[lo:hi]
    best = float(seg.max())
    if best <= 0:
        return float('nan')

    # Choisir le **plus petit** retard qui corrèle presque aussi bien que le
    # meilleur, et non le meilleur. Un signal périodique corrèle tout aussi
    # bien à 2 ou 3 périodes qu'à une seule : prendre l'argmax fait tomber
    # l'octave au hasard du bruit. Mesuré sur le violon : ac = 0,8800 à trois
    # périodes contre 0,8781 à une seule — 0,2 % d'écart décidait d'un facteur
    # 3 sur la note annoncée.
    ok = np.nonzero(seg >= 0.92 * best)[0]
    k = int(ok[0]) + lo if ok.size else int(np.argmax(seg)) + lo
    # remonter au sommet local, l'entrée dans la zone n'en est que le flanc
    while k + 1 < hi and ac[k + 1] > ac[k]:
        k += 1

    if 0 < k < ac.size - 1:
        a, b, c = ac[k - 1], ac[k], ac[k + 1]
        den = a - 2 * b + c
        if den < 0:                       # un sommet, pas une pente
            k = k + float(np.clip(0.5 * (a - c) / den, -0.5, 0.5))
    return float(fs / k) if k > 0 else float('nan')


# =============================================================================
# Préréglages — un point de départ par instrument
# =============================================================================

def _wind(exciter, f0, kind, n_modes, q, bore_mm, peak_ratio, name):
    """Assemble une voix à vent. `bore_mm` = diamètre de perce côté anche."""
    z_peak = peak_ratio * z_char(bore_mm * 1e-3)
    res = Resonator(bore_modes(f0, n_modes, kind, q, z_peak), name=name)
    return HybridVoice(exciter, res, name=name)


def accordeon(f0_hz=110.0, volume_m3=40e-6, **kw):
    """Anche libre sur chambre fermée.

    Le seul de la famille dont le résonateur n'a **aucun mode** : juste une
    compliance. C'est pourquoi l'anche impose sa hauteur au lieu de la
    recevoir d'un tuyau — et pourquoi `f0_hz` règle ici la languette
    elle-même, pas une longueur de perce.
    """
    ex = FreeReedExciter(freq_hz=f0_hz, **kw)
    res = Resonator(compliance=chamber_compliance(volume_m3), name="chambre")
    return HybridVoice(ex, res, name="accordéon")


def clarinette(f0_hz=147.0, n_modes=10, q=40.0, bore_mm=14.6, peak_ratio=20.0,
               **kw):
    """Perce cylindrique : harmoniques impairs, registre à la douzième.

    Le son « creux » de la clarinette n'est pas une métaphore : le modèle
    sort environ 37 dB d'écart entre rangs impairs et pairs. C'est la perce
    qui le décide, pas l'anche.
    """
    return _wind(SingleReedExciter(**kw), f0_hz, 'cylindrique', n_modes, q,
                 bore_mm, peak_ratio, "clarinette")


def saxophone(f0_hz=233.0, n_modes=12, q=30.0, bore_mm=10.0, peak_ratio=20.0,
              **kw):
    """Perce conique : série harmonique complète, registre à l'octave.

    Même anche simple que la clarinette, même excitateur — seule la perce
    change, et tout le timbre avec elle.
    """
    kw.setdefault('rest_opening_m', 5.0e-4)
    kw.setdefault('closing_pressure_pa', 3000.0)
    kw.setdefault('freq_hz', 2000.0)
    return _wind(SingleReedExciter(**kw), f0_hz, 'conique', n_modes, q,
                 bore_mm, peak_ratio, "saxophone")


def bombarde(f0_hz=294.0, n_modes=12, q=28.0, bore_mm=5.0, peak_ratio=20.0,
             **kw):
    """Anche double, perce conique étroite : la voix qui porte au fest-noz.

    L'impédance de perce y est huit fois celle d'une clarinette, ce qui
    demande une anche minuscule et raide et une pression de souffle que le
    modèle chiffre en milliers de pascals. Rien d'étonnant à ce qu'on joue par
    couple avec le biniou et qu'on se relaie.
    """
    return _wind(DoubleReedExciter(**kw), f0_hz, 'conique', n_modes, q,
                 bore_mm, peak_ratio, "bombarde")


def cornemuse(f0_hz=233.0, n_modes=12, q=30.0, bore_mm=4.0, peak_ratio=20.0,
              **kw):
    """Chalumeau de cornemuse : anche double alimentée par le **sac**.

    Le sac est un réservoir : la pression y est lissée, et le musicien ne peut
    pas l'articuler. Pas d'attaque, pas de nuance — d'où l'ornementation par
    notes de passage, qui est une réponse à cette contrainte physique et non
    un maniérisme de style.
    """
    return _wind(DoubleReedExciter(**kw), f0_hz, 'conique', n_modes, q,
                 bore_mm, peak_ratio, "cornemuse")


def violon(f0_hz=440.0, n_modes=16, beta=1.0 / 7.0, mass_kg=3.5e-4, q=500.0,
           **kw):
    """Corde frottée à archet — vitesse et force toutes deux modulables."""
    ex = BowExciter(**kw)
    res = Resonator(string_modes(f0_hz, n_modes, beta, mass_kg, q), name="corde")
    return HybridVoice(ex, res, name="violon")


def vielle_a_roue(f0_hz=196.0, n_modes=16, beta=1.0 / 9.0, mass_kg=6.0e-4,
                  q=400.0, wheel_speed=0.35, **kw):
    """Vielle à roue : la roue est un archet qui ne s'arrête jamais.

    Vitesse constante, donc pas d'accent par le geste d'archet — l'articulation
    passe par le chien et par les à-coups de manivelle. Point d'appui plus
    proche du chevalet qu'au violon, d'où un timbre plus riche en aigus.
    """
    kw.setdefault('bow_speed', wheel_speed)
    ex = BowExciter(**kw)
    res = Resonator(string_modes(f0_hz, n_modes, beta, mass_kg, q), name="corde")
    return HybridVoice(ex, res, name="vielle à roue")


#: Tous les instruments connus, par nom. `identify.py` s'en sert pour choisir
#: la famille d'excitateur à partir d'un simple nom d'instrument.
INSTRUMENTS = {
    'accordeon': accordeon,
    'clarinette': clarinette,
    'saxophone': saxophone,
    'bombarde': bombarde,
    'cornemuse': cornemuse,
    'violon': violon,
    'vielle': vielle_a_roue,
}

#: Familles physiques, pour savoir quoi mesurer et quoi ajuster.
FAMILIES = {
    'accordeon': 'anche_libre',
    'clarinette': 'anche_simple',
    'saxophone': 'anche_simple',
    'bombarde': 'anche_double',
    'cornemuse': 'anche_double',
    'violon': 'archet',
    'vielle': 'archet',
}


def build(instrument, f0_hz=None, **kw):
    """Construit une voix par son nom. `build('violon', 440)`."""
    key = str(instrument).strip().lower()
    if key not in INSTRUMENTS:
        raise ValueError(
            f"instrument inconnu : {instrument!r}. "
            f"Connus : {', '.join(sorted(INSTRUMENTS))}")
    return INSTRUMENTS[key](**({'f0_hz': f0_hz} if f0_hz else {}), **kw)

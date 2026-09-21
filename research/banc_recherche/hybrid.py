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
               cutoff_hz=None, cutoff_order=3.0, stretch=0.0, prune_db=45.0):
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

    Pertes visco-thermiques
    -----------------------
    L'air qui frotte contre la paroi perd de l'énergie dans une couche limite
    d'épaisseur `∝ 1/√f`. Il en découle, sans paramètre libre :

        Q_n = q·√(f_n/f_0)        et        Z_n = z_peak/√(f_n/f_0)

    Les résonances aiguës sont donc **plus sélectives** et un peu plus
    faibles, mais bien moins faibles que ce qu'une décroissance en `1/rang`
    laissait croire : au rang 9 d'une clarinette, l'écart est de +4,4 dB.

    La coupure de réseau de trous
    -----------------------------
    Ce n'est donc pas la viscosité qui éteint les aigus d'un instrument à
    vent, et c'est là que le modèle précédent se trompait de mécanisme. Le
    vrai responsable est le **réseau de trous latéraux** : en dessous de sa
    fréquence de coupure il réfléchit l'onde et fabrique des résonances,
    au-dessus il devient transparent et l'énergie s'échappe (Benade).

    C'est une grandeur physique, propre à l'instrument et mesurable :

    | instrument            | `cutoff_hz` |
    |-----------------------|-------------|
    | basson                | ~450        |
    | saxophone alto        | ~700        |
    | hautbois, cornemuse   | ~1100       |
    | clarinette            | ~1500       |

    Elle explique d'un coup pourquoi un saxophone sonne plus sombre qu'une
    clarinette dans l'aigu, et pourquoi le pavillon change le timbre sans
    changer la note. `cutoff_hz=None` la désactive.

    `stretch` écarte les résonances aiguës de la série exacte :
    `f_n = f_0·r·(1 + stretch·(r−1))`. Une perce réelle n'est jamais
    exactement harmonique — le volume du bec et celui de l'anche déplacent
    les résonances hautes, et c'est pourquoi un clarinettiste doit « placer »
    sa douzième. Défaut 0, à mesurer (E14).

    `prune_db` écarte les modes plus de tant de dB sous le plus fort. Un mode
    négligeable coûte un biquad sur la carte sans rien apporter au son.
    """
    n = np.arange(1, int(n_modes) + 1)
    if kind == 'cylindrique':
        ratios = (2 * n - 1).astype('float64')
    elif kind == 'conique':
        ratios = n.astype('float64')
    else:
        raise ValueError("kind doit valoir 'cylindrique' ou 'conique'")

    ratios = ratios * (1.0 + float(stretch) * (ratios - 1.0))
    freqs = float(f0_hz) * ratios

    racine = np.sqrt(ratios)
    qs = float(q) * racine                     # visco-thermique : Q ∝ √f
    pics = float(z_peak) / racine              # visco-thermique : Z ∝ 1/√f

    if cutoff_hz:
        # au-dessus de la coupure le réseau laisse fuir : le sommet s'effondre
        # et la résonance s'élargit, les deux pour la même raison.
        transp = 1.0 / (1.0 + (freqs / float(cutoff_hz)) ** float(cutoff_order))
        pics = pics * transp
        qs = np.maximum(qs * transp, 1.0)

    garde = pics >= pics.max() * 10 ** (-abs(float(prune_db)) / 20.0)
    return [Mode(freq_hz=float(f), q=float(qq), peak=float(pk))
            for f, qq, pk, ok in zip(freqs, qs, pics, garde) if ok]


def modes_from_partials(freqs_hz, q=35.0, z_peak=2.0e7, cutoff_hz=None,
                        cutoff_order=3.0, prune_db=45.0, peaks=None, qs=None):
    """Résonateur bâti sur des fréquences de résonance **réelles**.

    `bore_modes` fabrique une série idéale — harmonique ou impaire. Aucune
    perce ne fait ça. Les résonances d'un tuyau réel s'écartent de la série
    exacte à cause de la perce elle-même, du bec, des trous ouverts et du
    pavillon, et c'est cet écart qui décide si l'instrument est **juste** d'un
    registre à l'autre. Un facteur passe sa vie dessus.

    Cette fonction prend donc la liste telle qu'elle sort d'un calcul de perce
    (Tutti) ou d'une mesure d'impédance (`transfer.py`), et n'invente rien.

    Ce qui reste calculé plutôt que fourni, faute de mieux : `Q` et le sommet
    de chaque résonance, par les lois visco-thermiques `Q ∝ √f`, `Z ∝ 1/√f`
    rapportées à la plus grave. Passer `qs` et `peaks` si on les a — auquel cas
    plus rien n'est supposé.
    """
    f = np.asarray(freqs_hz, dtype='float64').ravel()
    f = np.sort(f[np.isfinite(f) & (f > 0)])
    if f.size == 0:
        raise ValueError("aucune fréquence de résonance exploitable")

    ratios = f / f[0]
    racine = np.sqrt(ratios)
    qq = np.asarray(qs, dtype='float64') if qs is not None else float(q) * racine
    pk = np.asarray(peaks, dtype='float64') if peaks is not None else float(z_peak) / racine
    qq = np.broadcast_to(qq, f.shape).astype('float64').copy()
    pk = np.broadcast_to(pk, f.shape).astype('float64').copy()

    if cutoff_hz:
        transp = 1.0 / (1.0 + (f / float(cutoff_hz)) ** float(cutoff_order))
        pk *= transp
        qq = np.maximum(qq * transp, 1.0)

    garde = pk >= pk.max() * 10 ** (-abs(float(prune_db)) / 20.0)
    return [Mode(float(a), float(b), float(c))
            for a, b, c, ok in zip(f, qq, pk, garde) if ok]


def modes_from_cents(f0_hz, cents, kind='conique', **kw):
    """Série idéale **corrigée note à note** par un écart en cents.

    C'est la forme sous laquelle un calcul de perce rend naturellement sa
    justesse : « la douzième est 12 cents trop basse ». `cents[i]` s'applique
    au i-ème mode de la série choisie.

        modes_from_cents(147.0, [0, -12, +7, +3], kind='cylindrique')

    Un écart en cents est un rapport de fréquences, pas une différence : on
    multiplie par `2^(c/1200)`, on n'ajoute pas.
    """
    c = np.asarray(cents, dtype='float64').ravel()
    n = np.arange(1, c.size + 1, dtype='float64')
    if kind == 'cylindrique':
        ratios = 2 * n - 1
    elif kind == 'conique':
        ratios = n
    else:
        raise ValueError("kind doit valoir 'cylindrique' ou 'conique'")
    return modes_from_partials(float(f0_hz) * ratios * 2.0 ** (c / 1200.0), **kw)


def inharmonicity_cents(modes, kind=None):
    """Écart de chaque résonance à la série idéale, en cents.

    L'inverse de `modes_from_cents` : ce que le modèle **a**, dit dans l'unité
    où on juge la justesse. `kind=None` devine la série d'après le rapport de
    la deuxième résonance à la première (≈2 → conique, ≈3 → cylindrique).

    Sert à confronter un jeu de modes mesuré au calcul de perce, et à vérifier
    qu'on n'a pas perdu la justesse en route.
    """
    f = np.array([m.freq_hz for m in modes], dtype='float64')
    if f.size == 0:
        return np.zeros(0)
    if kind is None:
        kind = 'cylindrique' if (f.size > 1 and f[1] / f[0] > 2.4) else 'conique'
    n = np.arange(1, f.size + 1, dtype='float64')
    ideal = f[0] * ((2 * n - 1) if kind == 'cylindrique' else n)
    return 1200.0 * np.log2(f / ideal)


def register_vent(modes, kill=1, strength=0.02):
    """Étouffe les `kill` premières résonances — c'est ce que fait une clé de
    registre, et rien d'autre.

    Le trou de registre s'ouvre près d'un nœud de pression de la résonance
    qu'on veut garder, et près d'un ventre de celle qu'on veut tuer : la
    première cesse de réfléchir, l'oscillation se rabat sur la suivante
    disponible.

    Le modèle en tire la hauteur du registre **sans qu'on la lui donne**, et
    c'est une des plus jolies vérifications du cadre :

    | perce        | résonances       | registre obtenu |
    |--------------|------------------|-----------------|
    | cylindrique  | f0, 3f0, 5f0…    | **×3,00** — la douzième |
    | conique      | f0, 2f0, 3f0…    | **×2,00** — l'octave |

    C'est précisément ce qui distingue le doigté d'une clarinette de celui
    d'un saxophone, et le modèle le retrouve à la troisième décimale.

    `strength` est ce qu'il reste du sommet étouffé (0,02 = −34 dB).
    """
    out = []
    for i, m in enumerate(modes):
        if i < int(kill):
            out.append(Mode(m.freq_hz, max(m.q * 0.1, 1.0), m.peak * float(strength)))
        else:
            out.append(Mode(m.freq_hz, m.q, m.peak))
    return out


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

def _wind(exciter, f0, kind, n_modes, q, bore_mm, peak_ratio, name,
          cutoff_hz=None, stretch=0.0, register=0, bell_mm=None,
          engine='ideal'):
    """Assemble une voix à vent. `bore_mm` = diamètre de perce côté anche.

    `register=0` joue le registre grave ; `1` ouvre la clé de registre et
    laisse le modèle trouver lui-même la douzième ou l'octave selon la perce.

    Deux moteurs pour le résonateur
    --------------------------------
    `engine='ideal'` — `bore_modes` : une série harmonique ou impaire exacte,
    postulée. Rapide, et c'est elle qui a servi à tous les résultats déjà
    validés du dépôt (registre ×2/×3, écart impairs/pairs...).

    `engine='tutt'` — la même physique que le pont TUTT (matrices de
    transfert, pertes de Kirchhoff/Mason, impédance de rayonnement) sur une
    perce à **un seul tronçon** qui vise `f0`. TUTT est la référence pour la
    justesse et l'inharmonicité d'une **vraie** perce — mais une perce à un
    tronçon tronqué **n'est pas** une vraie perce, et l'essai a mal tourné :
    le cône idéalisé ne redonne pas le registre à l'octave, ses résonances
    suivent `tan(kL)=kL` au lieu de la série harmonique attendue, avec des
    écarts de plusieurs centaines de cents. Le cylindre, lui, n'a aucune
    ambiguïté de troncature et marche très bien par cette voie (`clarinette`
    l'utilise par défaut). Détail de ce qui a été essayé et pourquoi ça ne
    suffit pas encore : `docs/modele_hybride_generalise.md`, §9.

    Tant que ce point n'est pas résolu, `engine='tutt'` sur une perce
    **conique** n'est donc **pas** le défaut ici — pour une vraie perce
    conique (fichier TUTT réel), c'est `tutt.resonator_from_dat` directement
    qu'il faut appeler : lui est validé, à 1,5 cent près, sur la bombarde
    d'Ewen.
    """
    if engine == 'tutt':
        from . import tutt
        res, _infos = tutt.ideal_resonator(kind, f0, bore_mm, n_modes=n_modes,
                                           bell_mm=bell_mm, cutoff_hz=cutoff_hz)
        modes = res.modes
    elif engine == 'ideal':
        z_peak = peak_ratio * z_char(bore_mm * 1e-3)
        modes = bore_modes(f0, n_modes, kind, q, z_peak,
                           cutoff_hz=cutoff_hz, stretch=stretch)
    else:
        raise ValueError("engine doit valoir 'tutt' ou 'ideal'")
    if register:
        modes = register_vent(modes, kill=int(register))
    res = Resonator(modes, name=name)
    return HybridVoice(exciter, res, name=name)


ACCORDEON_REF_HZ = 110.0     # l'anche dont les cotes servent de référence


def accordeon(f0_hz=110.0, volume_m3=None, **kw):
    """Anche libre sur chambre fermée.

    Le seul de la famille dont le résonateur n'a **aucun mode** : juste une
    compliance. C'est pourquoi l'anche impose sa hauteur au lieu de la
    recevoir d'un tuyau — et pourquoi `f0_hz` règle ici la languette
    elle-même, pas une longueur de perce.

    **Les cotes suivent la note.** Garder la languette du la grave pour jouer
    dans l'aigu ne donne pas un son aigu : ça ne donne aucun son. Essayé —
    au-dessus de 185 Hz l'anche se contente de se coucher dans le courant
    d'air sans jamais osciller. Le facteur d'accordéon ne fait d'ailleurs pas
    autrement : il a une languette **par note**.

    On applique une similitude géométrique, la plus simple des lois et celle
    qu'approchent les jeux d'anches réels à l'intérieur d'un registre : la
    languette aiguë est une copie réduite de la grave, toutes ses dimensions
    divisées par le même nombre.

        L ∝ 1/f,  largeur ∝ 1/f,  épaisseur ∝ 1/f

    ce qui redonne bien la fréquence d'une poutre encastrée, `f ∝ e/L²`, et
    donne une masse en `1/f³`.

    Le volume de la chambre suit en `1/f³` lui aussi — et là, ce n'est pas un
    choix mais une conséquence. Pour que le couplage anche↔chambre garde la
    même force d'une note à l'autre, il faut `A²/(C·m·ω²)` constant ; en y
    portant les lois ci-dessus, l'exposant de la géométrie s'élimine et il ne
    reste que `V ∝ f⁻³`. Ça tombe juste : 40 cm³ pour le la grave, un dixième
    de centimètre cube dans l'aigu — l'ordre de grandeur des cellules d'un
    sommier d'accordéon.

    Une seule cote ne suit pas : la **fuite résiduelle** entre la languette
    et son cadre. Ce n'est pas une dimension du dessin, c'est une tolérance
    d'atelier — elle ne rétrécit pas parce que la note monte.

    Toute cote passée explicitement l'emporte sur la loi d'échelle : c'est ce
    qui permet de confronter le modèle à une anche réelle mesurée au banc.
    """
    r = float(f0_hz) / ACCORDEON_REF_HZ
    ref = FreeReedExciter()
    echelle = {
        'width_m': ref.width_m / r,
        'rest_offset_m': ref.rest_offset_m / r,
        'max_open_m': ref.max_open_m / r,
        'area_m2': ref.area_m2 / r ** 2,
        'force_area_m2': ref.force_area_m2 / r ** 2,
        'mass_kg': ref.mass_kg / r ** 3,
    }
    for cle, valeur in echelle.items():
        kw.setdefault(cle, valeur)
    if volume_m3 is None:
        volume_m3 = 40e-6 / r ** 3

    ex = FreeReedExciter(freq_hz=f0_hz, **kw)
    res = Resonator(compliance=chamber_compliance(volume_m3), name="chambre")
    return HybridVoice(ex, res, name="accordéon")


def clarinette(f0_hz=147.0, n_modes=10, q=40.0, bore_mm=14.6, peak_ratio=20.0,
               cutoff_hz=1500.0, register=0, engine='tutt', **kw):
    """Perce cylindrique : harmoniques impairs, registre à la douzième.

    Le son « creux » de la clarinette n'est pas une métaphore : le modèle
    sort environ 37 dB d'écart entre rangs impairs et pairs. C'est la perce
    qui le décide, pas l'anche.

    Seul des quatre vents à passer par `engine='tutt'` par défaut : un
    cylindre n'a pas de troncature de cône à trancher (cf. `_wind`), et le
    calcul redonne la série impaire exacte à la stretch de couche limite
    près — perte et légère dispersion des harmoniques aigus comprises,
    plutôt que postulées par `stretch=`.
    """
    return _wind(SingleReedExciter(**kw), f0_hz, 'cylindrique', n_modes, q,
                 bore_mm, peak_ratio, "clarinette", cutoff_hz,
                 register=register, engine=engine)


def saxophone(f0_hz=233.0, n_modes=12, q=30.0, bore_mm=10.0, bell_mm=None,
             peak_ratio=20.0, cutoff_hz=700.0, register=0, engine='ideal',
             **kw):
    """Perce conique : série harmonique complète, registre à l'octave.

    Même anche simple que la clarinette, même excitateur — seule la perce
    change, et tout le timbre avec elle.
    """
    kw.setdefault('rest_opening_m', 5.0e-4)
    kw.setdefault('closing_pressure_pa', 3000.0)
    kw.setdefault('freq_hz', 2000.0)
    return _wind(SingleReedExciter(**kw), f0_hz, 'conique', n_modes, q,
                 bore_mm, peak_ratio, "saxophone", cutoff_hz,
                 register=register, bell_mm=bell_mm, engine=engine)


def bombarde(f0_hz=294.0, n_modes=12, q=28.0, bore_mm=5.0, bell_mm=None,
            peak_ratio=20.0, cutoff_hz=1100.0, register=0, engine='ideal',
            **kw):
    """Anche double, perce conique étroite : la voix qui porte au fest-noz.

    L'impédance de perce y est huit fois celle d'une clarinette, ce qui
    demande une anche minuscule et raide et une pression de souffle que le
    modèle chiffre en milliers de pascals. Rien d'étonnant à ce qu'on joue par
    couple avec le biniou et qu'on se relaie.
    """
    return _wind(DoubleReedExciter(**kw), f0_hz, 'conique', n_modes, q,
                 bore_mm, peak_ratio, "bombarde", cutoff_hz,
                 register=register, bell_mm=bell_mm, engine=engine)


def cornemuse(f0_hz=233.0, n_modes=12, q=30.0, bore_mm=4.0, bell_mm=None,
             peak_ratio=20.0, cutoff_hz=1100.0, register=0, engine='ideal',
             **kw):
    """Chalumeau de cornemuse : anche double alimentée par le **sac**.

    Le sac est un réservoir : la pression y est lissée, et le musicien ne peut
    pas l'articuler. Pas d'attaque, pas de nuance — d'où l'ornementation par
    notes de passage, qui est une réponse à cette contrainte physique et non
    un maniérisme de style.
    """
    return _wind(DoubleReedExciter(**kw), f0_hz, 'conique', n_modes, q,
                 bore_mm, peak_ratio, "cornemuse", cutoff_hz,
                 register=register, bell_mm=bell_mm, engine=engine)


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

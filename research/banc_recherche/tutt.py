"""Pont vers TUTT — des vraies perces au modèle physique.

TUTT est le logiciel de B.B. Ninob (http://la.trompette.online.fr/Ninob/) :
à partir des longueurs et diamètres des tronçons d'un instrument à vent, il
calcule la hauteur de chaque doigté et simule l'effet d'une modification.
Cuivres et bois. Il est accompagné d'une bibliothèque de perces réelles —
Stanesby, Martinlot, Van Eyck, Kynsecker, traversos, chalumeaux.

Pourquoi ce module existe
-------------------------
`hybrid.bore_modes` fabrique une série **idéale** : harmonique pour un cône,
impaire pour un cylindre. Aucune perce ne fait ça. La perce elle-même, le bec,
les trous ouverts et le pavillon écartent les résonances de la série exacte,
et **c'est cet écart qui décide de la justesse** d'un registre à l'autre.

Le modèle y est maximalement sensible : mesuré sur une clarinette, désaccorder
la deuxième résonance de 40 cents déplace la note du registre de 40,2 cents.
Sans les vraies résonances, tout ce qui touche à la justesse inter-registre
est donc faux — d'où ce module.

Ce qu'il lit
-----------
- **`.dat`** — le fichier d'entrée de TUTT : géométrie des tronçons, trous
  latéraux, embouchure (dont les volumes `V0`/`V1` et la masse et la raideur
  de l'anche), table des doigtés ;
- **`.out`** — ce que TUTT calcule : par doigté, la pulsation visée `OREF`,
  la pulsation obtenue `OTUBE`, l'écart en `CENTS` et le facteur `Q`.

Ce qu'il calcule lui-même
-------------------------
L'impédance d'entrée d'une suite de tronçons coniques ou cylindriques, par
matrices de transfert, avec pertes visco-thermiques. Les sommets de cette
impédance sont les résonances réelles de la perce : c'est ce qui alimente
`hybrid.modes_from_partials`.

Les **trous latéraux** y sont, depuis que `Ltran9.for` a montré comment TUTT
les pose : chaque cheminée est un tuyau de plus, branché en dérivation, avec
sa géométrie, sa constante de propagation et son impédance de bout. Un doigté
se donne par son nom (`'fa'`) ou par son tableau de 0/1 — `1` = fermé, comme
le `CP` de TUTT.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

import numpy as np

RHO = 1.2040          # valeurs par défaut de TUTT
CELERITE = 343.0
GAMMA = 1.400
P0 = 1.014e5
ETA = 1.8e-5          # viscosité dynamique de l'air (Pa·s)
PRANDTL = 0.71


# =============================================================================
# Lecture des fichiers TUTT
# =============================================================================

@dataclass
class BoreDat:
    """Géométrie et embouchure, telles que TUTT les reçoit."""
    title: str = ""
    n_sections: int = 0
    closed_bottom: bool = False
    d0: np.ndarray = field(default_factory=lambda: np.zeros(0))   # Ø amont (m)
    dl: np.ndarray = field(default_factory=lambda: np.zeros(0))   # Ø aval (m)
    lengths: np.ndarray = field(default_factory=lambda: np.zeros(0))
    hole_d0: np.ndarray = field(default_factory=lambda: np.zeros(0))
    hole_dl: np.ndarray = field(default_factory=lambda: np.zeros(0))
    hole_len: np.ndarray = field(default_factory=lambda: np.zeros(0))
    ofilib: np.ndarray = field(default_factory=lambda: np.zeros(0))
    istyle: np.ndarray = field(default_factory=lambda: np.zeros(0))
    levee: np.ndarray = field(default_factory=lambda: np.zeros(0))
    temperature_c: tuple = (20.0, 20.0)   # (embouchure, pavillon), comme TUTT
    a4_hz: float = 440.0
    embouchure: dict = field(default_factory=dict)
    fingerings: list = field(default_factory=list)   # [(nom, [0/1, ...]), ...]

    @property
    def total_length_m(self):
        return float(np.sum(self.lengths))

    @property
    def solid_reed(self):
        """`True` si l'excitateur est une **anche solide** (roseau, métal).

        Le source de TUTT tranche : `IF(IFLUTE.EQ.1) GO TO 2` puis
        `IF(IFLUTE.EQ.2) GO TO 2`, et l'étiquette 2 porte le commentaire
        « ON A AFFAIRE A UNE ANCHE SOLIDE ». Donc `IFLUTE ∈ {1, 2}` désigne
        une anche solide, et **toute autre valeur une anche aérienne** — un
        jet de flûte.

        Le nom du champ dit donc l'inverse de ce qu'il vaut, et je m'y étais
        laissé prendre : ma première version appelait « flûte » exactement ce
        qui est une anche.
        """
        return int(self.embouchure.get('IFLUTE', 0)) in (1, 2)

    @property
    def air_reed(self):
        """`True` pour une anche **aérienne** : flûte à bec, traversière."""
        return not self.solid_reed

    @property
    def jet_velocity_ms(self):
        """`(V0, V1)` — **vitesses de jet**, en m/s. Pas des volumes.

        Piège dans lequel je suis tombé : j'avais lu `V0` comme un volume de
        cavité d'anche, en cm³. Le source dit `V EST LA VITESSE DU JET`, et
        `V = V0 + V1·(ω/ωc − 1)` avec `ωc = α·V0/LA`. Les 26 du fichier de
        flûte à bec sont donc 26 **m/s**, ce qui est une vitesse de souffle
        tout à fait ordinaire — et non 26 cm³.

        Ces deux paramètres ne servent qu'aux anches aériennes ; pour une
        anche solide, TUTT saute le calcul et prend `MREED`/`KREED`. C'est
        pourquoi les fichiers d'anche portent `V0 = 1.e10` : la valeur n'est
        jamais lue.
        """
        return (float(self.embouchure.get('V0', 0.0) or 0.0),
                float(self.embouchure.get('V1', 0.0) or 0.0))

    @property
    def reed_oscillator(self):
        """`(masse, raideur)` de l'anche solide — `MREED`, `KREED`.

        C'est ainsi que TUTT pose l'anche : un oscillateur masse-ressort
        couplé au tube, et non une cavité. La « cavité équivalente » de
        l'article *Modes propres d'un tronc de cône* est un résultat
        analytique séparé, pas la façon dont le logiciel calcule.
        """
        return (float(self.embouchure.get('MREED', 0.0) or 0.0),
                float(self.embouchure.get('KREED', 0.0) or 0.0))

    @property
    def roughness(self):
        """`OFILIB` — rapport périmètre réel / périmètre géométrique.

        Le commentaire du source est sans ambiguïté : « TABLEAU PERIMETRE
        MICROSCOPIQUE DE LA PERCE / PERIMETRE OFFICIEL », et le calcul fait
        `PERI = π·OFILIB(I)·DM`. C'est donc la **rugosité** : une perce en
        bois poreux ou corrodée offre plus de paroi mouillée qu'un tube lisse
        de même section, donc plus de pertes de couche limite.

        Conséquence rassurante : `OFILIB` n'entre **que** dans les pertes. Un
        1,5 sur une bombarde ne décale pas ses résonances de 50 %, il abaisse
        son Q d'autant. Ninob y a consacré un article entier (*Dissipation
        viscothermique… influence de la rugosité de la paroi*), qui montre que
        la corrosion interne dégrade l'instrument avec le temps.
        """
        return self.ofilib if self.ofilib.size else np.ones(len(self.lengths))

    def __repr__(self):
        return (f"<BoreDat {self.title[:40]!r} {len(self.lengths)} tronçons, "
                f"{self.total_length_m * 1e3:.0f} mm, "
                f"{len(self.fingerings)} doigtés>")


#: Un nombre tel que Fortran l'écrit — et il l'écrit plus librement que la
#: plupart des langages : `10.e-3` et `1.e10` ont un point sans décimale
#: derrière, `.5` n'a pas de chiffre devant. Une regex qui l'ignore ne
#: renvoie pas une erreur : elle découpe `10.e-3` en `10` puis `-3`, décale
#: toutes les colonnes du tableau, et on lit un paramètre pour un autre.
_NOMBRE = re.compile(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eEdD][-+]?\d+)?')


def _floats(ligne):
    return [float(x.replace('d', 'e').replace('D', 'E')) for x in _NOMBRE.findall(ligne)]


def _lire_lignes(chemin):
    with open(chemin, 'r', encoding='latin-1') as f:
        return [l.rstrip('\n').rstrip('\r') for l in f]


def _valeurs_apres(lignes, i, combien):
    """Lit `combien` nombres à partir de la ligne `i`, sur autant de lignes
    qu'il faut — TUTT répartit librement ses tableaux sur plusieurs lignes."""
    out = []
    j = i
    while len(out) < combien and j < len(lignes):
        out.extend(_floats(lignes[j]))
        j += 1
    return np.array(out[:combien], dtype='float64'), j


def read_dat(chemin):
    """Lit un fichier d'entrée TUTT (`.dat`).

    Les étiquettes sont repérées par mot-clé et non par position : TUTT a
    changé de format entre versions (tutt25, tutt40, tutt43) et les fichiers
    d'une bibliothèque constituée sur des années ne sont pas homogènes.
    """
    lignes = _lire_lignes(chemin)
    out = BoreDat()
    haut = [l.upper() for l in lignes]

    for i, l in enumerate(haut):
        if 'NOMBRE DE TRONCONS' in l:
            v, _ = _valeurs_apres(lignes, i + 1, 1)
            out.n_sections = int(v[0])
        elif 'BAS DE LIGNE' in l:
            v, _ = _valeurs_apres(lignes, i + 1, 1)
            out.closed_bottom = bool(round(v[0]))
        elif 'FREQUENCE DU LA' in l:
            v, _ = _valeurs_apres(lignes, i + 1, 1)
            out.a4_hz = float(v[0])
        elif 'TEMPERATURE' in l:
            v, _ = _valeurs_apres(lignes, i + 1, 2)
            out.temperature_c = (float(v[0]), float(v[1]))

    n1 = out.n_sections + 1
    n = max(out.n_sections, 0)
    for i, l in enumerate(haut):
        if 'TABLEAU PERCE D0 ' in l or l.strip().startswith('TABLEAU PERCE D0'):
            out.d0, _ = _valeurs_apres(lignes, i + 1, n1)
        elif 'TABLEAU PERCE DL' in l:
            out.dl, _ = _valeurs_apres(lignes, i + 1, n1)
        elif 'TRONCONS DE LA LIGNE PRINCIPALE' in l:
            out.lengths, _ = _valeurs_apres(lignes, i + 1, n1)
        elif 'OFILIB' in l:
            out.ofilib, _ = _valeurs_apres(lignes, i + 1, n1)
        elif 'LATERAUX D0P' in l:
            out.hole_d0, _ = _valeurs_apres(lignes, i + 1, n)
        elif 'LATERAUX DLP' in l:
            out.hole_dl, _ = _valeurs_apres(lignes, i + 1, n)
        elif 'LATERAUX LP0' in l:
            out.hole_len, _ = _valeurs_apres(lignes, i + 1, n)
        elif 'ISTYLE' in l:
            # 0 = pas de clé, 1 = plateau creux, 2 = plateau plein
            out.istyle, _ = _valeurs_apres(lignes, i + 1, n)
        elif 'LEVEE DES CLES' in l:
            out.levee, _ = _valeurs_apres(lignes, i + 1, n)

    # -- embouchure : une ligne d'en-têtes, une ligne de valeurs
    for i, l in enumerate(haut):
        if 'IFLUTE' in l:
            cles = lignes[i].split()
            vals = _floats(lignes[i + 1]) if i + 1 < len(lignes) else []
            out.embouchure.update({k: v for k, v in zip(cles, vals)})
        elif 'MREED' in l and 'KREED' in l:
            cles = lignes[i].split()
            vals = _floats(lignes[i + 1]) if i + 1 < len(lignes) else []
            out.embouchure.update({k.upper(): v for k, v in zip(cles, vals)})

    # -- titre : la première ligne qui n'est ni une étiquette ni des nombres
    for l in lignes[:6]:
        s = l.strip()
        if s and not _floats(s) and 'VERSION' not in s.upper() and 'TUTT' not in s.upper():
            out.title = s
            break

    # -- doigtés : lignes de 0/1 suivies d'un nom
    for l in lignes:
        # Le nom peut contenir des chiffres — « do5 », « fa#4 » — mais doit
        # commencer par une lettre, sinon on ramasserait les 0/1 du doigté
        # lui-même. La première version excluait les chiffres partout et
        # tronquait « doigt0 » en « doigt ».
        m = re.match(r"^\s*((?:[01]\s+){2,})['\s]*"
                     r"([A-Za-zÀ-ÿ#éè][A-Za-zÀ-ÿ#éè0-9 ]*)", l)
        if m:
            trous = [int(x) for x in m.group(1).split()]
            if len(trous) >= 2:
                out.fingerings.append((m.group(2).strip(), trous))
    return out


@dataclass
class TuttNote:
    """Ce que TUTT calcule pour un doigté."""
    name: str = ""
    f_target_hz: float = float('nan')     # OREF/2π — la note visée
    f_tube_hz: float = float('nan')       # OTUBE/2π — ce que le tuyau donne
    cents: float = float('nan')           # l'écart, et donc la justesse
    q: float = float('nan')

    @property
    def cents_recalcules(self):
        """Écart recalculé depuis les deux fréquences — vérifie la lecture."""
        if not (self.f_target_hz > 0 and self.f_tube_hz > 0):
            return float('nan')
        return 1200.0 * np.log2(self.f_tube_hz / self.f_target_hz)


def read_out(chemin):
    """Lit un fichier de résultats TUTT (`.out`).

    Chaque doigté occupe trois lignes :

        do       0.38E-02  0.17E-02  ...      ← nom + critères
        3100.9   3089.0    0.00E+00  0.27E+02 ← OREF, OTUBE, CLOUT, Q
                 -6.6      0.23E-05  ...      ← CENTS

    `OREF` et `OTUBE` sont des **pulsations** (rad/s), pas des fréquences :
    3100,9 rad/s = 493,5 Hz, soit do5 au diapason 415. On divise par 2π.
    """
    lignes = _lire_lignes(chemin)
    notes = []
    for i, l in enumerate(lignes):
        m = re.match(r"^\s{2,}([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ#0-9]{0,6})\s+[-+.\dEe]", l)
        if not m or i + 2 >= len(lignes):
            continue
        l2, l3 = _floats(lignes[i + 1]), _floats(lignes[i + 2])
        if len(l2) < 2 or not l3:
            continue
        n = TuttNote(name=m.group(1).strip())
        n.f_target_hz = l2[0] / (2 * np.pi)
        n.f_tube_hz = l2[1] / (2 * np.pi)
        n.cents = l3[0]
        if len(l2) >= 4:
            n.q = l2[3]
        notes.append(n)
    return notes


# =============================================================================
# Impédance d'entrée d'une perce
# =============================================================================

def celerite(temp_c):
    """Célérité du son, formule de TUTT : `329,95 + 0,69·T` (T en °C).

    Elle suppose l'air **saturé d'humidité et à 2,5 % de CO₂** — c'est-à-dire
    l'air expiré, pas l'air ambiant (réf. Coltman, JASA 65, 1979, 499). À
    20 °C elle donne 343,75 m/s, un peu au-dessus de la valeur sèche
    habituelle : le souffle du musicien est plus rapide que l'air de la pièce.
    """
    return 329.95 + 0.69 * float(temp_c)


def _gamma_prime():
    """Facteur de pertes de Mason : `(1 + 1,581·(√γ − 1/√γ))·√η`.

    Vaut 1,534·√η, là où la forme usuelle `1 + (γ−1)/√Pr` donne 1,475 — 4 %
    d'écart, sans conséquence pratique, mais autant prendre celle du logiciel
    auquel on se compare.
    """
    sg = np.sqrt(GAMMA)
    return (1.0 + 1.581 * (sg - 1.0 / sg)) * np.sqrt(ETA)


def _propagation(freqs, radius_m, temp_c=20.0, roughness=1.0):
    """Constante de propagation et impédance caractéristique, avec pertes.

    Formule de Kirchhoff telle que TUTT l'implémente (réf. Mason, *Phys. Rev.*
    31, 1928, 283), reprise ici terme pour terme :

        P = périmètre·γ' / (2·section·√(2ωρ))
        k = (ω/c)·[(1 + P) − jP]

    `P` est à la fois l'atténuation **et** le ralentissement de l'onde : les
    pertes de couche limite ne font pas qu'amortir, elles freinent. C'est ce
    qui explique qu'un tuyau sonne plus grave que sa longueur ne le dit — sur
    un cylindre Ø 15 mm à 167 Hz, `P = 1,7 %`, soit 30 cents.

    `roughness` est le `OFILIB` de TUTT : le rapport du périmètre réel au
    périmètre géométrique. Une perce en bois poreux ou corrodée frotte plus
    qu'un tube lisse de même section. Il n'entre **que** dans les pertes : un
    OFILIB de 1,5 abaisse le Q de moitié, il ne déplace pas les résonances de
    50 %.

    Vérification croisée : la valeur de `P` calculée ici (0,0173) coïncide à
    1 % près avec celle qu'on tire à la main de la formule de couche limite,
    et la première résonance du cylindre d'essai de TUTT tombe à 0,6 cent de
    ce que TUTT lui-même annonce.
    """
    c = celerite(temp_c)
    w = 2 * np.pi * np.asarray(freqs, dtype='float64')
    r = max(float(radius_m), 1e-5)
    d = 2.0 * r

    peri = np.pi * float(roughness) * d
    sm = np.pi * d * d / 4.0
    prov = peri * _gamma_prime() / (2.0 * sm * np.sqrt(2.0 * np.maximum(w, 1e-9) * RHO))

    k = w / c
    gamma = prov * k + 1j * k * (1.0 + prov)
    zc = RHO * c / (np.pi * r * r)
    return gamma, zc


def _z_troncon(freqs, d0, dl, length, z_aval, temp_c=20.0, roughness=1.0):
    """Impédance vue du côté `d0`, connaissant celle du côté `dl`. Un tronçon.

    C'est **la** formule de TUTT (`Ltran9.for`), et elle vaut d'être écrite
    en entier, parce que la remplacer par un empilement de cylindres — ce que
    faisait ce module jusqu'ici — donne un résultat faux d'un demi-ton sur un
    cône, sans rien signaler.

    Dans un tronçon tronconique d'origine `x = 0` côté `d0`, le diamètre vaut
    `d0·(1 + Δx)` avec la **conicité** de TUTT :

        Δ = (dl − d0) / (d0 · L)

    et les champs sont, non pas des ondes planes, mais des ondes sphériques :

        p(x) = (A·e^(−Γx) + B·e^(+Γx)) / (1 + Δx)
        w(x) = −S₀/(jωρ) · [A·a(x) − B·b(x)]
            a(x) = (−Γ + Δ(−Γx − 1))·e^(−Γx)
            b(x) = (−Γ + Δ(−Γx + 1))·e^(+Γx)

    Le `1/(1 + Δx)` sur la pression est la décroissance sphérique du cône ;
    les termes en `Δ` sur le débit en sont la contrepartie. **Ce sont eux qui
    font qu'un cône est un cône** : un empilement de cylindres les perd, et
    avec eux le registre à l'octave — les résonances retombent alors sur
    `tan(kL) = kL`, la signature d'un cône *fermé* à son petit bout.

    Un tronçon se traite ainsi en **un seul pas**, si long soit-il, au lieu
    d'un découpage à convergence surveillée. Plus juste *et* plus rapide, ce
    qui n'arrive pas si souvent. TUTT le dit d'ailleurs lui-même : « LES
    TRONCONS SONT SUPPOSES TRONCONIQUES ; ILS PEUVENT ETRE LONGS CAR ON TIENT
    COMPTE DES VARIATIONS SPATIALES DE PRESSION ET DE DEBIT ».

    `Γ` est la constante de propagation complexe avec pertes visco-thermiques
    (cf. `_propagation`) ; elle joue le rôle du `jk` de TUTT, au signe près.
    """
    freqs = np.asarray(freqs, dtype='float64')
    L = float(length)
    z_aval = np.asarray(z_aval, dtype='complex128')
    if L <= 0:
        return z_aval

    d0, dl = float(d0), float(dl)
    # pertes évaluées sur le rayon moyen du tronçon : la couche limite ne
    # connaît pas la conicité, seulement la paroi qu'elle frotte.
    gamma, _zc = _propagation(freqs, (d0 + dl) / 4.0, temp_c, roughness)
    omega = 2 * np.pi * freqs
    delta = (dl - d0) / (d0 * L)
    s0 = np.pi * d0 ** 2 / 4.0
    g = s0 / (1j * omega * RHO)

    e_moins, e_plus = np.exp(-gamma * L), np.exp(+gamma * L)
    a_l = (-gamma + delta * (-gamma * L - 1.0)) * e_moins
    b_l = (-gamma + delta * (-gamma * L + 1.0)) * e_plus
    a_0, b_0 = (-gamma - delta), (-gamma + delta)

    # On ne forme jamais le rapport A/B : il diverge quand B s'annule. On
    # garde le couple (numérateur, dénominateur), qui ne diverge pas.
    rayon = 1.0 + delta * L
    na = -e_plus / rayon + z_aval * g * b_l          # A ∝ na
    nb = e_moins / rayon + z_aval * g * a_l          # B ∝ nb
    return (na + nb) / (-g * (na * a_0 - nb * b_0))


def diametre_effectif_trou(d0p, dlp, lp0):
    """Le diamètre qui compte pour une cheminée, selon `LCZB` de TUTT.

    Une cheminée n'est pas toujours un cylindre : le perçage est souvent
    conique, ou sous-coupé (*undercut*), et les deux bouts n'ont pas le même
    diamètre. Lequel prendre pour la correction de longueur ?

    Ninob tranche par une moyenne pondérée par la sveltesse de la cheminée :

        `d_eff = e^{−LP0/DLP}·min(D0P, DLP) + (1 − e^{−LP0/DLP})·DLP`

    Haute devant son diamètre, la cheminée se comporte comme un tuyau et
    c'est son diamètre intérieur `DLP` qui mène ; basse devant son diamètre
    — le cas d'un gros trou dans une paroi mince, la bombarde exactement —
    c'est le **plus petit** des deux qui mène, parce que c'est lui qui
    étrangle le passage.
    """
    d0p, dlp, lp0 = float(d0p), float(dlp), float(lp0)
    poids = math.exp(-lp0 / (dlp + 1e-5))
    return poids * min(d0p, dlp) + (1.0 - poids) * dlp


def cheminee_effective(d0p, dlp, lp0, d_perce, ouvert,
                       istyle=0, levee=1.0, pression=0.0, flutec=1.0):
    """`LCZB` : la hauteur **acoustique** d'une cheminée, corrections comprises.

    C'est la pièce qui manquait, et elle manquait beaucoup. Le fichier `.dat`
    donne `LP0`, la hauteur *percée* — l'épaisseur de bois sous le doigt. Ce
    n'est pas ce que l'air voit. TUTT le dit en toutes lettres dans
    `LTRANS` : « LP = TABLEAU DES LONGUEURS **EFFECTIVES** DES LIGNES
    LATERALES … COMPTE TENU DES CORRECTIONS DE LONGUEUR ÉVALUÉES
    PRÉALABLEMENT ».

    Deux corrections, **appliquées seulement si le trou est ouvert** :

    - **intérieure** (Nederveen, *Acustica* 28, 1973, p. 12) :
      `c_int = (d_eff/2)·(1,3 − 0,9·d_eff/d_perce)`. C'est le volume d'air
      qui, dans la perce elle-même, participe au mouvement dans la cheminée.
      Sur la bombarde d'Ewen elle vaut **3,8 mm pour une cheminée percée de
      2,35 mm** : elle triple la cheminée. L'ignorer rend chaque trou ouvert
      presque parfaitement court-circuitant, et alors la gamme s'étire —
      c'était notre cas, +14 % sur chaque intervalle.
    - **extérieure**, dite effet de jet : `c_out = ζ·p̃·flutec·d_eff` avec
      ζ = 4, `flutec` = 1 pour une anche et 0,1 pour une flûte, et `p̃` la
      pression acoustique au droit du trou normalisée par son maximum dans
      le tuyau. Elle dépend donc du champ, pas seulement de la géométrie :
      TUTT fait deux passes, la première avec `p̃ = 0`. Ici `pression` vaut
      0 par défaut, ce qui est exactement la première passe de TUTT.

    Un trou **fermé** garde sa hauteur brute : rien ne dépasse dans la
    perce, il n'y a rien à corriger. C'est pour ça qu'un doigté fourchu
    marche — et c'est pour ça qu'il ne marchait pas chez nous.
    """
    d0p, dlp, lp0 = float(d0p), float(dlp), float(lp0)
    if d0p < 1e-8:
        return lp0                         # pas de trou : rien à corriger
    ouv = 1.0 if ouvert else 0.0
    d_eff = diametre_effectif_trou(d0p, dlp, lp0)
    c_int = (d_eff * (1.3 - 0.9 * d_eff / d_perce) / 2.0) * ouv
    c_out = 4.0 * float(pression) * float(flutec) * d_eff * ouv
    # corrections de clé — nulles sans clé (ISTYLE = 0), ce qui est le cas de
    # tous les instruments à trous nus.
    c_cle_ext = c_cle_int = 0.0
    if istyle:
        rayon = d0p / 2.0
        c_cle_ext = (0.65 * rayon * ((rayon / max(levee, 1e-9)) ** 0.39 - 1.0)
                     * ouv * istyle / 2.0)
        if istyle == 1:                    # plateau creux
            c_cle_int = 1.0e-3 * (1.0 - ouv)
    return lp0 + c_int + c_out + c_cle_ext + c_cle_int


def _z_bout_trou(freqs, d_bout, longueur_brute, section):
    """`ZBOUT` : ce que voit le bout ouvert d'une cheminée.

    Rayonnement **et** perte de charge, comme Ninob les écrit :

        `Z = jρω·c_out/S · (1 − jω·c_out/c) + 7,5·π·LC·η·ρ/S²`

    avec `c_out = 0,35·d` — la correction de bout classique, prise ici non
    comme un allongement mais comme un ingrédient de l'impédance, ce qui
    évite d'avoir à la rajouter ailleurs. Le second terme est la perte de
    charge visqueuse dans la cheminée, de type Stokes (écoulement laminaire
    supposé : TUTT reste dans l'acoustique linéaire des petites
    oscillations). Diamètre et surface sont donnés séparément pour pouvoir
    traiter un trou **ovale**, où l'un ne se déduit pas de l'autre.

    Le facteur `ρ` du terme visqueux est celui du source ; dimensionnellement
    une résistance de Poiseuille s'écrit `8πηL/S²` sans densité. On le garde
    tel quel — il ne pèse que 1,2 sur un terme déjà mille fois plus petit que
    le rayonnement — mais on le note plutôt que de le corriger en douce.
    """
    w = 2 * np.pi * np.asarray(freqs, dtype='float64')
    c_out = 0.35 * float(d_bout)
    s = float(section)
    z_ray = 1j * RHO * w * c_out / s * (1.0 - 1j * w * c_out / CELERITE)
    z_visq = 7.5 * np.pi * float(longueur_brute) * ETA * RHO / s ** 2
    return z_ray + z_visq


def _z_trou(freqs, d0p, dlp, longueur, ouvert, temp_c=20.0, roughness=1.0,
            longueur_brute=None):
    """Impédance d'une cheminée latérale, vue depuis la perce principale.

    Un trou n'est pas un bouton qu'on enfonce : c'est **un tuyau de plus**,
    court et étroit, branché en dérivation. TUTT le dit dans sa façon de
    décrire l'instrument — « UNE COLONNE D'AIR RAMIFIEE EN ARETE DE
    POISSON » — et lui donne sa propre géométrie (`D0P`, `DLP`, `LP0`), sa
    propre constante de propagation, sa propre impédance de bout.

    - **ouvert**, la cheminée débouche à l'air libre : elle porte son
      impédance de bout (`_z_bout_trou`), petite, qui court-circuite la perce
      en dessous. Le tuyau se comporte comme s'il s'arrêtait là — d'où la
      note plus aiguë.
    - **fermé**, elle est bouchée au bout : impédance infinie, et il ne reste
      que le petit volume de la cheminée, qui alourdit très légèrement la
      colonne. Un trou fermé n'est donc pas neutre, et c'est pourquoi TUTT le
      garde dans le calcul plutôt que de l'effacer.

    `longueur` est la hauteur **effective** (cf. `cheminee_effective`), celle
    que remonte la ligne ; `longueur_brute` est la hauteur percée, que TUTT
    passe seule à `ZBOUT` pour la perte de charge — c'est bien le bois réel
    que l'air frotte, pas la correction.

    Une cheminée de section nulle (`D0P = 0`) est un changement de perce sans
    trou : le module rend alors une impédance infinie, qui ne change rien en
    parallèle.
    """
    freqs = np.asarray(freqs, dtype='float64')
    d0p, dlp, longueur = float(d0p), float(dlp), float(longueur)
    infini = np.full(np.shape(freqs), 1e12, dtype='complex128')
    if d0p < 1e-8 or longueur < 1e-8:
        return infini                      # pas de trou ici, juste un raccord
    if longueur_brute is None:
        longueur_brute = longueur

    if ouvert:
        z_bout = _z_bout_trou(freqs, d0p, longueur_brute,
                              np.pi * d0p ** 2 / 4.0)
    else:
        z_bout = infini
    # La cheminée se remonte comme un tronçon : elle est souvent conique elle
    # aussi (perçage conique, chambrage), d'où D0P ≠ DLP.
    #
    # **Quel bout est lequel.** `LTRANS` le dit : « POUR CES DERNIERS,
    # L'ORIGINE EST PRISE AU BOUT DE LA LIGNE OPPOSÉE AU NŒUD » — l'origine
    # de la cheminée est son bout **libre**, donc `D0P` est le bout libre et
    # `DLP` le bout qui débouche dans la perce. Le fichier le confirme pour
    # le bout mort d'une flûte : « D0P(N) est le diamètre du bout mort au
    # niveau du bouchon, DLP(N) au niveau de l'embouchure » — D0P loin du
    # tube, DLP au tube. Et `LCZB` passe bien `D0P` à `ZBOUT`, qui calcule un
    # rayonnement : c'est le bout qui rayonne.
    #
    # `_z_troncon(d0, dl, …)` rend l'impédance du côté `d0` connaissant celle
    # du côté `dl`. Ici on connaît celle du bout libre et on veut celle au
    # nœud : c'est donc `dlp` qui joue le rôle de `d0`, et `d0p` celui de
    # `dl`. Les prendre dans l'ordre du fichier, c'est parcourir la cheminée
    # à l'envers.
    return _z_troncon(freqs, dlp, d0p, longueur, z_bout, temp_c, roughness)


def _impedance_rayonnement(freqs, radius_m, flanged=False):
    """Impédance de rayonnement au bout ouvert.

    Sans elle, un tuyau ouvert réfléchirait parfaitement et ne rayonnerait
    rien — il n'y aurait ni son au dehors, ni amortissement des résonances
    aiguës. La correction de longueur (0,6 r) qui en découle est ce qui fait
    qu'un tuyau sonne toujours un peu plus grave que sa longueur ne le dit.
    """
    w = 2 * np.pi * np.asarray(freqs, dtype='float64')
    k = w / CELERITE
    a = float(radius_m)
    zc = RHO * CELERITE / (np.pi * a * a)
    ka = k * a
    if flanged:
        return zc * (0.25 * ka ** 2 + 1j * 0.8216 * ka)
    return zc * (0.25 * ka ** 2 + 1j * 0.6133 * ka)


def _doigte_en_tableau(dat: BoreDat, fingering, n):
    """Normalise un doigté : nom du fichier, liste de 0/1, ou rien.

    `1` = trou **fermé**, `0` = ouvert, comme le `CP` de TUTT — et non
    l'inverse, piège classique puisqu'on dit « boucher un trou » et qu'on
    écrit 1 pour ça.

    Sans doigté, tout est fermé : c'est le seul choix qui redonne exactement
    ce que le module calculait avant que les trous existent.
    """
    if fingering is None:
        return np.ones(n, dtype=int)
    if isinstance(fingering, str):
        for nom, trous in dat.fingerings:
            if nom.strip().lower() == fingering.strip().lower():
                fingering = trous
                break
        else:
            connus = ', '.join(nom for nom, _ in dat.fingerings) or 'aucun'
            raise ValueError(f"doigté inconnu : {fingering!r}. Connus : {connus}")
    out = np.ones(n, dtype=int)
    v = np.asarray(fingering, dtype=int).ravel()
    out[:min(n, v.size)] = v[:min(n, v.size)]
    return out


def input_impedance(dat: BoreDat, freqs, n_slices=None,
                    reed_volume_m3=None, fingering=None):
    # `n_slices` n'a plus d'effet : chaque tronçon se traite en un pas exact
    # (cf. `_z_troncon`). Le paramètre reste accepté pour ne pas casser les
    # appels existants.
    """Impédance d'entrée de la colonne principale, vue de l'embouchure.

    **Sens de lecture des tableaux.** TUTT décrit l'instrument du *pavillon*
    (indice 0) vers l'*embouchure* (indice N) — le manuel le dit : « pour le
    tronçon N+1 décrivant l'embouchure… ». Dans chaque tronçon, `DL` est le
    côté pavillon et `D0` le côté embouchure ; la continuité se lit
    `DL[i] = D0[i-1]`.

    On part donc du **bout ouvert** (`DL[0]`, la sortie du pavillon), qui
    porte l'impédance de rayonnement, et on remonte tronçon par tronçon
    jusqu'à l'embouchure.

    Lire à l'envers ne donne pas un résultat « un peu faux » mais un
    instrument qui n'existe pas : sur la bombarde sol d'Ewen, les rapports de
    résonances passent de 1 : 1,99 : 2,96 (série harmonique, ce que doit
    donner un cône) à 1 : 1,79 : 2,63 (rien de connu).

    **Trous latéraux.** `fingering` donne l'état de chaque cheminée, dans
    l'ordre des tableaux du fichier : `0` = ouvert, `1` = fermé, comme le
    `CP` de TUTT. On peut aussi passer le **nom** d'un doigté du fichier
    (`'fa'`, `'sol'`…) et il sera cherché dans `dat.fingerings`. Sans
    `fingering`, tout est considéré **fermé** — ce qui redonne exactement la
    colonne principale seule, c'est-à-dire l'ancien comportement du module.

    Chaque cheminée se pose **en parallèle** au nœud qui la porte : la perce
    et le trou débouchent sur le même point, donc les admittances s'ajoutent.
    Un trou ouvert court-circuite ce qui est en dessous — le tuyau se
    comporte comme s'il s'arrêtait là, et la note monte.

    `n_slices` est conservé pour compatibilité, mais n'a plus d'effet : le
    tronçon conique est exact, il n'y a plus rien à découper.
    """
    freqs = np.asarray(freqs, dtype='float64')
    # Le fichier donne les températures « en haut et en bas de la ligne » : en
    # haut, c'est l'embouchure — là où souffle le musicien, donc la chaude.
    # Les inverser refroidit le bec et réchauffe le pavillon, soit l'exact
    # contraire de ce qui se passe.
    t_emb, t_pav = dat.temperature_c
    n = len(dat.lengths)
    if n == 0:
        raise ValueError("géométrie vide : le fichier a-t-il été lu ?")

    r_bout = float(dat.dl[0]) / 2.0          # sortie du pavillon
    if dat.closed_bottom:
        Z = np.full(freqs.shape, 1e12, dtype='complex128')
    else:
        Z = _impedance_rayonnement(freqs, r_bout).astype('complex128')

    # Profil de température **exponentiel**, constante 0,25 m, comme TUTT :
    # le souffle chaud du musicien ne pénètre pas loin dans le tuyau. Une
    # interpolation linéaire réchaufferait tout le corps de l'instrument.
    doigte = _doigte_en_tableau(dat, fingering, n)

    xtot = float(np.sum(dat.lengths))
    rug = dat.roughness
    x = 0.0
    for i in range(n):
        x += dat.lengths[i]
        milieu = x - dat.lengths[i] / 2.0          # abscisse depuis le pavillon
        temp = t_pav + (t_emb - t_pav) * np.exp(-(xtot - milieu) / 0.25)
        # milieu se compte depuis le pavillon : l'exponentielle vaut 1 côté
        # embouchure (souffle chaud) et s'éteint vers le pavillon (ambiant).
        # on remonte du côté pavillon (DL) vers le côté embouchure (D0) :
        # `Z` est connue côté DL, on veut celle côté D0.
        Z = _z_troncon(freqs, dat.d0[i], dat.dl[i], dat.lengths[i], Z,
                       temp, float(rug[i]) if i < len(rug) else 1.0)

        # la cheminée du nœud i se branche en dérivation sur ce qu'on vient
        # de remonter : les admittances s'ajoutent.
        if i < len(dat.hole_d0) and i < len(dat.hole_len):
            d0p = float(dat.hole_d0[i])
            dlp = float(dat.hole_dl[i]) if i < len(dat.hole_dl) else d0p
            lp0 = float(dat.hole_len[i])
            ouvert = not doigte[i]
            # `dtube=(d0(i)+dl(i+1))/2.` dans LCZB : le diamètre de la perce
            # au droit du trou, moyenné sur le nœud que la cheminée perce.
            d_perce = (float(dat.d0[i]) +
                       float(dat.dl[i + 1] if i + 1 < len(dat.dl) else dat.d0[i])) / 2.0
            lp = cheminee_effective(
                d0p, dlp, lp0, d_perce, ouvert,
                istyle=int(dat.istyle[i]) if i < len(dat.istyle) else 0,
                levee=float(dat.levee[i]) if i < len(dat.levee) else 1.0,
                pression=0.0, flutec=1.0 if dat.solid_reed else 0.1)
            z_trou = _z_trou(freqs, d0p, dlp, lp, ouvert, temp,
                             float(rug[i]) if i < len(rug) else 1.0,
                             longueur_brute=lp0)
            Z = 1.0 / (1.0 / Z + 1.0 / z_trou)

    v = reed_volume_m3          # jamais déduit du fichier : cf. reed_volume_m3()
    if v and v > 0:
        # cavité d'anche **en parallèle** : les deux débouchent sur le même
        # nœud, celui du bec. En série elle allongerait le tuyau ; en
        # parallèle elle l'assouplit, ce qui n'est pas la même chose.
        w = 2 * np.pi * freqs
        Z = 1.0 / (1.0 / Z + 1j * w * (v / (RHO * CELERITE ** 2)))
    return Z


def resonances(dat: BoreDat, fmin=50.0, fmax=4000.0, n_points=6000,
               n_peaks=10, n_slices=None, reed_volume_m3=None,
               prominence_db=30.0, fingering=None):
    """Fréquences et facteurs Q des sommets de |Z| — les vraies résonances.

    C'est la sortie qui alimente `hybrid.modes_from_partials`, et donc la
    raison d'être du module : des résonances **calculées sur la géométrie**
    au lieu d'une série idéale supposée.

    Les sommets sont rendus dans l'**ordre des fréquences**, en partant du
    plus grave : `prominence_db` écarte au passage les bosses trop faibles
    pour être des résonances. Prendre les plus *forts* au lieu des premiers
    donnerait des rangs non consécutifs, et tout calcul d'octave ou de
    douzième fait dessus serait faux sans prévenir.
    """
    f = np.linspace(float(fmin), float(fmax), int(n_points))
    mod = np.abs(input_impedance(dat, f, n_slices, reed_volume_m3,
                                 fingering=fingering))

    interieur = np.arange(1, mod.size - 1)
    sommets = interieur[(mod[1:-1] > mod[:-2]) & (mod[1:-1] > mod[2:])]
    if sommets.size == 0:
        return [], [], []

    # Prendre les **premiers** sommets, pas les plus forts. Une série de
    # résonances est ordonnée en fréquence : retenir les plus hauts sommets
    # ramasse des rangs non consécutifs, et l'« octave » calculée ensuite ne
    # veut plus rien dire. Sur un cône nu, la fondamentale est rarement le
    # sommet le plus fort — c'est exactement là que je me suis fait avoir.
    garde = mod[sommets] >= mod[sommets].max() * 10 ** (-prominence_db / 20.0)
    sommets = sommets[garde][:int(n_peaks)]
    if sommets.size == 0:
        return [], [], []

    freqs, qs, pics = [], [], []
    for k in sommets:
        # interpolation parabolique : la résolution du balayage sinon
        a, b, c = mod[k - 1], mod[k], mod[k + 1]
        den = a - 2 * b + c
        dec = float(np.clip(0.5 * (a - c) / den, -0.5, 0.5)) if den < 0 else 0.0
        fc = f[k] + dec * (f[1] - f[0])

        seuil = b / np.sqrt(2.0)
        g = k
        while g > 0 and mod[g] > seuil:
            g -= 1
        d = k
        while d < mod.size - 1 and mod[d] > seuil:
            d += 1
        largeur = f[d] - f[g]
        freqs.append(float(fc))
        qs.append(float(fc / largeur) if largeur > 0 else float('nan'))
        pics.append(float(b))
    return freqs, qs, pics


def reed_impedance(freqs, mass_kg, stiffness, area_m2):
    """Impédance de l'anche vue comme oscillateur : `j(mω − k/ω)/A²`.

    C'est ainsi que TUTT pose l'anche (`Ltran9.for`) : une réactance pure,
    masse moins raideur, ramenée à la surface vibrante. Elle est négative
    sous la fréquence propre de l'anche, positive au-dessus, et nulle
    exactement dessus — ce qui fait que l'anche tire la note vers sa propre
    résonance d'autant plus fort qu'elle en est proche.

    `MREED` et `KREED` des fichiers `.dat` vont directement ici.
    """
    omega = 2 * np.pi * np.asarray(freqs, dtype='float64')
    a = float(area_m2)
    if a <= 0:
        raise ValueError("surface d'anche nulle")
    return 1j * (float(mass_kg) * omega - float(stiffness) / omega) / a ** 2


def playing_frequencies(dat: BoreDat, fmin=50.0, fmax=4000.0, n_points=8000,
                        reed=None, reed_area_m2=1.0e-4, coupling=0.0,
                        coupling_phase=0.0, z_mouth=0.0, n_max=24,
                        fingering=None, **kw):
    """Fréquences permises **au sens de TUTT** : les zéros de `Im(Z)`.

    Là où `resonances` prend les sommets de |Z| du tube nu, TUTT pose le
    critère complet, anche comprise (`Ltran9.for`) :

        Z = Z_anche + (Z_tube + Z_bouche) / FC        FC = FCM·e^(j·FCP)

    et cherche les fréquences où **la partie imaginaire s'annule**. C'est
    l'équation de la dynamique de l'anche en régime permanent : à ces
    fréquences-là, et à elles seules, l'anche peut osciller sans que rien ne
    la pousse ni ne la freine en quadrature.

    Un zéro se trouve d'ailleurs mieux qu'un sommet : il se coince entre deux
    points de signe opposé et s'interpole linéairement, sans parabole à
    ajuster ni résolution de balayage qui traîne. Sur le cylindre d'essai,
    les deux critères tombent à **0,07 Hz** l'un de l'autre (0,7 cent) — ce
    qui valide les deux d'un coup.

    Cette fonction rend **tous** les zéros trouvés, dans l'ordre des
    fréquences. C'est ce que fait TUTT : il calcule la liste, puis
    `Proxi.for` — ici `mode_le_plus_proche` — choisit celui qui tombe le plus
    près de la note visée. Aucun tri « par type de résonance » n'est fait ici,
    parce qu'aucun n'est fait là-bas.

    ⚠️ `coupling=0` (le défaut) débranche l'anche et ne laisse que le tube :
    c'est la seule branche **vérifiée** de cette fonction. Le terme d'anche
    est écrit d'après le source, mais il demande les vraies valeurs de
    `MREED`, `KREED` et de la surface vibrante, qui ne viennent qu'avec un
    fichier réel — inventer un jeu plausible donne des décalages de plus
    d'une octave, ce qui ne prouve rien d'autre que l'invention. À brancher
    et à confronter le jour où une perce d'Ewen passera par là.

    Ninob note dans le source ce qu'on doit alors y voir : avec une anche
    **solide** (roseau, métal) les fréquences permises sont proches des
    **antirésonances** du tube, avec une anche **aérienne** (jet de flûte)
    proches de ses **résonances**.
    """
    freqs = np.linspace(float(fmin), float(fmax), int(n_points))
    z_tube = input_impedance(dat, freqs, fingering=fingering, **kw)

    fcm = float(coupling)
    if fcm < 1e-5:
        z = z_tube + z_mouth               # pas d'anche : le tube seul
    else:
        if reed is None:
            reed = dat.reed_oscillator
        fc = fcm * np.exp(1j * float(coupling_phase))
        z = (reed_impedance(freqs, float(reed[0]), float(reed[1]), reed_area_m2)
             + (z_tube + z_mouth) / fc)

    im = np.imag(z)
    change = np.nonzero(np.sign(im[:-1]) * np.sign(im[1:]) < 0)[0]
    sortie = []
    for i in change[:int(n_max)]:
        a, b = im[i], im[i + 1]
        sortie.append(float(freqs[i] + (freqs[i + 1] - freqs[i]) * a / (a - b)))
    return sortie


def mode_le_plus_proche(modes_hz, cible_hz):
    """`Proxi.for` : lequel de ces modes joue la note visée, et à combien.

    TUTT ne décide pas *a priori* quel mode fait la note : il calcule la
    liste, puis prend celui qui tombe le plus près de la référence. Renvoie
    `(rang, fréquence, écart_en_cents)`.

    Le source prévoit les deux débordements et les nomme joliment : si la
    note visée est au-dessus du dernier mode trouvé c'est « !!!grave!!! », si
    elle est en dessous du premier c'est « !!!benin!!! ». Dans les deux cas
    il prend le mode extrême plutôt que de rendre une erreur, et on fait
    pareil : un instrument qui ne peut pas atteindre la note joue quand même
    quelque chose.
    """
    f = np.asarray(modes_hz, dtype='float64').ravel()
    if f.size == 0:
        raise ValueError("aucun mode : rien à choisir")
    cible = float(cible_hz)
    rang = int(np.argmin(np.abs(f - cible)))
    return rang, float(f[rang]), float(1200.0 * np.log2(f[rang] / cible))


def resonator_from_dat(chemin_ou_dat, fmin=50.0, fmax=4000.0, n_peaks=10,
                       cutoff_hz=None, cutoff_order=3.0, prune_db=45.0,
                       fingering=None, **kw):
    """Construit un `hybrid.Resonator` depuis une perce TUTT. Le pont complet.

    Renvoie `(resonator, infos)`. `infos` dit d'où vient chaque chose — la
    même discipline que `identify.py` : ce qui est calculé sur la géométrie
    ne doit pas se confondre avec ce qui reste supposé.

    `cutoff_hz` applique la coupure de réseau de trous de Benade (cf.
    `hybrid.bore_modes`) par-dessus les résonances calculées — utile pour une
    perce dont on ne modélise pas encore les trous eux-mêmes (`ideal_resonator`
    s'en sert). Les autres mots-clés (`reed_volume_m3`, `prominence_db`)
    vont à `resonances` ; `n_slices` y est accepté sans effet.
    """
    from .hybrid import Resonator, modes_from_partials, inharmonicity_cents

    dat = chemin_ou_dat if isinstance(chemin_ou_dat, BoreDat) \
        else read_dat(chemin_ou_dat)
    doigte = fingering
    freqs, qs, pics = resonances(dat, fmin, fmax, n_peaks=n_peaks,
                                 fingering=fingering, **kw)
    if not freqs:
        raise ValueError(f"aucune résonance trouvée entre {fmin} et {fmax} Hz")

    modes = modes_from_partials(freqs, qs=qs, peaks=pics, cutoff_hz=cutoff_hz,
                                cutoff_order=cutoff_order, prune_db=prune_db)
    infos = {
        'titre': dat.title,
        'tronçons': len(dat.lengths),
        'longueur_mm': dat.total_length_m * 1e3,
        'bout': 'fermé' if dat.closed_bottom else 'ouvert',
        'résonances_hz': [round(f, 2) for f in freqs],
        'inharmonicité_cents': [round(c, 1)
                                for c in inharmonicity_cents(modes)],
        'doigtés_dans_le_fichier': len(dat.fingerings),
        'trous_latéraux': 'NON POSÉS dans le calcul d\'impédance',
    }
    return Resonator(modes, name=dat.title or 'perce TUTT'), infos


# =============================================================================
# Perce idéale — TUTT comme moteur par défaut, sans fichier réel
# =============================================================================

def bore_dat_ideal(kind, f0_hz, bore_mm, bell_mm=None, taper=4.5,
                   temp_c=(32.0, 20.0), roughness=1.0):
    """Une perce à un seul tronçon — cylindre ou cône — qui vise `f0_hz`.

    Pour un **cylindre**, c'est solide : aucune ambiguïté de troncature, la
    longueur (quart d'onde, fermé à l'anche) et le calcul redonnent la série
    impaire exacte à la stretch de couche limite près, avec les pertes
    visco-thermiques de Kirchhoff/Mason et l'impédance de rayonnement de
    TUTT — la même chaîne que `resonator_from_dat`, validée à 1,5 cent sur la
    bombarde d'Ewen. `hybrid.clarinette` s'en sert par défaut.

    Pour un **cône**, ⚠️ **ce n'est pas encore juste**, et c'est resté dans
    le module pour ne pas perdre l'essai : un cône à un seul tronçon, tronqué
    à `bore_mm` au lieu de rejoindre une vraie pointe, ne redonne pas le
    registre à l'octave attendu. Ses résonances suivent `tan(kL)=kL` — la
    même transcendante qu'un cône *fermé* à son petit bout — au lieu de la
    série harmonique d'un cône *entraîné près de sa pointe*, avec des écarts
    de plusieurs centaines de cents, vérifié en balayant `taper` de 4,5 à 100
    et le rayon tronqué de 0,5 mm à 0,5 µm sans que ça converge. Le calcul
    est probablement correct pour ce qu'il modélise ; c'est le modèle
    lui-même — une troncature franche, sans rien au-delà — qui ne représente
    pas ce qu'un vrai cône fait près de son sommet. Détail de l'essai et de
    ce qu'il faudrait pour le reprendre : `docs/modele_hybride_generalise.md`
    §9. `hybrid.saxophone`/`bombarde`/`cornemuse` restent donc sur
    `engine='ideal'` par défaut.

    La longueur vient des formules classiques du quart d'onde (cylindre) et
    du demi-onde (cône) — un point de départ, pas une valeur exacte : les
    corrections de bout et les pertes déplacent un peu la fondamentale
    réelle, et c'est justement ce que le calcul restitue. L'accordage note à
    note de `live.py` absorbe l'écart résiduel, comme il absorbe déjà celui
    de l'anche libre — mais n'absorbe pas une série de partiels fausse.

    `bore_mm` est le diamètre côté anche. Pour un cône, `bell_mm` donne le
    diamètre côté pavillon ; à défaut, `taper` (le rapport pavillon/anche)
    le fixe — 4,5 est un ordre de grandeur, pas une mesure, comme le reste
    des cotes de ce module tant qu'aucune vraie perce n'est en jeu.
    """
    c = celerite(float(temp_c[0]))
    if kind == 'cylindrique':
        # fermé à l'anche (nœud de vitesse), ouvert au pavillon : quart d'onde
        longueur = c / (4.0 * float(f0_hz))
        d_reed = d_bell = float(bore_mm) * 1e-3
    elif kind == 'conique':
        # l'anche au sommet d'un cône se comporte comme un tube ouvert aux
        # deux bouts : la série est harmonique complète, et la longueur se
        # règle sur une demi-onde plutôt qu'un quart d'onde.
        longueur = c / (2.0 * float(f0_hz))
        d_reed = float(bore_mm) * 1e-3
        d_bell = float(bell_mm) * 1e-3 if bell_mm else d_reed * float(taper)
    else:
        raise ValueError("kind doit valoir 'cylindrique' ou 'conique'")

    return BoreDat(
        title=f"perce idéale {kind}, f0={float(f0_hz):.1f} Hz",
        n_sections=1,
        closed_bottom=False,
        d0=np.array([d_reed]),
        dl=np.array([d_bell]),
        lengths=np.array([longueur]),
        ofilib=np.array([float(roughness)]),
        temperature_c=(float(temp_c[0]), float(temp_c[1])),
    )


def ideal_resonator(kind, f0_hz, bore_mm, n_modes=10, bell_mm=None,
                    taper=4.5, cutoff_hz=None, cutoff_order=3.0, **kw):
    """Résonateur TUTT d'une perce idéalisée à un tronçon.

    Solide pour `kind='cylindrique'` (aucune troncature de cône à trancher) ;
    **pas encore juste pour `kind='conique'`** — cf. l'avertissement de
    `bore_dat_ideal`. `hybrid._wind` n'appelle donc cette fonction par défaut
    que pour la clarinette.

    Renvoie `(resonator, infos)`, comme `resonator_from_dat` — dont c'est un
    simple appel, sur une perce à un tronçon plutôt que lue d'un fichier.
    """
    dat = bore_dat_ideal(kind, f0_hz, bore_mm, bell_mm=bell_mm, taper=taper)
    rang_max = (2 * int(n_modes) - 1) if kind == 'cylindrique' else int(n_modes)
    fmin = max(20.0, 0.5 * float(f0_hz))
    fmax = min(9000.0, float(f0_hz) * (rang_max + 1.5))
    n_peaks = rang_max + 2
    return resonator_from_dat(dat, fmin=fmin, fmax=fmax, n_peaks=n_peaks,
                              cutoff_hz=cutoff_hz, cutoff_order=cutoff_order,
                              **kw)


# =============================================================================
# Mise à l'échelle — la vraie réponse à « peut-on simplifier une perce »
# =============================================================================

def gamme_des_doigtes(dat: BoreDat, doigtes=None, fmin=50.0, fmax=3000.0,
                      **kw):
    """Ce que chaque doigté donne comme note. La gamme d'une perce réelle.

    C'est le pont que tout le reste attendait. Une vraie perce ne se
    transpose pas note par note : elle a des **trous**, et chaque
    combinaison de doigts donne une note. Maintenant que les cheminées sont
    posées, cette liste se calcule.

    `doigtes` accepte une liste de `(nom, tableau)` ; à défaut on prend ceux
    du fichier (`dat.fingerings`). Renvoie `[(nom, doigté, fréquence), …]`,
    trié du grave à l'aigu — c'est-à-dire la gamme de l'instrument, telle
    que sa géométrie la donne et non telle qu'on l'espérait.

    Un doigté dont aucune résonance ne sort de l'intervalle est écarté avec
    sa raison plutôt que rendu à zéro.
    """
    if doigtes is None:
        doigtes = dat.fingerings
    if not doigtes:
        raise ValueError("aucun doigté : ni fourni, ni dans le fichier")

    out = []
    for nom, trous in doigtes:
        f = resonances(dat, fmin, fmax, n_peaks=1, fingering=trous, **kw)[0]
        if f:
            out.append((nom, list(trous), float(f[0])))
    out.sort(key=lambda t: t[2])
    return out


def cavite_qui_accorde_l_octave(dat: BoreDat, fmin=40.0, fmax=3000.0,
                                v_max=None, tol_cents=0.5, n_iter=40,
                                **kw):
    """Le volume de cavité d'anche qui rend l'octave juste. Dichotomie.

    Un cône tronqué octavie trop haut : il lui manque le bout pointu. Ninob
    montre (*Modes propres d'un tronc de cône*) qu'une anche solide au petit
    bout se comporte comme une **cavité ajoutée**, qui abaisse les modes
    graves plus que les aigus et corrige l'octave — c'est ce qui permet à un
    saxophone ou à un hautbois d'octavier juste.

    Cette fonction cherche le volume qui l'annule, et c'est exactement le
    geste d'un facteur : on ne calcule pas la cavité, on l'ajuste jusqu'à ce
    que l'octave tombe juste. L'écart varie de façon monotone avec le volume
    (mesuré : +95 cents à vide, +27 à 1,12 cm³, +2 à 1,5 cm³, −30 à 2 cm³),
    donc une dichotomie suffit et converge sans surprise.

    Renvoie `(volume_m3, écart_en_cents)`. Si aucun volume de l'intervalle ne
    change le signe de l'écart, renvoie le meilleur trouvé plutôt que de
    lever : une perce dont l'octave est déjà juste n'a rien à corriger, et
    c'est une réponse, pas une erreur.

    `v_max` borne la recherche ; à défaut, dix fois le volume du cône
    géométriquement manquant, ce qui couvre largement (le volume qui corrige
    vaut environ 1,3 fois celui-là).
    """
    def ecart(v):
        f = resonances(dat, fmin, fmax, n_peaks=2,
                       reed_volume_m3=(v if v and v > 0 else None), **kw)[0]
        if len(f) < 2:
            return float('nan')
        return 1200.0 * np.log2((f[1] / f[0]) / 2.0)

    if v_max is None:
        # volume du cône manquant : (1/3)·π·r₀²·x₁, avec x₁ l'apex virtuel
        r0, r1 = float(dat.d0[-1]) / 2.0, float(dat.dl[0]) / 2.0
        longueur = float(np.sum(dat.lengths))
        if r1 <= r0:
            v_max = np.pi * r0 ** 2 * longueur          # cylindre : pas d'apex
        else:
            x1 = longueur * r0 / (r1 - r0)
            v_max = 10.0 * np.pi * r0 ** 2 * x1 / 3.0

    bas, haut = 0.0, float(v_max)
    e_bas, e_haut = ecart(bas), ecart(haut)
    if not np.isfinite(e_bas):
        raise ValueError("octave introuvable : la perce a-t-elle deux modes ?")
    if not np.isfinite(e_haut) or e_bas * e_haut > 0:
        return (bas, e_bas) if abs(e_bas) <= abs(e_haut) else (haut, e_haut)

    for _ in range(int(n_iter)):
        milieu = 0.5 * (bas + haut)
        e = ecart(milieu)
        if not np.isfinite(e):
            break
        if abs(e) < float(tol_cents):
            return milieu, e
        if e_bas * e < 0:
            haut, e_haut = milieu, e
        else:
            bas, e_bas = milieu, e
    milieu = 0.5 * (bas + haut)
    return milieu, ecart(milieu)


def scale_bore(dat: BoreDat, factor, title=None):
    """La même forme, à une autre taille. Rien d'autre ne change.

    Un cône réduit à un seul tronçon casse le registre (§9 de
    `modele_hybride_generalise.md`, et `test_le_cone_idealise_tronque_n_est
    _pas_encore_juste`) : ses résonances suivent `tan(kL)=kL` au lieu de la
    série harmonique, parce que la **forme** décide du registre, pas
    seulement la longueur et les deux diamètres d'extrémité.

    La vraie simplification n'est donc pas d'inventer une forme plus simple,
    c'est de **réutiliser une forme déjà juste**, à une autre échelle —
    exactement comme une famille d'instruments réels (soprano, alto, ténor)
    est une famille de formes proches mises à l'échelle, pas une famille de
    formes redessinées de zéro à chaque taille.

    Mesuré sur une perce à 3 tronçons artificielle, en faisant varier
    `factor` de 0,5 à 2 (soit une octave de gamme) : les **rapports** de
    résonance dérivent de moins de 2 % — le résidu attendu des pertes
    visco-thermiques, qui n'ont pas la même échelle de longueur que la
    géométrie (l'épaisseur de couche limite va en `1/√f`, pas en facteur
    d'échelle). La fondamentale suit `1/factor` à moins de 1 % près, l'écart
    restant se corrigeant comme d'habitude à l'accordage note à note.

    Multiplie longueurs, diamètres de perce **et** de trous latéraux.
    `ofilib` (rugosité) est sans dimension, inchangé. L'anche (`MREED`,
    `KREED`, `V0`/`V1`) n'est **pas** mise à l'échelle : elle suivrait sa
    propre loi, comme celle écrite pour l'anche libre dans `hybrid.accordeon`
    — pas encore faite ici, et il ne faut pas laisser croire le contraire.
    """
    k = float(factor)
    if k <= 0:
        raise ValueError("le facteur d'échelle doit être positif")
    return BoreDat(
        title=title if title is not None else f"{dat.title} (×{k:.3g})",
        n_sections=dat.n_sections,
        closed_bottom=dat.closed_bottom,
        d0=dat.d0 * k,
        dl=dat.dl * k,
        lengths=dat.lengths * k,
        hole_d0=dat.hole_d0 * k,
        hole_dl=dat.hole_dl * k,
        hole_len=dat.hole_len * k,
        ofilib=dat.ofilib.copy(),
        temperature_c=dat.temperature_c,
        a4_hz=dat.a4_hz,
        embouchure=dict(dat.embouchure),
        fingerings=list(dat.fingerings),
    )


def scale_bore_to(dat: BoreDat, f0_hz, fmin=30.0, fmax=4000.0, **kw):
    """`scale_bore`, avec le facteur **mesuré** plutôt que deviné.

    Cherche la fondamentale actuelle de `dat` (première résonance dans
    [fmin, fmax]), puis renvoie la perce mise à l'échelle pour viser
    `f0_hz`. C'est ce bloc, répété note par note, qui permettrait de couvrir
    un clavier entier à partir d'une seule perce mesurée — le pendant, côté
    perce réelle, de ce que fait déjà `live._accorder` côté anche libre.
    """
    freqs, _qs, _pics = resonances(dat, fmin, fmax, n_peaks=1, **kw)
    if not freqs:
        raise ValueError(f"aucune résonance trouvée entre {fmin} et {fmax} Hz "
                         f"— la perce vise-t-elle vraiment cette gamme ?")
    facteur = freqs[0] / float(f0_hz)
    return scale_bore(dat, facteur)


# =============================================================================
# Conversion tutt25 → tutt43
# =============================================================================

#: Blocs que TUTT 4.3 exige et que les fichiers d'avant (tutt25, tutt40) n'ont
#: pas. Chacun s'insère **après la ligne de valeurs** qui suit l'étiquette
#: donnée — pas après l'étiquette elle-même, sinon on sépare une étiquette de
#: ses valeurs et la lecture Fortran s'arrête sur « Bad real number ».
_BLOCS_MANQUANTS = (
    ('IFLUTE', 'MREED', ["MREED KREED LBUCC TANDELTA", "{mreed} {kreed} 0.1 1."]),
    ('AUTO ENTRETIEN', 'IMPADM',
     ["DONNEES CONCERNANT LE CALCUL IMPADM (-1 si impedance, 1 si admittance)",
      "-1"]),
)


def to_tutt43(chemin_entree, chemin_sortie, mreed=0.0, kreed=800.0):
    """Convertit un fichier TUTT ancien (tutt25/tutt40) au format 4.3.

    Une banque de perces constituée sur des années n'est pas homogène : le
    format a gagné des blocs en route. Trois différences, toutes mécaniques :

    1. **l'en-tête de version** (deux lignes) que 4.3 lit en premier ;
    2. le bloc **`MREED`/`KREED`** — masse et raideur de l'anche solide. Les
       anciens fichiers ne l'ont pas. Les valeurs par défaut ne comptent que
       pour une anche solide, et il faut les renseigner pour une justesse fine ;
    3. le bloc **`IMPADM`** : zéros de l'impédance (−1) ou de l'admittance (+1).

    Plus un détail qui bloque la lecture : dans la table des doigtés,
    `'fa    '100` doit devenir `'fa    ' 100`. Sans séparateur après le nom,
    Fortran s'arrête sur « Bad integer ».

    Renvoie le chemin écrit.
    """
    import pathlib
    lignes = _lire_lignes(chemin_entree)
    presents = {marqueur for _, marqueur, _ in _BLOCS_MANQUANTS
                if any(marqueur in l.upper() for l in lignes)}

    out = []
    if not (lignes and 'VERSION FORMAT' in lignes[0].upper()):
        out += ["VERSION FORMAT DE FICHIER D'ENTREE AVEC MENTION DE LA VERSION DE TUTT",
                "TUTT43_2024.11"]

    attendu = None                      # bloc à poser après la prochaine ligne
    for ligne in lignes:
        out.append(re.sub(r"'(\d)", r"' \1", ligne))
        if attendu is not None:         # on vient d'écrire la ligne de valeurs
            out += attendu
            attendu = None
            continue
        haut = ligne.upper()
        for ancre, marqueur, bloc in _BLOCS_MANQUANTS:
            if ancre in haut and marqueur not in presents:
                attendu = [b.format(mreed=mreed, kreed=kreed) for b in bloc]
                break

    p = pathlib.Path(chemin_sortie)
    p.write_text("\n".join(out) + "\n", encoding='latin-1')
    return str(p)

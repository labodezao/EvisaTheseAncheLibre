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

⚠️ Les trous latéraux ne sont **pas** encore posés dans le calcul
d'impédance : seule la colonne principale l'est. Un doigté tous trous fermés
est donc juste, un doigté ouvert ne l'est pas. TUTT, lui, les traite. À faire.
"""
from __future__ import annotations

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
    temperature_c: tuple = (20.0, 20.0)   # (pavillon, embouchure)
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
        m = re.match(r"^\s*((?:[01]\s+){2,})['\s]*([A-Za-zÀ-ÿ#éè][^\d']*)", l)
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


def _matrice_troncon(freqs, d0, dl, length, temp_c=20.0, n_slices=None,
                     roughness=1.0):
    """Matrice de transfert d'un tronçon, conique ou cylindrique.

    Un cône est découpé en tranches cylindriques. C'est moins élégant qu'une
    matrice conique analytique, mais c'est **vérifiable** : on augmente le
    nombre de tranches jusqu'à ce que le résultat ne bouge plus, et on n'a
    aucune formule à se tromper.
    """
    freqs = np.asarray(freqs, dtype='float64')
    r0, r1 = float(d0) / 2.0, float(dl) / 2.0
    L = float(length)
    if L <= 0:
        z = np.ones_like(freqs, dtype='complex128')
        o = np.zeros_like(z)
        return np.array([[z, o], [o, z]])

    if n_slices is None:
        conicite = abs(r1 - r0) / max(r0, r1, 1e-9)
        n_slices = 1 if conicite < 1e-6 else max(8, int(60 * conicite))

    bords = np.linspace(0.0, 1.0, n_slices + 1)
    rayons = r0 + (r1 - r0) * 0.5 * (bords[:-1] + bords[1:])
    dl_slice = L / n_slices

    un = np.ones_like(freqs, dtype='complex128')
    zero = np.zeros_like(un)
    A, B, C, D = un.copy(), zero.copy(), zero.copy(), un.copy()
    for r in rayons:
        g, zc = _propagation(freqs, r, temp_c, roughness)
        gl = g * dl_slice
        ch, sh = np.cosh(gl), np.sinh(gl)
        a, b, c_, d = ch, zc * sh, sh / zc, ch
        A, B, C, D = A * a + B * c_, A * b + B * d, C * a + D * c_, C * b + D * d
    return np.array([[A, B], [C, D]])


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


def input_impedance(dat: BoreDat, freqs, n_slices=None,
                    reed_volume_m3=None):
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

    ⚠️ Trous latéraux non posés — cf. l'avertissement du module.
    """
    freqs = np.asarray(freqs, dtype='float64')
    t_pav, t_emb = dat.temperature_c
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
    xtot = float(np.sum(dat.lengths))
    rug = dat.roughness
    x = 0.0
    for i in range(n):
        x += dat.lengths[i]
        milieu = x - dat.lengths[i] / 2.0          # abscisse depuis le pavillon
        temp = t_pav + (t_emb - t_pav) * np.exp(-(xtot - milieu) / 0.25)
        # on remonte du côté pavillon (DL) vers le côté embouchure (D0)
        M = _matrice_troncon(freqs, dat.dl[i], dat.d0[i], dat.lengths[i],
                             temp, n_slices,
                             float(rug[i]) if i < len(rug) else 1.0)
        A, B, C, D = M[0, 0], M[0, 1], M[1, 0], M[1, 1]
        Z = (A * Z + B) / (C * Z + D)

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
               prominence_db=30.0):
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
    mod = np.abs(input_impedance(dat, f, n_slices, reed_volume_m3))

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


def resonator_from_dat(chemin_ou_dat, fmin=50.0, fmax=4000.0, n_peaks=10,
                       **kw):
    """Construit un `hybrid.Resonator` depuis une perce TUTT. Le pont complet.

    Renvoie `(resonator, infos)`. `infos` dit d'où vient chaque chose — la
    même discipline que `identify.py` : ce qui est calculé sur la géométrie
    ne doit pas se confondre avec ce qui reste supposé.
    """
    from .hybrid import Resonator, modes_from_partials, inharmonicity_cents

    dat = chemin_ou_dat if isinstance(chemin_ou_dat, BoreDat) \
        else read_dat(chemin_ou_dat)
    freqs, qs, pics = resonances(dat, fmin, fmax, n_peaks=n_peaks, **kw)
    if not freqs:
        raise ValueError(f"aucune résonance trouvée entre {fmin} et {fmax} Hz")

    modes = modes_from_partials(freqs, qs=qs, peaks=pics)
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

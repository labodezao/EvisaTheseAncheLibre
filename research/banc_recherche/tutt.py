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
    temperature_c: tuple = (20.0, 20.0)
    a4_hz: float = 440.0
    embouchure: dict = field(default_factory=dict)
    fingerings: list = field(default_factory=list)   # [(nom, [0/1, ...]), ...]

    @property
    def total_length_m(self):
        return float(np.sum(self.lengths))

    @property
    def is_flute(self):
        return bool(self.embouchure.get('IFLUTE', 0))

    def __repr__(self):
        return (f"<BoreDat {self.title[:40]!r} {len(self.lengths)} tronçons, "
                f"{self.total_length_m * 1e3:.0f} mm, "
                f"{len(self.fingerings)} doigtés>")


_NOMBRE = re.compile(r'[-+]?\d*\.?\d+(?:[eEdD][-+]?\d+)?')


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

def _propagation(freqs, radius_m, temp_c=20.0):
    """Constante de propagation et impédance caractéristique, avec pertes.

    Pertes visco-thermiques de couche limite (Kirchhoff) : l'atténuation
    croît en `√f` et décroît avec le rayon. C'est ce qui rend une perce
    étroite bien plus amortie qu'une large, et pourquoi un piccolo demande
    plus de souffle qu'une flûte basse.
    """
    c = CELERITE * np.sqrt((273.15 + temp_c) / 293.15)
    w = 2 * np.pi * np.asarray(freqs, dtype='float64')
    r = max(float(radius_m), 1e-5)

    # épaisseur de couche limite visqueuse
    delta = np.sqrt(2.0 * ETA / (RHO * np.maximum(w, 1e-9)))
    alpha = (delta / (r * 2.0)) * (1.0 + (GAMMA - 1.0) / np.sqrt(PRANDTL))
    k = w / c
    gamma = alpha * k + 1j * k * (1.0 + alpha)
    zc = RHO * c / (np.pi * r * r)
    return gamma, zc


def _matrice_troncon(freqs, d0, dl, length, temp_c=20.0, n_slices=None):
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
        g, zc = _propagation(freqs, r, temp_c)
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


def input_impedance(dat: BoreDat, freqs, n_slices=None):
    """Impédance d'entrée de la colonne principale, vue de l'embouchure.

    On remonte de la sortie vers l'entrée : le bout ouvert présente son
    impédance de rayonnement, chaque tronçon la transforme.

    ⚠️ Trous latéraux non posés — cf. l'avertissement du module.
    """
    freqs = np.asarray(freqs, dtype='float64')
    t0, t1 = dat.temperature_c
    n = len(dat.lengths)
    if n == 0:
        raise ValueError("géométrie vide : le fichier a-t-il été lu ?")

    r_bout = float(dat.dl[-1]) / 2.0
    if dat.closed_bottom:
        Z = np.full(freqs.shape, 1e12, dtype='complex128')
    else:
        Z = _impedance_rayonnement(freqs, r_bout).astype('complex128')

    for i in range(n - 1, -1, -1):
        frac = (i + 0.5) / n
        temp = t0 + (t1 - t0) * frac
        M = _matrice_troncon(freqs, dat.d0[i], dat.dl[i], dat.lengths[i],
                             temp, n_slices)
        A, B, C, D = M[0, 0], M[0, 1], M[1, 0], M[1, 1]
        Z = (A * Z + B) / (C * Z + D)
    return Z


def resonances(dat: BoreDat, fmin=50.0, fmax=4000.0, n_points=6000,
               n_peaks=10, n_slices=None):
    """Fréquences et facteurs Q des sommets de |Z| — les vraies résonances.

    C'est la sortie qui alimente `hybrid.modes_from_partials`, et donc la
    raison d'être du module : des résonances **calculées sur la géométrie**
    au lieu d'une série idéale supposée.
    """
    f = np.linspace(float(fmin), float(fmax), int(n_points))
    mod = np.abs(input_impedance(dat, f, n_slices))

    interieur = np.arange(1, mod.size - 1)
    sommets = interieur[(mod[1:-1] > mod[:-2]) & (mod[1:-1] > mod[2:])]
    if sommets.size == 0:
        return [], [], []
    sommets = sommets[np.argsort(mod[sommets])[::-1][:int(n_peaks)]]
    sommets = np.sort(sommets)

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

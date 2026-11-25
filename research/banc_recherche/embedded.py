"""Moteur temps réel embarquable — du modèle physique au STM32.

`hybrid.py` intègre les équations en RK4 : c'est juste, c'est lisible, et
c'est **trop cher** pour un microcontrôleur. Quatre évaluations de dérivée par
pas, huit pas par échantillon : 114 MFLOP/s par voix, soit une voix et demie
sur un STM32F4. Inutilisable en concert.

Ce module fait le même instrument autrement. La partie linéaire — le
résonateur, la dynamique de l'anche — devient un banc de **biquads**, qui est
la forme exacte d'un oscillateur amorti en temps discret. Seule la
non-linéarité (Bernoulli, frottement) reste évaluée pas à pas, et elle seule
a besoin d'être suréchantillonnée.

    32 MFLOP/s par voix  →  5 voix sur un F4, 15 sur un H7, 30 sur un H7 double cœur

Ce que ce moteur vise
---------------------
Ce que fait SWAM : un modèle piloté **en continu** par l'expression, pas un
sampler qui fond entre des couches. La différence s'entend sur tout ce qui
n'est pas une note tenue — l'attaque, le crescendo, la liaison, le vibrato
qui change le timbre et pas seulement la hauteur. Un sampler interpole entre
des instantanés ; un modèle traverse les états parce qu'il les calcule.

Mais **sans ordinateur**, sur la carte elle-même, pour le live.

Ce qui suit est donc écrit sous contrainte temps réel dure :

- `float32` partout (le FPU des Cortex-M4F/M7 est simple précision) ;
- aucune allocation dynamique, aucun `printf` dans le chemin audio ;
- de `libm`, uniquement `sqrtf` — qui est une instruction câblée (`VSQRT`) ;
- taille d'état fixe, connue à la compilation.

Pourquoi pas le Dream SAM5716
-----------------------------
Parce que ce n'est pas la bonne puce pour ça, et autant le dire tout de suite.
Les SAM5xxx sont des moteurs de **lecture d'échantillons** (wavetable) : leur
force est de lire beaucoup de voix depuis une ROM, pas d'exécuter une boucle
de rétroaction non linéaire échantillon par échantillon. Le jeu
d'instructions et la chaîne d'outils ne sont pas prévus pour du code
utilisateur arbitraire de ce genre.

Un STM32 + un codec audio, c'est la même boîte, le même prix, et ça calcule
vraiment un modèle physique.

⚠️ Le délai d'un échantillon interne
------------------------------------
Un modèle physique est une **boucle** : l'excitateur lit ce que le résonateur
présente, et le résonateur reçoit ce que l'excitateur produit, au même
instant. En temps discret, ça se mord la queue. On casse la boucle avec un
retard d'un échantillon *interne* — 5 µs à 192 kHz, très en dessous d'une
période, et c'est exactement ce que fait tout guide d'ondes numérique. La
conséquence est un léger décalage de la hauteur jouée, mesurable et
documenté, pas un bug caché.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .hybrid import (HybridVoice, SingleReedExciter, DoubleReedExciter,
                     FreeReedExciter, BowExciter, RHO)

#: familles reconnues par le moteur C (doit rester aligné sur l'enum généré)
FAMILY_SINGLE_REED = 0
FAMILY_FREE_REED = 1
FAMILY_BOW = 2


# =============================================================================
# Biquads
# =============================================================================

def biquad_bandpass(freq_hz, q, peak, fs):
    """Passe-bande à gain `peak` au sommet — un mode de résonance.

    Forme RBJ, normalisée `a0 = 1`. C'est l'équivalent discret exact, au
    gauchissement bilinéaire près, de `peak·(ω/Q)·s / (s² + (ω/Q)s + ω²)` :
    même sommet, même largeur, et zéro à fréquence nulle.
    """
    w0 = 2.0 * np.pi * float(freq_hz) / float(fs)
    if not (0.0 < w0 < np.pi):
        return None                       # au-delà de Nyquist : on laisse tomber
    alpha = np.sin(w0) / (2.0 * max(float(q), 1e-3))
    a0 = 1.0 + alpha
    g = float(peak)
    return (g * alpha / a0, 0.0, -g * alpha / a0,
            -2.0 * np.cos(w0) / a0, (1.0 - alpha) / a0)


def biquad_reed(freq_hz, q, dc_gain, fs):
    """Coefficients du biquad de l'anche pour le moteur C, `(b0, b1, b2, a1 + 2,
    1 - a2)` : `biquad_lowpass` en double précision, a1 et a2 rendus en écart à
    leurs limites (cf. `hv_reed`). `(0,) * 5` si la lame n'a pas de filtre."""
    c = biquad_lowpass(freq_hz, q, dc_gain, fs)
    if c is None:
        return (0.0,) * 5
    b0, b1, b2, a1, a2 = (float(x) for x in c)
    return (b0, b1, b2, a1 + 2.0, 1.0 - a2)


def biquad_lowpass(freq_hz, q, dc_gain, fs):
    """Passe-bas résonant de gain continu `dc_gain` — la dynamique d'une anche.

    L'anche suit la pression en basse fréquence (elle cède), résonne autour de
    sa fréquence propre, et ignore ce qui est plus aigu. Gain à fréquence
    nulle exactement `dc_gain`, ce qui fixe l'ouverture statique.
    """
    w0 = 2.0 * np.pi * float(freq_hz) / float(fs)
    if not (0.0 < w0 < np.pi):
        return None
    alpha = np.sin(w0) / (2.0 * max(float(q), 1e-3))
    cw = np.cos(w0)
    a0 = 1.0 + alpha
    g = float(dc_gain)
    b = g * (1.0 - cw) / 2.0
    return (b / a0, 2.0 * b / a0, b / a0, -2.0 * cw / a0, (1.0 - alpha) / a0)


#: sections d'ordre 2 au plus du filtre anti-repliement (ordre 10)
HV_MAX_AA = 5

#: bord de bande passante et début de bande atténuée du filtre anti-repliement,
#: en fraction de la cadence de sortie (20 kHz et 28 kHz à 48 kHz) : tout repli
#: reste au-dessus de 20 kHz.
AA_PASSANTE = 20000.0 / 48000.0
AA_COUPEE = 28000.0 / 48000.0
AA_LIMITE_PASSANTE = 18000.0 / 48000.0   # ondulation mesurée jusqu'ici
AA_ONDULATION_MAX_DB = 0.1
AA_ATTENUATION_MIN_DB = 80.0


def antirepliement_sos(oversample, samplerate):
    """Sections d'ordre 2 `(b0, b1, b2, a1, a2)` du filtre passe-bas qui
    précède la décimation de `oversample` pas vers `samplerate`. `[]` si
    `oversample == 1` (rien à replier).

    Elliptique, à la cadence interne ; le plus petit ordre de 6 à 10 qui tient,
    **vérifié sur la réponse** (`sosfreqz`) : ondulation de bande passante
    < 0,1 dB jusqu'à 18/48 de la cadence de sortie, atténuation >= 80 dB à
    partir de 28/48. Calculé à la construction, jamais dans le fil audio.
    Le gain est centré sur 0 dB (ondulation de +-0,025 dB).
    """
    from scipy import signal
    n = int(oversample)
    if n <= 1:
        return []
    fs_int = float(samplerate) * n
    rp = 0.05
    f_edge = AA_PASSANTE * float(samplerate)
    w = np.concatenate([
        np.linspace(1.0, AA_LIMITE_PASSANTE * samplerate, 400),
        np.linspace(AA_COUPEE * samplerate, fs_int / 2.0, 4000)])
    npass = 400
    derniere = None
    for ordre in range(6, 2 * HV_MAX_AA + 1):
        sos = signal.ellip(ordre, rp, AA_ATTENUATION_MIN_DB + 1.0, f_edge,
                           fs=fs_int, output='sos')
        sos = sos.copy()
        g = 10.0 ** (rp / 40.0)                    # centre l'ondulation sur 0 dB
        sos[0, :3] *= g
        _, h = signal.sosfreqz(sos, worN=w, fs=fs_int)
        db = 20.0 * np.log10(np.maximum(np.abs(h), 1e-30))
        derniere = sos
        if (np.max(np.abs(db[:npass])) < AA_ONDULATION_MAX_DB
                and np.max(db[npass:]) <= -AA_ATTENUATION_MIN_DB):
            break
    else:
        raise ValueError("filtre anti-repliement : aucun ordre <= %d ne tient "
                         "(suréchantillonnage %d)" % (2 * HV_MAX_AA, n))
    out = []
    for r in derniere:
        a0 = float(r[3])
        out.append(tuple(float(x) / a0 for x in (r[0], r[1], r[2], r[4], r[5])))
    return out


class BiquadBank:
    """Banc de biquads en forme directe II transposée.

    DF2T plutôt que DF1 : moins d'état, et surtout un meilleur comportement
    numérique en simple précision sur les résonances aiguës — ce qui compte
    quand la cible n'a que 24 bits de mantisse.
    """

    def __init__(self, coeffs):
        c = np.array([c for c in coeffs if c is not None], dtype='float64')
        self.n = len(c)
        if self.n:
            self.b0, self.b1, self.b2, self.a1, self.a2 = (c[:, i] for i in range(5))
        else:
            self.b0 = self.b1 = self.b2 = self.a1 = self.a2 = np.zeros(0)
        self.z1 = np.zeros(self.n)
        self.z2 = np.zeros(self.n)

    def reset(self):
        self.z1[:] = 0.0
        self.z2[:] = 0.0

    def step(self, x):
        """Avance d'un échantillon, renvoie la **somme** des sorties."""
        if not self.n:
            return 0.0
        y = self.b0 * x + self.z1
        self.z1 = self.b1 * x - self.a1 * y + self.z2
        self.z2 = self.b2 * x - self.a2 * y
        return float(y.sum())


# =============================================================================
# Voix temps réel
# =============================================================================

@dataclass
class RealtimeParams:
    """Tout ce que le moteur C a besoin de savoir. Rien de plus."""
    name: str = "voix"
    family: int = FAMILY_SINGLE_REED
    samplerate: float = 48000.0
    oversample: int = 4

    # résonateur
    modes: list = field(default_factory=list)      # [(f, q, peak), ...]
    compliance: float = 0.0                        # 0 = pas de cavité

    # excitateur — anches
    rest_opening_m: float = 4.0e-4
    width_m: float = 1.3e-2
    closing_pressure_pa: float = 4000.0
    reed_freq_hz: float = 2500.0
    reed_q: float = 4.0
    vena_contracta: float = 0.6
    #: pression de transition entre écoulement visqueux (linéaire) et
    #: inertiel (Bernoulli). Quelques pascals : négligeable pour le son,
    #: mais elle borne la pente du débit en zéro et laisse les notes
    #: s'éteindre.
    visc_pa: float = 1.0
    max_open_m: float = 0.0                        # >0 : anche libre (saturation)
    leak_m: float = 0.0
    #: loi de passage de l'anche libre (cf. `hybrid.FreeReedExciter`) :
    #: `LOI_TRAVERSANTE` (défaut : la languette traverse sa fente, section
    #: `largeur × √(gap² + jeu²)`, sans butée haute) ou `LOI_ECRETEE`
    #: (`clip(y + h₀, fuite, max_open)`, l'ancienne, à demander par son nom).
    #: Plaque, lame et jeu ne servent qu'à la première ; la levée au repos est
    #: `rest_opening_m`.
    loi: str = 'traversante'
    plate_m: float = 0.0
    tongue_m: float = 0.0
    clearance_m: float = 0.0
    reed_area_m2: float = 0.0
    source_impedance: float = 0.0                  # 0 = source parfaite
    #: surface de force de la lame, `largeur × longueur de la lame` (celle qui
    #: sert à `closing_pressure_pa` : `FreeReedExciter.force_area_m2`).
    force_area_m2: float = 0.0
    #: débit déplacé par la lame elle-même (anche libre, sortie rayonnée) :
    #: facteur F sans unité, `S_eff = F × force_area_m2`, et le débit rayonné
    #: est le débit de fente **moins** `S_eff × vitesse de la lame` dans le
    #: signe du débit net injecté (c'est le débit sortant de la chambre plus
    #: `S_eff × vitesse`, y > 0 ouvrant la fente). 0 (défaut) : le son d'avant,
    #: à l'échantillon près. Le bilan de la chambre et la lame ne changent pas.
    pompe: float = 0.0

    # excitateur — archet
    mu_static: float = 0.8
    mu_dynamic: float = 0.3
    v_char: float = 0.05
    bow_speed: float = 0.2

    #: ce que la voix sort : `SORTIE_RAYONNEE` (dérivée du débit net, ce que
    #: `hybrid.VoiceResult.radiated` appelle le rayonnement) ou
    #: `SORTIE_PRESSION` (pression de la chambre, l'ancienne sortie). `None` :
    #: le défaut de la famille (`sortie_par_defaut`).
    sortie: str = None

    @property
    def fs_internal(self):
        return self.samplerate * self.oversample

    @property
    def pump_area_m2(self):
        """`S_eff = F × largeur × longueur de la lame`, en m²."""
        return float(self.pompe) * float(self.force_area_m2)

    @property
    def sections_antirepliement(self):
        """Filtre passe-bas avant décimation (`antirepliement_sos`)."""
        return antirepliement_sos(self.oversample, self.samplerate)

    @property
    def sortie_effective(self):
        return self.sortie or sortie_par_defaut(self.family)


#: Lois de passage de l'anche libre (code C : 0 et 1).
LOI_ECRETEE = 'ecretee'
LOI_TRAVERSANTE = 'traversante'


def loi_c(params):
    """Numéro de la loi pour le C : 1 traversante (défaut de `RealtimeParams`),
    0 écrêtée (à demander par son nom). Le C reçoit toujours le numéro écrit
    ici, jamais un champ laissé à zéro."""
    return 1 if params.loi == LOI_TRAVERSANTE else 0


#: Sorties d'une voix. La pression de la chambre est un signal **intégré** : la
#: chambre intègre le débit, donc elle coupe les aigus (partiel 8 de la la 220
#: à -43,5 dB), et elle porte la pression continue du soufflet (centaines de
#: Pa, qui s'additionnent d'une voix à l'autre). Ce qu'un instrument rayonne
#: est la dérivée du débit net : celle de `hybrid.VoiceResult.radiated`.
SORTIE_RAYONNEE = 'rayonnee'
SORTIE_PRESSION = 'pression'


def sortie_par_defaut(family):
    """Sortie par défaut : rayonnée pour l'anche libre (l'accordéon).

    Les autres familles gardent la pression de la perce ou la vitesse de
    corde : le défaut n'a été prouvé (audit du 23/11/2026) que sur l'anche
    libre, et leurs tests et leurs échelles de sortie lisent cette grandeur.
    Elles peuvent la demander : `RealtimeParams(sortie=SORTIE_RAYONNEE)`.
    """
    return SORTIE_RAYONNEE if family == FAMILY_FREE_REED else SORTIE_PRESSION


#: suréchantillonnage minimal par famille, **mesuré** et non supposé.
#: L'archet en demande deux fois plus que l'anche : sa courbe de frottement
#: varie sur 0,05 m/s alors que la corde atteint 1,4 m/s, soit une pente bien
#: plus raide que Bernoulli. À K=4 le violon décroche et part à 91 Hz au lieu
#: de 440 ; à K=8 il retrouve 437,6 Hz.
OVERSAMPLE_MIN = {FAMILY_SINGLE_REED: 4, FAMILY_FREE_REED: 4, FAMILY_BOW: 8}


def params_from_voice(voice: HybridVoice, samplerate=48000.0, oversample=None,
                      name=None, sortie=None, pompe=0.0):
    """Traduit une `HybridVoice` continue en jeu de paramètres embarquables.

    `oversample=None` prend le minimum sûr de la famille (`OVERSAMPLE_MIN`).
    Ce n'est pas de la prudence : en dessous, la boucle décroche et sort une
    hauteur fausse, pas un son dégradé.

    Pourquoi suréchantillonner plutôt que résoudre le couplage implicitement
    (Newton) : en audio temps réel, un coût **fixe** par échantillon vaut
    mieux qu'un coût moyen plus bas mais variable. Un nombre d'itérations qui
    dépend du signal, c'est une échéance qu'on rate un jour de concert.

    `sortie` : `SORTIE_RAYONNEE` ou `SORTIE_PRESSION` (défaut de la famille,
    cf. `sortie_par_defaut`).

    `pompe` : facteur F du débit déplacé par la lame (`RealtimeParams.pompe`),
    0 par défaut. Il ne joue que pour l'anche libre en sortie rayonnée.
    """
    ex = voice.exciter
    fam = (FAMILY_BOW if isinstance(ex, BowExciter)
           else FAMILY_FREE_REED if isinstance(ex, FreeReedExciter)
           else FAMILY_SINGLE_REED)
    if oversample is None:
        oversample = OVERSAMPLE_MIN[fam]
    p = RealtimeParams(name=name or voice.name or "voix",
                       samplerate=float(samplerate), oversample=int(oversample),
                       modes=[(m.freq_hz, m.q, m.peak) for m in voice.resonator.modes],
                       compliance=float(voice.resonator.compliance or 0.0),
                       sortie=sortie)

    if isinstance(ex, (SingleReedExciter, DoubleReedExciter)):
        p.family = FAMILY_SINGLE_REED
        p.rest_opening_m = ex.rest_opening_m
        p.width_m = ex.width_m
        p.closing_pressure_pa = ex.closing_pressure_pa
        p.reed_freq_hz = ex.freq_hz
        p.reed_q = ex.q
        p.vena_contracta = ex.vena_contracta
    elif isinstance(ex, FreeReedExciter):
        p.family = FAMILY_FREE_REED
        p.rest_opening_m = ex.rest_offset_m
        p.width_m = ex.width_m
        p.reed_freq_hz = ex.freq_hz
        p.reed_q = ex.q
        p.vena_contracta = ex.vena_contracta
        p.max_open_m = ex.max_open_m
        p.leak_m = ex.leak_m
        p.loi = ex.loi
        p.plate_m = ex.plate_m
        p.tongue_m = ex.tongue_m
        p.clearance_m = ex.clearance_m
        p.reed_area_m2 = ex.area_m2
        p.force_area_m2 = float(ex.force_area_m2)
        p.pompe = float(pompe)
        p.source_impedance = (ex.source_impedance
                              if np.isfinite(ex.source_impedance) else 0.0)
        # raideur équivalente : la pression qui déplacerait la languette de h₀
        k = ex.mass_kg * (2 * np.pi * ex.freq_hz) ** 2
        p.closing_pressure_pa = float(k * ex.rest_offset_m / ex.force_area_m2)
    elif isinstance(ex, BowExciter):
        p.family = FAMILY_BOW
        p.mu_static, p.mu_dynamic = ex.mu_static, ex.mu_dynamic
        p.v_char, p.bow_speed = ex.v_char, ex.bow_speed
    else:
        raise TypeError(f"excitateur non embarquable : {type(ex).__name__}")
    return p


class BiquadCascade:
    """Cascade de biquads en forme directe II transposée (le filtre
    anti-repliement). Vide : identité."""

    def __init__(self, coeffs):
        self.c = [tuple(float(x) for x in c) for c in coeffs]
        self.z = [[0.0, 0.0] for _ in self.c]

    def reset(self):
        for z in self.z:
            z[0] = z[1] = 0.0

    def step(self, x):
        for (b0, b1, b2, a1, a2), z in zip(self.c, self.z):
            y = b0 * x + z[0]
            z[0] = b1 * x - a1 * y + z[1]
            z[1] = b2 * x - a2 * y
            x = y
        return x


class RealtimeVoice:
    """Implémentation de référence, **identique au C** pas pour pas.

    Existe pour qu'on puisse vérifier le portage sans carte sous la main : si
    le C et ce code divergent, c'est le portage qui est faux, pas la physique.
    Elle n'est pas rapide en Python et n'a pas à l'être — c'est le C qui joue.
    """

    def __init__(self, params: RealtimeParams):
        self.p = params
        fs = params.fs_internal
        self.res = BiquadBank([biquad_bandpass(f, q, pk, fs)
                               for f, q, pk in params.modes])

        if params.family == FAMILY_BOW:
            self.reed = BiquadBank([])
        else:
            # l'anche cède à la pression : gain continu = h₀ / p_fermeture,
            # signé selon le sens dans lequel la pression la pousse
            sign = -1.0 if params.family == FAMILY_SINGLE_REED else +1.0
            self.reed = BiquadBank([biquad_lowpass(
                params.reed_freq_hz, params.reed_q,
                sign * params.rest_opening_m / params.closing_pressure_pa, fs)])
        self.aa = BiquadCascade(params.sections_antirepliement)
        self.reset()

    def reset(self):
        self.res.reset()
        self.reed.reset()
        self.aa.reset()
        self.response = 0.0
        self.cavity = 0.0
        self.drive = 0.0
        self._kick = True
        self._net_prec = None       # débit net au dernier échantillon de sortie
        self._y_prec = None         # position de la lame au pas précédent
        self._y_anche = 0.0         # position de la lame au pas courant
        self.valve = 1.0            # soupape de clavier : 1 ouverte, 0 fermée
        self._valve_de = self._valve_a = 1.0
        self._valve_k = self._valve_n = 0

    def valve_start(self, de, a, n):
        """Rampe de la soupape de `de` à `a` en `n` échantillons de sortie, en
        demi-cosinus (`hv_valve_start`). `n` <= 0 : saut."""
        self._valve_de, self._valve_a = float(de), float(a)
        self._valve_k, self._valve_n = 0, int(n)
        self.valve = float(de) if n > 0 else float(a)

    def _valve_pas(self):
        if self._valve_k < self._valve_n:
            self._valve_k += 1
            if self._valve_k == self._valve_n:
                self.valve = self._valve_a
            else:
                self.valve = self._valve_de + (self._valve_a - self._valve_de)                     * 0.5 * (1.0 - np.cos(np.pi * self._valve_k / self._valve_n))

    # -- la non-linéarité, la seule chose qui coûte --------------------------
    def _exciter(self, response, level):
        p = self.p
        if p.family == FAMILY_BOW:
            v_rel = p.bow_speed - response
            mu = (p.mu_dynamic + (p.mu_static - p.mu_dynamic) /
                  (1.0 + abs(v_rel) / p.v_char))
            return level * np.sign(v_rel) * mu, float('nan')

        if p.family == FAMILY_SINGLE_REED:
            dp = level - response
            y = self.reed.step(dp)
            h = max(p.rest_opening_m + y, 0.0)
            q = (p.vena_contracta * p.width_m * h * np.sqrt(2.0 / RHO)
                 * dp / np.sqrt(abs(dp) + p.visc_pa))
            return q, h

        # anche libre : la pression l'ouvre, la soupape interdit le retour
        y = self.reed.step(response)
        self._y_anche = y
        z = p.rest_opening_m + y
        if p.loi == LOI_TRAVERSANTE:
            # la languette traverse sa fente (`coupled_reeds.ReedSetting.gap`,
            # lue dans le sens du moteur) ; seul le jeu passe quand gap = 0
            g = z if z > 0.0 else max(-z - (p.tongue_m + p.plate_m), 0.0)
            h = np.sqrt(g * g + p.clearance_m * p.clearance_m)
        else:
            h = min(max(z, p.leak_m), p.max_open_m)
        q_out = (p.vena_contracta * p.width_m * h * np.sqrt(2.0 / RHO)
                 * response / np.sqrt(response + p.visc_pa)) if response > 0.0 else 0.0
        q_src = level
        if p.source_impedance > 0.0:
            q_src -= response / p.source_impedance
        q_src *= self.valve            # la soupape ferme apport ET fuite
        return q_src - q_out, h

    def render(self, n_samples, level, out_opening=False, sortie=None):
        """Rend `n_samples` à la commande `level`. Renvoie `(audio, ouverture)`.

        `sortie` choisit le signal (défaut : `params.sortie_effective`).

        - `SORTIE_RAYONNEE` : la dérivée du débit net injecté dans le
          résonateur, `d(drive)/dt`, comme `hybrid.VoiceResult.radiated`.
          Calculée à chaque pas suréchantillonné (`Δdrive × fs_interne`), puis
          passée dans le **filtre elliptique anti-repliement**
          (`antirepliement_sos`), dont on ne garde qu'un échantillon sur
          `oversample`. Les partiels au-dessus de la moitié de la cadence de
          sortie ne se replient plus dans la bande. Le premier pas après
          `reset` vaut 0 (pas de débit précédent).
        - `SORTIE_PRESSION` : la pression de la chambre (anche libre, tuyau)
          ou la vitesse de corde (archet), l'ancienne sortie, filtrée et
          décimée de la même façon.
        Suréchantillonnage 1 : pas de filtre, sortie au pas interne.
        """
        p = self.p
        sortie = sortie or p.sortie_effective
        rayonnee = sortie == SORTIE_RAYONNEE
        n = int(n_samples)
        audio = np.zeros(n)
        opening = np.zeros(n) if out_opening else None
        fs_int = p.fs_internal

        for i in range(n):
            h = float('nan')
            self._valve_pas()
            for _ in range(p.oversample):
                if self._kick:
                    self.response += 1e-6      # amorce : l'équilibre est un point fixe
                    self._kick = False
                drive, h = self._exciter(self.response, level)
                self.drive = drive
                acoustic = self.res.step(drive)
                if p.compliance > 0.0:
                    self.cavity += drive / (p.compliance * p.fs_internal)
                    self.cavity *= 0.99999      # fuite lente : évite la dérive continue
                self.response = acoustic + self.cavity
                src = drive
                if p.family == FAMILY_FREE_REED:
                    # vitesse de la lame : différence arrière au pas interne
                    if self._y_prec is None:
                        self._y_prec = self._y_anche
                    if rayonnee and p.pump_area_m2 != 0.0:
                        src = drive - p.pump_area_m2 * (
                            self._y_anche - self._y_prec) * fs_int
                    self._y_prec = self._y_anche
                if rayonnee:
                    if self._net_prec is None:
                        self._net_prec = src
                    x = (src - self._net_prec) * fs_int
                    self._net_prec = src
                else:
                    x = self.response
                y = self.aa.step(x)
            audio[i] = y
            if out_opening:
                opening[i] = h
        return audio, opening


def cpu_estimate(params: RealtimeParams, mcu_mflops=480.0):
    """Coût du moteur, et combien de voix la carte tient.

    `mcu_mflops` : ~168 pour un STM32F4 à 168 MHz, ~480 pour un H7 à 480 MHz
    (un FMA simple précision par cycle). Estimation en comptant les flops, donc
    optimiste de 20 à 40 % — les accès mémoire et la boucle comptent aussi.
    À confronter à un vrai profilage sur carte, comme tout le reste.
    """
    n_aa = len(params.sections_antirepliement)     # filtre avant décimation
    n_biq = len(params.modes) + (0 if params.family == FAMILY_BOW else 1) + n_aa
    per_internal = n_biq * 9 + 15          # biquads + non-linéarité
    mflops = per_internal * params.fs_internal / 1e6
    return {
        'biquads': n_biq,
        'fs_internal_hz': params.fs_internal,
        'mflops_per_voice': float(mflops),
        'voices': float(mcu_mflops / mflops) if mflops > 0 else float('inf'),
        'state_bytes': int(4 * (2 * n_biq + 4)),
    }


# =============================================================================
# Génération du C embarqué
# =============================================================================

def _f(x):
    """Littéral `float` C valide.

    Deux pièges qui ne se voient qu'à la compilation : `nan`/`inf` ne sont pas
    des littéraux C, et `%g` rend `0` pour zéro — or `0f` n'est pas un
    flottant en C, il lui faut un point ou un exposant.
    """
    v = float(x)
    if not np.isfinite(v):
        v = 0.0
    out = "{:.9g}".format(v)
    if "e" not in out and "E" not in out and "." not in out:
        out += ".0"
    return out + "f"


def _d(x):
    """Littéral `double` C (sans suffixe), 17 chiffres : aller-retour exact."""
    v = float(x)
    if not np.isfinite(v):
        v = 0.0
    out = "{:.17g}".format(v)
    if "e" not in out and "E" not in out and "." not in out:
        out += ".0"
    return out


def _ident(name):
    """Identifiant C **ASCII** dérivé d'un nom d'instrument.

    `str.isalnum()` accepte les accents : « accordéon » passerait tel quel et
    donnerait un symbole que tous les compilateurs n'acceptent pas. On
    translittère donc plutôt que de remplacer — « accordéon » devient
    `accordeon` et non `accord_on`.
    """
    import unicodedata
    plat = unicodedata.normalize("NFKD", name or "voice")
    plat = "".join(c for c in plat if not unicodedata.combining(c))
    out = "".join(c if (c.isascii() and c.isalnum()) else "_" for c in plat)
    out = out.strip("_").lower() or "voice"
    return ("v_" + out) if out[0].isdigit() else out


C_ENGINE_H = r'''/* Moteur de modèle physique hybride — temps réel, embarquable.
 *
 * Généré par banc_recherche.embedded. Le moteur est FIXE : seules les tables
 * de paramètres changent d'un instrument à l'autre. Un seul code à relire.
 *
 * Contraintes tenues :
 *   - float32 seulement (FPU simple précision des Cortex-M4F / M7) ;
 *   - aucune allocation, aucun appel bloquant, taille d'état fixe ;
 *   - de libm, uniquement sqrtf (instruction VSQRT, ~14 cycles).
 *
 * Usage :
 *     static hv_state st;
 *     hv_reset(&st);
 *     hv_render(&clarinette_params, &st, pression_bouche, bloc, 64);
 */
#ifndef HYBRID_VOICE_H
#define HYBRID_VOICE_H

#include <stdint.h>

#ifndef HV_MAX_MODES
#define HV_MAX_MODES 24
#endif

/* Sections d'ordre 2 au plus du filtre anti-repliement (ordre 10). */
#ifndef HV_MAX_AA
#define HV_MAX_AA 5
#endif

#define HV_FAMILY_SINGLE_REED 0
#define HV_FAMILY_FREE_REED   1
#define HV_FAMILY_BOW         2

/* Sortie de hv_render. 0 (défaut d'une structure remise à zéro) : le
 * rayonnement, dérivée du débit net injecté dans le résonateur, calculée à
 * chaque pas interne. 1 : la pression de la chambre. Dans les deux cas le
 * signal passe par le filtre anti-repliement (aa) avant qu'on garde un pas
 * interne sur `oversample`. */
#define HV_OUT_RADIATED 0
#define HV_OUT_PRESSURE 1

/* Loi de passage de l'anche libre. Le défaut est la loi traversante (1) : la
 * languette traverse sa fente, section width*sqrt(gap^2 + clear^2), sans butée
 * haute ; le numéro est toujours écrit par le Python (`loi_c`), jamais laissé
 * à zéro dans une structure remise à zéro (plaque, lame et jeu seraient nuls).
 * 0 : ouverture écrêtée clip(h0 + y, leak, max_open), à demander par son nom. */
#define HV_LAW_CLIPPED 0
#define HV_LAW_THROUGH 1

typedef struct { float b0, b1, b2, a1, a2; } hv_biquad;
/* Biquad de l'anche : a1 et a2 sont stockés en écart à leurs valeurs limites,
 * da1 = a1 + 2 et ea2 = 1 - a2. Une lame grave (quelques centaines de Hz à
 * 192 kHz) a ses pôles tout près de z = 1 : a1 vaut -1,9999 et a2 0,9999, et
 * le pas de la simple précision (1,2e-7 sur a1) y fait des marches de 1 à 8
 * cents sur la fréquence de la lame. Les écarts, eux, gardent toute leur
 * précision.
 * Coefficients ET états du biquad de l'anche sont en double (hv_bqstate_d) :
 * en float, l'arrondi des états faisait à 192 kHz 0,03 à 0,1 cent de marche
 * irrégulière sur la hauteur et 3 cents d'écart à 290 Pa (note 45) ; en
 * double, le résidu tombe à 0,0023 cent (mesuré, essai_C_ablation.py). Le
 * reste du moteur reste en float.
 * Coût mesuré sur le PC de développement (10 s de voix, bloc de 512, 4x
 * suréchantillonné, 9 rendus, notes 45 et 69) : médiane 0,117 s avant, 0,115 s
 * après (note 45) ; 0,111 s avant et après (note 69) : indiscernable du bruit
 * de mesure. Sur une carte embarquée le coût est NON MESURÉ : le FPU simple
 * précision d'un Cortex-M4F/M7 n'a pas de double câblé (le double y est
 * émulé, donc nettement plus lent) ; à mesurer sur la carte avant de retenir
 * cette solution pour elle. */
typedef struct { double b0, b1, b2, da1, ea2; } hv_reed;
typedef struct { float z1, z2; } hv_bqstate;
typedef struct { double z1, z2; } hv_bqstate_d;

typedef struct {
    int   family;
    int   n_modes;
    int   oversample;

    const hv_biquad *modes;      /* n_modes résonances */
    hv_reed reed;                /* dynamique de l'anche (inutilisé : archet) */

    /* anches */
    float rest_opening;          /* h0, m */
    float width;                 /* m */
    float vena;                  /* coefficient de contraction */
    float max_open;              /* m, anche libre : saturation d'ouverture */
    float leak;                  /* m, anche libre : fuite résiduelle */
    float src_admit;             /* 1/R du soufflet, 0 = source parfaite */
    float flow_gain;             /* vena*width*sqrt(2/rho), précalculé */
    float visc_pa;               /* pression de transition visqueux/inertiel */

    /* archet */
    float mu_s, mu_d, v_char, bow_speed;

    /* cavité fermée (accordéon) : 0 si perce ouverte */
    float cavity_gain;           /* 1/(C*fs_interne) */
    float cavity_leak;

    /* sortie */
    int   out_mode;              /* HV_OUT_RADIATED ou HV_OUT_PRESSURE */
    float fs_out;                /* cadence de sortie, Hz (fs_interne/oversample) */

    /* anche libre, loi traversante (rest_opening = levée au repos) */
    int   free_law;              /* HV_LAW_CLIPPED ou HV_LAW_THROUGH */
    float plate;                 /* m, épaisseur de la plaque */
    float tongue;                /* m, épaisseur de la lame au bout */
    float clear;                 /* m, jeu latéral languette/fente */

    /* débit déplacé par la lame : S_eff = F * largeur * longueur de lame, m2.
     * 0 (défaut d'une structure remise à zéro) : pas de pompe. Anche libre,
     * sortie rayonnée seulement. */
    float pump_area;

    /* filtre anti-repliement avant décimation : n_aa sections d'ordre 2
     * (elliptique, calculé en Python à la construction). n_aa = 0 : aucun
     * filtre (oversample = 1). */
    int   n_aa;
    const hv_biquad *aa;
} hv_params;

typedef struct {
    hv_bqstate z[HV_MAX_MODES];
    hv_bqstate_d reed_z;         /* double : cf. hv_reed */
    hv_bqstate aa_z[HV_MAX_AA];  /* état du filtre anti-repliement */
    float response;
    float cavity;
    int   kicked;
    float net_prec;              /* débit net au dernier pas interne */
    int   net_ok;                /* 0 : pas encore de débit précédent */
    float y_prev;                /* position de la lame au pas précédent */
    int   y_ok;                  /* 0 : pas encore de position précédente */

    /* Soupape de clavier (anche libre) : conductance en série avec le passage
     * de la source, G(t) = src_admit * valve, valve de 0 (fermée : la chambre
     * est isolée) à 1 (ouverte). Elle multiplie l'apport P_s*G ET la fuite
     * -p*G, c'est-à-dire tout le débit de la source. Au repos (après
     * hv_reset) valve = 1 : le son d'avant, à l'échantillon. */
    float valve;                 /* valve au dernier échantillon de sortie */
    float valve_from, valve_to;  /* début et fin de la rampe en cours */
    float valve_c, valve_s;      /* cos et sin de pi*k/n, par rotation */
    float valve_dc, valve_ds;    /* cos et sin du pas pi/n */
    int   valve_left;            /* échantillons de sortie restant à la rampe, 0 = au repos */
} hv_state;

void hv_reset(hv_state *st);
/* Lance la rampe de la soupape de `from` à `to` (0 à 1) en `n` échantillons de
 * sortie, en demi-cosinus : valve = from + (to-from)*(1-cos(pi*k/n))/2. `n` <= 0 :
 * saut immédiat. Appelée aux événements de touche, jamais dans le fil audio
 * (elle seule utilise cosf et sinf). */
void hv_valve_start(hv_state *st, float from, float to, int n);
void hv_render(const hv_params *p, hv_state *st, float level,
               float *out, int n);

#endif /* HYBRID_VOICE_H */
'''

C_ENGINE_C = r'''#include "hybrid_voice.h"
#include <math.h>

/* Biquad en forme directe II transposée : deux états, bon conditionnement
 * en simple précision sur les résonances aiguës. */
static inline float bq_step(const hv_biquad *c, hv_bqstate *s, float x)
{
    const float y = c->b0 * x + s->z1;
    s->z1 = c->b1 * x - c->a1 * y + s->z2;
    s->z2 = c->b2 * x - c->a2 * y;
    return y;
}

/* Le biquad de l'anche, même forme que bq_step, mais a1 = da1 - 2 et
 * a2 = 1 - ea2 : -a1*y = 2*y - da1*y et -a2*y = -y + ea2*y. */
static inline double reed_step(const hv_reed *c, hv_bqstate_d *s, float x)
{
    const double y = c->b0 * x + s->z1;
    s->z1 = c->b1 * x + 2.0 * y - c->da1 * y + s->z2;
    s->z2 = c->b2 * x - y + c->ea2 * y;
    return y;
}

void hv_reset(hv_state *st)
{
    int i;
    for (i = 0; i < HV_MAX_MODES; ++i) { st->z[i].z1 = 0.0f; st->z[i].z2 = 0.0f; }
    st->reed_z.z1 = 0.0f;
    st->reed_z.z2 = 0.0f;
    for (i = 0; i < HV_MAX_AA; ++i) { st->aa_z[i].z1 = 0.0f; st->aa_z[i].z2 = 0.0f; }
    st->response = 0.0f;
    st->cavity = 0.0f;
    st->kicked = 0;
    st->net_prec = 0.0f;
    st->net_ok = 0;
    st->y_prev = 0.0f;
    st->y_ok = 0;
    st->valve = st->valve_from = st->valve_to = 1.0f;
    st->valve_c = 1.0f;
    st->valve_s = st->valve_dc = st->valve_ds = 0.0f;
    st->valve_left = 0;
}

void hv_valve_start(hv_state *st, float from, float to, int n)
{
    st->valve_from = from;
    st->valve_to = to;
    if (n <= 0) {
        st->valve = to;
        st->valve_left = 0;
        return;
    }
    st->valve = from;
    st->valve_left = n;
    st->valve_c = 1.0f;
    st->valve_s = 0.0f;
    st->valve_dc = cosf(3.14159265358979f / (float)n);
    st->valve_ds = sinf(3.14159265358979f / (float)n);
}

/* La soupape avance d'un échantillon de sortie : rotation de (c, s) d'un pas. */
static inline void hv_valve_step(hv_state *st)
{
    if (st->valve_left > 0) {
        const float c = st->valve_c * st->valve_dc - st->valve_s * st->valve_ds;
        st->valve_s = st->valve_s * st->valve_dc + st->valve_c * st->valve_ds;
        st->valve_c = c;
        if (--st->valve_left == 0)
            st->valve = st->valve_to;
        else
            st->valve = st->valve_from
                      + (st->valve_to - st->valve_from) * 0.5f * (1.0f - c);
    }
}

/* La non-linéarité : le seul endroit où l'instrument cesse d'être un filtre. */
static inline float hv_exciter(const hv_params *p, hv_state *st,
                               float response, float level, float *y_lame)
{
    *y_lame = 0.0f;
    if (p->family == HV_FAMILY_BOW) {
        const float v_rel = p->bow_speed - response;
        const float av = v_rel < 0.0f ? -v_rel : v_rel;
        const float mu = p->mu_d + (p->mu_s - p->mu_d) / (1.0f + av / p->v_char);
        return (v_rel < 0.0f ? -level : level) * mu;
    }

    if (p->family == HV_FAMILY_SINGLE_REED) {
        const float dp = level - response;
        const float y  = (float)reed_step(&p->reed, &st->reed_z, dp);
        float h = p->rest_opening + y;
        float adp;
        if (h < 0.0f) h = 0.0f;              /* l'anche claque sur la table */
        adp = dp < 0.0f ? -dp : dp;
        /* Bernoulli régularisé : dp/sqrt(|dp| + visc). Au-dessus de visc on
         * retrouve sign(dp)*sqrt(|dp|) ; en dessous la loi devient linéaire,
         * comme un écoulement visqueux. Sans cela la pente de sqrt est
         * INFINIE en zéro, et le modèle s'auto-entretient à pression nulle :
         * une note relâchée ne s'éteint jamais. */
        return p->flow_gain * h * dp / sqrtf(adp + p->visc_pa);
    }

    {   /* anche libre : la pression l'ouvre, la soupape interdit le retour */
        const float y = (float)reed_step(&p->reed, &st->reed_z, response);
        const float z = p->rest_opening + y;
        float h, q_out = 0.0f, q_src = level;
        if (p->free_law == HV_LAW_THROUGH) {
            /* la languette traverse sa fente : seul le jeu passe si gap = 0 */
            float g = z;
            if (z <= 0.0f) {
                g = -z - (p->tongue + p->plate);
                if (g < 0.0f) g = 0.0f;
            }
            h = sqrtf(g * g + p->clear * p->clear);
        } else {
            h = z;
            if (h < p->leak)     h = p->leak;
            if (h > p->max_open) h = p->max_open;
        }
        if (response > 0.0f)
            q_out = p->flow_gain * h * response / sqrtf(response + p->visc_pa);
        if (p->src_admit > 0.0f) q_src -= response * p->src_admit;
        q_src *= st->valve;      /* la soupape ferme apport ET fuite */
        *y_lame = y;
        return q_src - q_out;
    }
}

void hv_render(const hv_params *p, hv_state *st, float level,
               float *out, int n)
{
    int i, k, m;
    const float fs_int = p->fs_out * (float)p->oversample;
    for (i = 0; i < n; ++i) {
        float y = 0.0f;
        hv_valve_step(st);
        for (k = 0; k < p->oversample; ++k) {
            float acoustic = 0.0f, drive, x, y_lame, src;
            if (!st->kicked) { st->response += 1e-6f; st->kicked = 1; }
            drive = hv_exciter(p, st, st->response, level, &y_lame);
            if (p->family == HV_FAMILY_FREE_REED && !st->y_ok) {
                st->y_prev = y_lame;         /* vitesse nulle au premier pas */
                st->y_ok = 1;
            }
            for (m = 0; m < p->n_modes; ++m)
                acoustic += bq_step(&p->modes[m], &st->z[m], drive);
            if (p->cavity_gain > 0.0f) {
                st->cavity = (st->cavity + drive * p->cavity_gain) * p->cavity_leak;
            }
            st->response = acoustic + st->cavity;
            if (p->out_mode == HV_OUT_PRESSURE) {
                x = st->response;
            } else {
                /* dérivée du débit net au pas interne ; 0 au premier pas. Le
                 * débit déplacé par la lame (S_eff * vitesse) s'y retranche
                 * avant la dérivation : même signe que le débit net. */
                src = drive;
                if (p->family == HV_FAMILY_FREE_REED && p->pump_area != 0.0f)
                    src = drive - p->pump_area * (y_lame - st->y_prev) * fs_int;
                if (!st->net_ok) { st->net_prec = src; st->net_ok = 1; }
                x = (src - st->net_prec) * fs_int;
                st->net_prec = src;
            }
            st->y_prev = y_lame;
            /* passe-bas avant décimation : on ne garde que le dernier pas */
            for (m = 0; m < p->n_aa; ++m)
                x = bq_step(&p->aa[m], &st->aa_z[m], x);
            y = x;
        }
        out[i] = y;
    }
}
'''


def to_c_engine():
    """Le moteur C, identique pour tous les instruments.

    Renvoie `{'hybrid_voice.h': ..., 'hybrid_voice.c': ...}`. Ces deux
    fichiers ne dépendent d'aucun instrument : on les relit une fois, on les
    porte une fois, et chaque instrument n'est plus qu'une table.
    """
    return {'hybrid_voice.h': C_ENGINE_H, 'hybrid_voice.c': C_ENGINE_C}


def to_c_params(params: RealtimeParams, ident=None):
    """Table de paramètres C pour un instrument, prête à `#include`."""
    ident = ident or _ident(params.name)
    fs = params.fs_internal
    coeffs = [biquad_bandpass(f, q, pk, fs) for f, q, pk in params.modes]
    coeffs = [c for c in coeffs if c is not None]

    if params.family == FAMILY_BOW:
        reed = (0.0, 0.0, 0.0, 0.0, 0.0)
    else:
        sign = -1.0 if params.family == FAMILY_SINGLE_REED else +1.0
        reed = biquad_reed(params.reed_freq_hz, params.reed_q,
                           sign * params.rest_opening_m /
                           params.closing_pressure_pa, fs)

    L = [f"/* {params.name} — table générée par banc_recherche.embedded.",
         " * NE PAS ÉDITER : régénérer depuis le modèle Python.",
         f" * {len(coeffs)} modes · suréchantillonnage {params.oversample}"
         f" · {params.samplerate:.0f} Hz (interne {fs:.0f} Hz)",
         " */",
         f"#ifndef {ident.upper()}_PARAMS_H",
         f"#define {ident.upper()}_PARAMS_H", "",
         '#include "hybrid_voice.h"', "",
         f"static const hv_biquad {ident}_modes[{max(len(coeffs), 1)}] = {{"]
    for (b0, b1, b2, a1, a2), (f, q, pk) in zip(coeffs, params.modes):
        L.append(f"    {{{_f(b0)}, {_f(b1)}, {_f(b2)}, {_f(a1)}, {_f(a2)}}},"
                 f"  /* {f:8.1f} Hz  Q={q:.0f} */")
    if not coeffs:
        L.append("    {0.0f, 0.0f, 0.0f, 0.0f, 0.0f},")
    L.append("};")
    L.append("")
    aa = params.sections_antirepliement
    L.append(f"static const hv_biquad {ident}_aa[{max(len(aa), 1)}] = {{"
             "  /* filtre anti-repliement */")
    for b0, b1, b2, a1, a2 in aa:
        L.append(f"    {{{_f(b0)}, {_f(b1)}, {_f(b2)}, {_f(a1)}, {_f(a2)}}},")
    if not aa:
        L.append("    {0.0f, 0.0f, 0.0f, 0.0f, 0.0f},")
    L.append("};")
    L.append("")

    flow_gain = params.vena_contracta * params.width_m * np.sqrt(2.0 / RHO)
    cavity_gain = (1.0 / (params.compliance * fs)) if params.compliance > 0 else 0.0
    admit = (1.0 / params.source_impedance) if params.source_impedance > 0 else 0.0

    L += [f"static const hv_params {ident}_params = {{",
          f"    .family = {params.family},",
          f"    .n_modes = {len(coeffs)},",
          f"    .oversample = {params.oversample},",
          f"    .modes = {ident}_modes,",
          f"    .reed = {{{_d(reed[0])}, {_d(reed[1])}, {_d(reed[2])}, "
          f"{_d(reed[3])}, {_d(reed[4])}}},   /* b0 b1 b2 a1+2 1-a2, double */",
          f"    .rest_opening = {_f(params.rest_opening_m)},",
          f"    .width = {_f(params.width_m)},",
          f"    .vena = {_f(params.vena_contracta)},",
          f"    .max_open = {_f(params.max_open_m)},",
          f"    .leak = {_f(params.leak_m)},",
          f"    .src_admit = {_f(admit)},",
          f"    .flow_gain = {_f(flow_gain)},",
          f"    .visc_pa = {_f(params.visc_pa)},",
          f"    .mu_s = {_f(params.mu_static)},",
          f"    .mu_d = {_f(params.mu_dynamic)},",
          f"    .v_char = {_f(params.v_char)},",
          f"    .bow_speed = {_f(params.bow_speed)},",
          f"    .cavity_gain = {_f(cavity_gain)},",
          f"    .cavity_leak = {_f(0.99999 if cavity_gain else 0.0)},",
          f"    .out_mode = {0 if params.sortie_effective == SORTIE_RAYONNEE else 1},",
          f"    .fs_out = {_f(params.samplerate)},",

          f"    .free_law = {loi_c(params)},",
          f"    .plate = {_f(params.plate_m)},",
          f"    .tongue = {_f(params.tongue_m)},",
          f"    .clear = {_f(params.clearance_m)},",
          f"    .pump_area = {_f(params.pump_area_m2)},",
          f"    .n_aa = {len(aa)},",
          f"    .aa = {ident}_aa,",
          "};", "",
          f"#endif /* {ident.upper()}_PARAMS_H */", ""]
    return "\n".join(L)


def export_c(params: RealtimeParams, directory, ident=None):
    """Écrit moteur + table dans `directory`. Renvoie les chemins écrits."""
    import pathlib
    d = pathlib.Path(directory)
    d.mkdir(parents=True, exist_ok=True)
    written = []
    for nom, texte in to_c_engine().items():
        (d / nom).write_text(texte, encoding='utf-8')
        written.append(str(d / nom))
    ident = ident or _ident(params.name)
    f = d / f"{ident}_params.h"
    f.write_text(to_c_params(params, ident), encoding='utf-8')
    written.append(str(f))
    return written

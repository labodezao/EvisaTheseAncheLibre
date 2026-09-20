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
    max_open_m: float = 0.0                        # >0 : anche libre (saturation)
    leak_m: float = 0.0
    reed_area_m2: float = 0.0
    source_impedance: float = 0.0                  # 0 = source parfaite

    # excitateur — archet
    mu_static: float = 0.8
    mu_dynamic: float = 0.3
    v_char: float = 0.05
    bow_speed: float = 0.2

    @property
    def fs_internal(self):
        return self.samplerate * self.oversample


#: suréchantillonnage minimal par famille, **mesuré** et non supposé.
#: L'archet en demande deux fois plus que l'anche : sa courbe de frottement
#: varie sur 0,05 m/s alors que la corde atteint 1,4 m/s, soit une pente bien
#: plus raide que Bernoulli. À K=4 le violon décroche et part à 91 Hz au lieu
#: de 440 ; à K=8 il retrouve 437,6 Hz.
OVERSAMPLE_MIN = {FAMILY_SINGLE_REED: 4, FAMILY_FREE_REED: 4, FAMILY_BOW: 8}


def params_from_voice(voice: HybridVoice, samplerate=48000.0, oversample=None,
                      name=None):
    """Traduit une `HybridVoice` continue en jeu de paramètres embarquables.

    `oversample=None` prend le minimum sûr de la famille (`OVERSAMPLE_MIN`).
    Ce n'est pas de la prudence : en dessous, la boucle décroche et sort une
    hauteur fausse, pas un son dégradé.

    Pourquoi suréchantillonner plutôt que résoudre le couplage implicitement
    (Newton) : en audio temps réel, un coût **fixe** par échantillon vaut
    mieux qu'un coût moyen plus bas mais variable. Un nombre d'itérations qui
    dépend du signal, c'est une échéance qu'on rate un jour de concert.
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
                       compliance=float(voice.resonator.compliance or 0.0))

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
        p.reed_area_m2 = ex.area_m2
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
        self.reset()

    def reset(self):
        self.res.reset()
        self.reed.reset()
        self.response = 0.0
        self.cavity = 0.0
        self.drive = 0.0
        self._kick = True

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
            q = (p.vena_contracta * p.width_m * h *
                 np.sign(dp) * np.sqrt(2.0 * abs(dp) / RHO))
            return q, h

        # anche libre : la pression l'ouvre, la soupape interdit le retour
        y = self.reed.step(response)
        h = min(max(p.rest_opening_m + y, p.leak_m), p.max_open_m)
        q_out = (p.vena_contracta * p.width_m * h *
                 np.sqrt(2.0 * response / RHO)) if response > 0.0 else 0.0
        q_src = level
        if p.source_impedance > 0.0:
            q_src -= response / p.source_impedance
        return q_src - q_out, h

    def render(self, n_samples, level, out_opening=False):
        """Rend `n_samples` à la commande `level`. Renvoie `(audio, ouverture)`.

        L'audio est la grandeur que l'instrument rayonne : la pression pour un
        tuyau, la vitesse de corde pour un archet.
        """
        p = self.p
        n = int(n_samples)
        audio = np.zeros(n)
        opening = np.zeros(n) if out_opening else None

        for i in range(n):
            h = float('nan')
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
            audio[i] = self.response
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
    n_biq = len(params.modes) + (0 if params.family == FAMILY_BOW else 1)
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

#define HV_FAMILY_SINGLE_REED 0
#define HV_FAMILY_FREE_REED   1
#define HV_FAMILY_BOW         2

typedef struct { float b0, b1, b2, a1, a2; } hv_biquad;
typedef struct { float z1, z2; } hv_bqstate;

typedef struct {
    int   family;
    int   n_modes;
    int   oversample;

    const hv_biquad *modes;      /* n_modes résonances */
    hv_biquad reed;              /* dynamique de l'anche (inutilisé : archet) */

    /* anches */
    float rest_opening;          /* h0, m */
    float width;                 /* m */
    float vena;                  /* coefficient de contraction */
    float max_open;              /* m, anche libre : saturation d'ouverture */
    float leak;                  /* m, anche libre : fuite résiduelle */
    float src_admit;             /* 1/R du soufflet, 0 = source parfaite */
    float flow_gain;             /* vena*width*sqrt(2/rho), précalculé */

    /* archet */
    float mu_s, mu_d, v_char, bow_speed;

    /* cavité fermée (accordéon) : 0 si perce ouverte */
    float cavity_gain;           /* 1/(C*fs_interne) */
    float cavity_leak;
} hv_params;

typedef struct {
    hv_bqstate z[HV_MAX_MODES];
    hv_bqstate reed_z;
    float response;
    float cavity;
    int   kicked;
} hv_state;

void hv_reset(hv_state *st);
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

void hv_reset(hv_state *st)
{
    int i;
    for (i = 0; i < HV_MAX_MODES; ++i) { st->z[i].z1 = 0.0f; st->z[i].z2 = 0.0f; }
    st->reed_z.z1 = 0.0f;
    st->reed_z.z2 = 0.0f;
    st->response = 0.0f;
    st->cavity = 0.0f;
    st->kicked = 0;
}

/* La non-linéarité : le seul endroit où l'instrument cesse d'être un filtre. */
static inline float hv_exciter(const hv_params *p, hv_state *st,
                               float response, float level)
{
    if (p->family == HV_FAMILY_BOW) {
        const float v_rel = p->bow_speed - response;
        const float av = v_rel < 0.0f ? -v_rel : v_rel;
        const float mu = p->mu_d + (p->mu_s - p->mu_d) / (1.0f + av / p->v_char);
        return (v_rel < 0.0f ? -level : level) * mu;
    }

    if (p->family == HV_FAMILY_SINGLE_REED) {
        const float dp = level - response;
        const float y  = bq_step(&p->reed, &st->reed_z, dp);
        float h = p->rest_opening + y;
        float adp;
        if (h < 0.0f) h = 0.0f;              /* l'anche claque sur la table */
        adp = dp < 0.0f ? -dp : dp;
        return (dp < 0.0f ? -1.0f : 1.0f) * p->flow_gain * h * sqrtf(adp);
    }

    {   /* anche libre : la pression l'ouvre, la soupape interdit le retour */
        const float y = bq_step(&p->reed, &st->reed_z, response);
        float h = p->rest_opening + y;
        float q_out = 0.0f, q_src = level;
        if (h < p->leak)     h = p->leak;
        if (h > p->max_open) h = p->max_open;
        if (response > 0.0f) q_out = p->flow_gain * h * sqrtf(response);
        if (p->src_admit > 0.0f) q_src -= response * p->src_admit;
        return q_src - q_out;
    }
}

void hv_render(const hv_params *p, hv_state *st, float level,
               float *out, int n)
{
    int i, k, m;
    for (i = 0; i < n; ++i) {
        for (k = 0; k < p->oversample; ++k) {
            float drive, acoustic = 0.0f;
            if (!st->kicked) { st->response += 1e-6f; st->kicked = 1; }
            drive = hv_exciter(p, st, st->response, level);
            for (m = 0; m < p->n_modes; ++m)
                acoustic += bq_step(&p->modes[m], &st->z[m], drive);
            if (p->cavity_gain > 0.0f) {
                st->cavity = (st->cavity + drive * p->cavity_gain) * p->cavity_leak;
            }
            st->response = acoustic + st->cavity;
        }
        out[i] = st->response;
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
        reed = biquad_lowpass(params.reed_freq_hz, params.reed_q,
                              sign * params.rest_opening_m /
                              params.closing_pressure_pa, fs) or (0.,) * 5

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

    flow_gain = params.vena_contracta * params.width_m * np.sqrt(2.0 / RHO)
    cavity_gain = (1.0 / (params.compliance * fs)) if params.compliance > 0 else 0.0
    admit = (1.0 / params.source_impedance) if params.source_impedance > 0 else 0.0

    L += [f"static const hv_params {ident}_params = {{",
          f"    .family = {params.family},",
          f"    .n_modes = {len(coeffs)},",
          f"    .oversample = {params.oversample},",
          f"    .modes = {ident}_modes,",
          f"    .reed = {{{_f(reed[0])}, {_f(reed[1])}, {_f(reed[2])}, "
          f"{_f(reed[3])}, {_f(reed[4])}}},",
          f"    .rest_opening = {_f(params.rest_opening_m)},",
          f"    .width = {_f(params.width_m)},",
          f"    .vena = {_f(params.vena_contracta)},",
          f"    .max_open = {_f(params.max_open_m)},",
          f"    .leak = {_f(params.leak_m)},",
          f"    .src_admit = {_f(admit)},",
          f"    .flow_gain = {_f(flow_gain)},",
          f"    .mu_s = {_f(params.mu_static)},",
          f"    .mu_d = {_f(params.mu_dynamic)},",
          f"    .v_char = {_f(params.v_char)},",
          f"    .bow_speed = {_f(params.bow_speed)},",
          f"    .cavity_gain = {_f(cavity_gain)},",
          f"    .cavity_leak = {_f(0.99999 if cavity_gain else 0.0)},",
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

"""Du sample au modèle physique : calage de l'anche sur un son mesuré.

Pièce manquante entre `sample_extract` (ce qu'on mesure d'un enregistrement)
et `reed_oscillator` (le modèle qui produit le son). Elle répond à une
question simple et concrète : *quelle anche, dans quelle chambre, produirait
ce son-là ?*

Le point délicat, et qui se trompe facilement : **la fréquence de jeu n'est
pas la fréquence propre de la languette**. Le ressort d'air de la chambre
ajoute une raideur au système et remonte la note.

L'écart dépend fortement du registre, parce que cette raideur ajoutée est à
peu près **fixe** alors que celle de la languette croît avec l'aigu :

- grosse anche de basse (102 Hz propres) : joue à 119 Hz, soit **+2,7
  demi-tons** — l'ignorer fausse tout ;
- anche médium (220 Hz propres) : joue à 221,7 Hz, **+0,14 demi-ton** —
  négligeable en pratique.

`tune_to_playing_frequency` inverse ce décalage quel que soit le registre.
Elle coûte quelques secondes (chaque itération cherche un seuil) ; dans
l'aigu, `build_model` seul suffit largement.
"""
from __future__ import annotations

import numpy as np

from .reed_model import SECTIONS_DEFAULT
from . import modal
from .reed_oscillator import FreeReedModel, Chamber, Slot, Source


def scale_sections(sections, factor_length):
    """Homothétie sur les **longueurs** des tronçons.

    Pour une poutre encastrée-libre, `f ∝ 1/L²` : multiplier les longueurs par
    `s` divise les fréquences propres par `s²`. On ne touche ni aux épaisseurs
    ni au matériau, donc le profil (et le caractère d'anche lestée) est
    conservé.
    """
    sec = np.array(sections, dtype=float, copy=True)
    sec[:, 0] *= float(factor_length)
    return sec


def sections_for_mode(f_target, sections=None, n_modes=2):
    """Géométrie dont le **premier mode propre** vaut `f_target` (Hz).

    `n_modes` doit être celui du modèle qui utilisera cette géométrie : la
    projection de Rayleigh-Ritz donne une première fréquence d'autant plus
    basse qu'on ajoute des modes, et caler sur une base à 1 mode pour évaluer
    ensuite sur 2 décale la note de 2 % (mesuré : 220,1 Hz visés, 215,7
    obtenus).

    Attention : c'est la fréquence de la languette *libre*, pas celle qu'elle
    jouera une fois montée — voir `tune_to_playing_frequency`.
    """
    base = SECTIONS_DEFAULT if sections is None else sections
    f_ref = float(np.sort(modal.natural_frequencies_np(base, n_modes=n_modes))[0])
    if not np.isfinite(f_target) or f_target <= 0:
        raise ValueError("f_target doit être une fréquence positive")
    return scale_sections(base, np.sqrt(f_ref / float(f_target)))


def build_model(f_mode_hz, chamber=None, slot=None, source=None,
                n_modes=2, zeta=0.004, sections=None):
    """`FreeReedModel` dont la languette a `f_mode_hz` comme premier mode."""
    return FreeReedModel(sections=sections_for_mode(f_mode_hz, sections, n_modes),
                         chamber=chamber or Chamber(), slot=slot or Slot(),
                         source=source or Source(), n_modes=n_modes, zeta=zeta)


def playing_frequency(model, n_scan=20):
    """Fréquence au seuil de démarrage, ou `nan` si l'anche ne démarre pas."""
    bas = model.hopf_threshold(n_scan=n_scan)
    return float(bas[2]) if bas else float('nan')


def tune_to_playing_frequency(f_play_hz, tol=0.5, n_iter=12, n_scan=16, **kw):
    """Cherche la languette dont la **fréquence de jeu** vaut `f_play_hz`.

    Inverse le raidissement dû au ressort d'air, par itérations de point fixe
    sur le rapport (fréquence visée / fréquence obtenue). Renvoie
    `(modèle, f_jouée, f_mode)`.

    Lève `RuntimeError` si aucune anche de la famille ne démarre — cas réel :
    sous un certain volume de chambre, **rien ne s'auto-entretient**, et il
    vaut mieux le dire que de renvoyer un modèle muet.
    """
    f_mode = float(f_play_hz)          # première tentative : l'ignorer
    best = None
    for _ in range(int(n_iter)):
        m = build_model(f_mode, **kw)
        f_play = playing_frequency(m, n_scan=n_scan)
        if not np.isfinite(f_play):
            raise RuntimeError(
                f"aucun démarrage pour une languette à {f_mode:.1f} Hz : "
                "vérifie le volume de chambre (trop petit = ressort d'air trop "
                "raide) et l'ouverture de saturation")
        best = (m, f_play, f_mode)
        if abs(f_play - f_play_hz) <= tol:
            break
        f_mode *= f_play_hz / f_play   # le décalage est multiplicatif
    return best


def synthesize(model, dur=2.0, fs=44100.0, drive=2.0, oversample=16,
               settle=0.6):
    """Fait sonner le modèle et renvoie `(audio, infos)`.

    `drive` est un multiple du **seuil de démarrage** : c'est la nuance, et
    c'est la grandeur qui a un sens physique (1,0 = au seuil, rien ne sort).

    L'audio renvoyé est `dq/dt`, le proxy du rayonnement en champ lointain —
    une anche libre rayonne par le débit modulé, pas par la pression de
    chambre. Les `settle` premières secondes sont coupées : l'établissement du
    cycle limite demande plus d'une seconde et fausserait l'écoute.
    """
    bas = model.hopf_threshold(n_scan=20)
    if bas is None:
        raise RuntimeError("ce modèle ne s'auto-entretient pas : pas de son à produire")
    q_on, p_on, f_on = bas

    res = model.simulate(dur + settle, fs=fs, q_in=q_on * float(drive),
                         oversample=oversample)
    n_cut = int(settle * fs)
    audio = res.radiated[n_cut:]
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak

    tail = slice(int(0.8 * res.tip.size), None)
    infos = dict(
        q_on=q_on, p_on=p_on, f_on=f_on,
        f_modes=model.f_modes.tolist(),
        drive=float(drive),
        excursion_mm=float(np.ptp(res.tip[tail])) * 1e3,
        pressure_pa=float(np.ptp(res.pressure[tail])),
        closed_fraction=float(np.mean(res.opening[tail] <= model.slot.leak_m * 1.001)),
    )
    return audio, infos


def compare_to_sample(audio, sample_audio, fs):
    """Distance log-spectrale (dB) entre le son synthétisé et l'original.

    Repère : < 3 dB très proche, 3–8 dB même couleur, > 8 dB timbre différent.

    ⚠️ Les deux signaux doivent être dans le **même domaine**. La synthèse
    renvoie `dq/dt`, le rayonnement en champ lointain, qui accentue les aigus
    de 6 dB/octave. C'est comparable à un **enregistrement au micro**, qui
    contient déjà ce rayonnement — mais pas à une somme d'harmoniques
    fabriquée à la main, ce qui donnerait un écart énorme sans que le modèle
    y soit pour rien.
    """
    from .synth_export import spectral_distance_db
    return spectral_distance_db(sample_audio, audio, fs)

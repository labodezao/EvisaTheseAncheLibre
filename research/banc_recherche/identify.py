"""Du son mesuré au modèle physique — l'identification hybride.

La question honnête n'est pas « peut-on retrouver un modèle physique complet
à partir d'un enregistrement ? » — la réponse est non, et
`sample_extract.extract_multi` le démontre : sur une note unique, le problème
est sous-déterminé, source et résonateur restent confondus dans l'enveloppe.

La question utile est : **qu'est-ce qui se mesure, et qu'est-ce qui se
suppose ?** Ce module tient les deux colonnes séparées et le dit dans son
rapport, parce qu'un paramètre supposé qu'on prend pour mesuré est la façon
la plus sûre de se tromper longtemps.

Ce qui se mesure vraiment
-------------------------
- **f0** — sans ambiguïté, par autocorrélation ;
- **la conicité d'une perce** — le rapport pairs/impairs des partiels
  distingue un tuyau cylindrique d'un cône, et c'est franc : une clarinette
  affiche 30 dB d'écart là où un saxophone en montre 4 ;
- **la position d'archet** — un mode que l'archet touche à son nœud ne peut
  pas sonner. Le creux dans la série harmonique donne `β ≈ 1/n` ;
- **la décroissance spectrale** — pente en dB par octave de rang, d'où
  l'amortissement des modes aigus et la nuance de jeu ;
- **le corps** (résonances fixes en fréquence absolue) — mais seulement avec
  **plusieurs notes**, via `extract_multi`.

Ce qui reste supposé
--------------------
La famille d'excitateur, les dimensions de l'anche, la masse de la corde. On
ne les déduit pas d'un son : on les prend d'un a priori d'instrument, et on
ne prétend pas les avoir mesurées. Le rapport les liste comme telles.

La suite, c'est la paillasse : `docs/experiences_a_mener.md`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import hybrid
from .hybrid import (HybridVoice, Resonator, bore_modes, string_modes,
                     SingleReedExciter, DoubleReedExciter, BowExciter)


# =============================================================================
# Descripteurs
# =============================================================================

def harmonic_levels(y, sr, f0_hz, n_partials=16, bw_cents=70.0):
    """Niveau (dB, rang 1 = 0 dB) de chaque partiel d'un son tenu.

    On cherche le maximum dans une fenêtre autour de `n·f0` plutôt que la
    valeur au bin exact : un vibrato, une dérive de justesse ou une fenêtre
    trop courte déplacent le partiel de plusieurs bins, et lire au bin exact
    mesurerait alors le creux à côté du pic.
    """
    x = np.asarray(y, dtype='float64').ravel()
    x = x - x.mean()
    if x.size < 1024 or f0_hz <= 0:
        return np.full(int(n_partials), np.nan)

    n_fft = int(2 ** np.ceil(np.log2(min(x.size, 1 << 16))))
    X = np.abs(np.fft.rfft(x[:n_fft] * np.hanning(min(n_fft, x.size))[:n_fft], n_fft))
    fr = np.fft.rfftfreq(n_fft, 1.0 / sr)

    out = np.full(int(n_partials), np.nan)
    for k in range(1, int(n_partials) + 1):
        fc = k * f0_hz
        if fc >= sr / 2:
            break
        half = fc * (2 ** (bw_cents / 1200.0) - 1.0)
        m = np.abs(fr - fc) <= max(half, fr[1] * 1.5)
        if m.any():
            out[k - 1] = X[m].max()

    ref = out[0] if np.isfinite(out[0]) and out[0] > 0 else np.nanmax(out)
    if not np.isfinite(ref) or ref <= 0:
        return np.full(int(n_partials), np.nan)
    return 20 * np.log10(np.maximum(out, ref * 1e-6) / ref)


def odd_even_ratio(levels_db):
    """Écart moyen impairs − pairs, en dB. Le signe de la conicité.

    Un tuyau cylindrique fermé à l'anche ne résonne que sur les rangs impairs.
    Un cône les prend tous. Mesuré sur le modèle : ~35 dB pour une
    clarinette, ~4 dB pour un saxophone.

    ⚠️ À lire sur un son **tenu et bien établi**. Sur une anche battante, le
    rapport cyclique déplace fortement cet équilibre — une anche fermée la
    moitié du temps éteint ses harmoniques paires même sur une perce conique.
    Ce descripteur sépare les perces, pas les régimes de jeu.
    """
    v = np.asarray(levels_db, dtype='float64')
    odd, even = v[0::2], v[1::2]
    o, e = odd[np.isfinite(odd)], even[np.isfinite(even)]
    if o.size < 2 or e.size < 2:
        return float('nan')
    return float(o.mean() - e.mean())


def bore_kind_from_sound(levels_db, seuil_db=12.0):
    """`'cylindrique'` ou `'conique'`, d'après le rapport pairs/impairs."""
    r = odd_even_ratio(levels_db)
    if not np.isfinite(r):
        return 'conique'
    return 'cylindrique' if r > seuil_db else 'conique'


def bow_position_from_sound(levels_db, n_min=3, n_max=12):
    """Position d'archet `β`, d'après le creux dans la série harmonique.

    L'archet posé à la fraction β annule les modes dont il touche un nœud,
    c'est-à-dire les rangs multiples de 1/β. Le partiel le plus faible de la
    série donne donc directement le dénominateur.

    Renvoie `nan` si aucun creux ne se détache : mieux vaut l'avouer que
    d'inventer une position.
    """
    v = np.asarray(levels_db, dtype='float64')
    hi = min(int(n_max), v.size)
    if hi <= n_min:
        return float('nan')
    seg = v[n_min - 1:hi]
    if not np.isfinite(seg).any():
        return float('nan')
    k = int(np.nanargmin(seg)) + n_min
    voisins = [v[j - 1] for j in (k - 1, k + 1)
               if 0 < j <= v.size and np.isfinite(v[j - 1])]
    if not voisins or (np.mean(voisins) - v[k - 1]) < 6.0:
        return float('nan')          # pas de creux franc : on ne conclut pas
    return 1.0 / k


def spectral_decay(levels_db):
    """Pente des partiels, en dB par octave de **rang**.

    Repères : une dent de scie idéale (Helmholtz parfait) donne −6 dB/octave ;
    plus raide, le son est sourd ; plus plat, il est criard.
    """
    v = np.asarray(levels_db, dtype='float64')
    n = np.arange(1, v.size + 1, dtype='float64')
    ok = np.isfinite(v)
    if ok.sum() < 3:
        return float('nan')
    return float(np.polyfit(np.log2(n[ok]), v[ok], 1)[0])


# =============================================================================
# Identification
# =============================================================================

@dataclass
class Identification:
    """Le modèle, et surtout **ce qu'on sait de sa provenance**."""
    voice: HybridVoice = None
    instrument: str = ""
    f0_hz: float = float('nan')
    level: float = float('nan')

    mesure: dict = field(default_factory=dict)    # ce qui vient du son
    suppose: dict = field(default_factory=dict)   # ce qui vient d'un a priori
    ecart_db: float = float('nan')                # accord modèle / son

    def rapport(self):
        """Rapport lisible — à coller dans un carnet de manip."""
        L = [f"Instrument      : {self.instrument}",
             f"Fréquence       : {self.f0_hz:.2f} Hz",
             f"Commande de jeu : {self.level:.4g}",
             "",
             "MESURÉ sur le son :"]
        L += [f"  - {k:26s} {v}" for k, v in self.mesure.items()] or ["  (rien)"]
        L += ["", "SUPPOSÉ (a priori d'instrument, non mesuré) :"]
        L += [f"  - {k:26s} {v}" for k, v in self.suppose.items()] or ["  (rien)"]
        if np.isfinite(self.ecart_db):
            L += ["", f"Écart spectral modèle / son : {self.ecart_db:.1f} dB RMS",
                  "  (< 4 dB : même couleur · 4–8 : parent · > 8 : autre timbre)"]
        return "\n".join(L)


def _fit_level(voice, levels_db, candidats, fs=22050.0, dur=0.22, settle=0.16):
    """Cherche la nuance dont le spectre colle le mieux au son mesuré.

    Une seule grandeur à ajuster, et c'est celle que le musicien pousse
    vraiment. Le reste de l'excitateur vient de la famille : on ne va pas
    prétendre régler six paramètres d'anche sur un enregistrement.
    """
    cible = np.asarray(levels_db, dtype='float64')
    n = min(cible.size, 12)
    best, best_err, best_lv = None, float('inf'), float('nan')
    for lv in candidats:
        try:
            r = voice.simulate(dur, fs=fs, level=float(lv), oversample=8,
                               settle=settle)
        except Exception:
            continue
        if np.ptp(r.response) < 1e-9:
            continue
        f0 = hybrid.playing_frequency(r.response, r.fs)
        if not np.isfinite(f0) or f0 <= 0:
            continue
        got = harmonic_levels(r.response, r.fs, f0, n_partials=n)
        ok = np.isfinite(got) & np.isfinite(cible[:n])
        if ok.sum() < 3:
            continue
        err = float(np.sqrt(np.mean((got[ok] - cible[:n][ok]) ** 2)))
        if err < best_err:
            best, best_err, best_lv = r, err, float(lv)
    return best_lv, best_err


def identify(y, sr, instrument, f0_hz=None, n_partials=16, fit_level=True):
    """Identifie un modèle physique hybride à partir d'un son tenu.

    `instrument` nomme la famille (`'clarinette'`, `'saxophone'`, `'bombarde'`,
    `'cornemuse'`, `'violon'`, `'vielle'`, `'accordeon'`). C'est l'a priori
    qu'on assume : le son ne dira pas s'il vient d'une anche ou d'un archet,
    et prétendre le deviner serait de la magie.

    Ce qui, en revanche, sort bel et bien du son : la hauteur, la conicité de
    la perce, la position d'archet, la décroissance spectrale, et la nuance.
    """
    y = np.asarray(y, dtype='float64').ravel()
    f0 = float(f0_hz) if f0_hz else hybrid.playing_frequency(y, sr)
    if not np.isfinite(f0) or f0 <= 0:
        raise ValueError("hauteur introuvable : le son est-il tenu et monophonique ?")

    niveaux = harmonic_levels(y, sr, f0, n_partials=n_partials)
    pente = spectral_decay(niveaux)
    ident = Identification(instrument=str(instrument), f0_hz=f0)
    ident.mesure['f0 (Hz)'] = f"{f0:.2f}"
    ident.mesure['pente spectrale'] = f"{pente:+.1f} dB/octave de rang"

    fam = hybrid.FAMILIES.get(str(instrument).lower())
    if fam is None:
        raise ValueError(f"instrument inconnu : {instrument!r}. "
                         f"Connus : {', '.join(sorted(hybrid.FAMILIES))}")

    if fam == 'archet':
        beta = bow_position_from_sound(niveaux)
        if np.isfinite(beta):
            ident.mesure['position d\'archet β'] = f"1/{1/beta:.0f} (creux harmonique)"
        else:
            beta = 1.0 / 7.0
            ident.suppose['position d\'archet β'] = "1/7 (aucun creux net)"
        # une pente raide = des aigus vite perdus = modes aigus plus amortis
        q_decay = float(np.clip((-pente - 6.0) / 6.0, 0.0, 1.5)) \
            if np.isfinite(pente) else 0.0
        ident.mesure['amortissement aigus'] = f"Q ∝ 1/n^{q_decay:.2f}"
        ident.suppose['masse de corde'] = "3,5·10⁻⁴ kg (a priori)"
        ident.suppose['loi de frottement'] = "courbe μ(v), collophane non thermique"
        modes = string_modes(f0, 16, beta, 3.5e-4, 500.0, q_decay=q_decay)
        voice = HybridVoice(BowExciter(), Resonator(modes, name="corde"),
                            name=str(instrument))
        candidats = np.geomspace(0.05, 1.5, 10)

    elif fam == 'anche_libre':
        ident.suppose['résonateur'] = "chambre 40 cm³ (à mesurer, cf. E2)"
        ident.suppose['géométrie de languette'] = "a priori accordéon"
        voice = hybrid.accordeon(f0_hz=f0)
        candidats = np.geomspace(1e-6, 3e-5, 10)

    else:
        kind = bore_kind_from_sound(niveaux)
        r = odd_even_ratio(niveaux)
        ident.mesure['conicité'] = f"{kind} (impairs−pairs {r:+.1f} dB)"
        ident.suppose['diamètre de perce'] = "a priori d'instrument"
        ident.suppose['géométrie d\'anche'] = "a priori d'instrument"
        base = hybrid.INSTRUMENTS[str(instrument).lower()](f0_hz=f0)
        ex = base.exciter
        modes = bore_modes(f0, len(base.resonator.modes), kind,
                           base.resonator.modes[0].q,
                           base.resonator.modes[0].peak)
        voice = HybridVoice(ex, Resonator(modes, name="perce"),
                            name=str(instrument))
        pc = ex.closing_pressure_pa
        candidats = np.linspace(0.4 * pc, 1.1 * pc, 10)

    ident.voice = voice
    if fit_level:
        lv, err = _fit_level(voice, niveaux, candidats)
        ident.level, ident.ecart_db = lv, err
        if np.isfinite(lv):
            ident.mesure['nuance ajustée'] = f"{lv:.4g} ({ex_unit(voice)})"
    return ident


def ex_unit(voice):
    """Unité de la commande de jeu, pour l'affichage."""
    return getattr(voice.exciter, 'control_unit', '') or '—'


def to_realtime(ident: Identification, samplerate=48000.0, oversample=None):
    """Passe de l'identification au jeu de paramètres embarquable."""
    from .embedded import params_from_voice
    return params_from_voice(ident.voice, samplerate=samplerate,
                             oversample=oversample, name=ident.instrument)

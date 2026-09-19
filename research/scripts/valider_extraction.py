#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
VALIDATION DE L'EXTRACTION — signal de test à vérité connue
================================================================================

On fabrique un son dont on **connaît** tous les paramètres (hauteur, vibrato,
résonance du corps, attaque, bruit), on le passe dans l'extracteur, et on
compare. Puis on **resynthétise depuis le modèle extrait** et on mesure la
distance au signal d'origine.

C'est le seul contrôle honnête : tant qu'on n'a pas rejoué le son depuis les
paramètres, on ne sait pas si les paramètres décrivent le son.

Deux resynthèses, qui ne testent pas la même chose :
  - additive      : rejoue les partiels mesurés (valide l'extraction des raies)
  - source_filter : source à la pente mesurée + biquads du résonateur
                    (valide la séparation source/corps — le vrai test)

USAGE
    python3 valider_extraction.py               # sortie texte
    python3 valider_extraction.py --wav DOSSIER # + écrit les WAV à écouter
================================================================================
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from banc_recherche import sample_extract as sx
from banc_recherche import synth_export as se


# ==============================================================================
# Signal de test : vérité connue
# ==============================================================================

VERITE = dict(
    f0_hz=220.0,
    vibrato_rate_hz=5.0,
    vibrato_depth_cents=30.0,
    resonance_hz=1500.0,
    resonance_q=3.0,
    attack_s=0.080,
    noise_pct=2.0,
    duration_s=3.0,
    samplerate=44100,
)


def signal_test(v=VERITE, seed=0):
    """Anche synthétique : peigne harmonique mis en forme par une résonance de
    corps, avec attaque, vibrato et un peu de souffle."""
    sr = v['samplerate']
    n = int(v['duration_s'] * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(seed)

    # hauteur instantanée (vibrato)
    dev = (v['vibrato_depth_cents'] / 1200.0) * np.sin(2 * np.pi * v['vibrato_rate_hz'] * t)
    f_inst = v['f0_hz'] * (2.0 ** dev)
    phase = 2 * np.pi * np.cumsum(f_inst) / sr

    # partiels mis en forme par la résonance du corps (2e ordre)
    y = np.zeros(n)
    k = 1
    while k * v['f0_hz'] < sr / 2 * 0.9:
        f = k * v['f0_hz']
        r = f / v['resonance_hz']
        amp = 1.0 / np.sqrt((1 - r ** 2) ** 2 + (r / v['resonance_q']) ** 2)
        y += amp * np.sin(k * phase + rng.uniform(0, 2 * np.pi))
        k += 1

    # attaque puis extinction douce
    env = np.minimum(1.0, t / v['attack_s'])
    rel = 0.25
    env *= np.minimum(1.0, (v['duration_s'] - t) / rel)
    y *= np.maximum(env, 0.0)

    # souffle
    rms = np.sqrt(np.mean(y ** 2))
    y += rng.standard_normal(n) * rms * np.sqrt(v['noise_pct'] / 100.0) * np.maximum(env, 0)

    return y / (np.max(np.abs(y)) or 1.0), sr


# ==============================================================================
# Comparaison
# ==============================================================================

def _ligne(nom, attendu, mesure, unite="", tol=None):
    if mesure is None or not np.isfinite(mesure):
        return f"  {nom:<26} {attendu:>10.2f}   {'—':>10}   {unite}"
    ecart = mesure - attendu
    verdict = ""
    if tol is not None:
        verdict = "  ok" if abs(ecart) <= tol else "  ÉCART"
    return (f"  {nom:<26} {attendu:>10.2f}   {mesure:>10.2f}   "
            f"{unite:<14} {ecart:+8.2f}{verdict}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[3])
    ap.add_argument('--wav', metavar='DIR', default=None,
                    help="écrit original + resynthèses en WAV dans ce dossier")
    args = ap.parse_args()

    v = VERITE
    y, sr = signal_test(v)

    print("=" * 78)
    print("SIGNAL DE TEST — vérité connue")
    print("=" * 78)
    print(f"  {v['duration_s']:.1f} s à {sr} Hz · f0 = {v['f0_hz']} Hz · "
          f"corps {v['resonance_hz']} Hz (Q={v['resonance_q']})")
    print(f"  vibrato {v['vibrato_rate_hz']} Hz / {v['vibrato_depth_cents']} cents · "
          f"attaque {v['attack_s']*1000:.0f} ms · souffle {v['noise_pct']} %")

    m = sx.extract(y, sr, name="test", n_partials=16, n_resonators=4)

    print()
    print("=" * 78)
    print("EXTRACTION — attendu vs mesuré")
    print("=" * 78)
    print(f"  {'grandeur':<26} {'attendu':>10}   {'mesuré':>10}   {'unité':<14} {'écart':>8}")
    print("  " + "-" * 74)
    print(_ligne("hauteur f0", v['f0_hz'], m.f0_hz, "Hz", tol=2.0))
    print(_ligne("vibrato — taux", v['vibrato_rate_hz'], m.vibrato_rate_hz, "Hz", tol=1.0))
    print(_ligne("vibrato — profondeur", v['vibrato_depth_cents'], m.vibrato_depth_cents,
                 "cents", tol=15.0))

    if m.resonators:
        best = max(m.resonators, key=lambda r: r['gain_db'])
        print(_ligne("résonance du corps", v['resonance_hz'], best['freq_hz'], "Hz", tol=250.0))
        print(_ligne("facteur Q du corps", v['resonance_q'], best['q'], "", tol=2.0))
    else:
        print("  aucune résonance détectée")

    if m.adsr:
        print(_ligne("attaque", v['attack_s'] * 1000, m.adsr['attack_s'] * 1000, "ms", tol=40.0))
    print(_ligne("part de bruit", v['noise_pct'], m.percussive_pct, "%", tol=8.0))

    print()
    print("  Partiels mesurés (niveau dB relatif au fondamental) :")
    for k, lvl in enumerate(m.partial_levels_db[:10], start=1):
        f = k * m.f0_hz
        r = f / v['resonance_hz']
        attendu = 1.0 / np.sqrt((1 - r ** 2) ** 2 + (r / v['resonance_q']) ** 2)
        r1 = m.f0_hz / v['resonance_hz']
        ref = 1.0 / np.sqrt((1 - r1 ** 2) ** 2 + (r1 / v['resonance_q']) ** 2)
        attendu_db = 20 * np.log10(attendu / ref)
        bar = "#" * max(0, int((lvl + 30) / 2))
        print(f"    n={k:2d}  {f:7.0f} Hz   attendu {attendu_db:+6.1f}   "
              f"mesuré {lvl:+6.1f} dB  {bar}")

    # ---- resynthèses -------------------------------------------------------
    print()
    print("=" * 78)
    print("RESYNTHÈSE DEPUIS LE MODÈLE — distance log-spectrale à l'original")
    print("=" * 78)

    resyn = {}
    for mode in ('additive', 'source_filter'):
        r = se.resynthesize(m, duration_s=v['duration_s'], samplerate=sr, mode=mode)
        d = se.spectral_distance_db(y, r, sr)
        resyn[mode] = r
        note = "excellent" if d < 3 else ("correct" if d < 8 else "approximatif")
        print(f"  {mode:<16} {d:6.2f} dB d'écart moyen   ({note})")

    print()
    print("  Repère : < 3 dB = très proche · 3-8 dB = même couleur, détails différents")
    print("           > 8 dB = timbre différent")

    # ---- séparation source / résonateur sur plusieurs notes ----------------
    print()
    print("=" * 78)
    print("SÉPARATION SOURCE / RÉSONATEUR — une note vs plusieurs")
    print("=" * 78)
    print("  Sur une note seule, les partiels n'échantillonnent l'enveloppe que")
    print(f"  tous les {v['f0_hz']:.0f} Hz : la résonance à {v['resonance_hz']:.0f} Hz tombe entre deux")
    print("  harmoniques, et source et filtre restent confondus.")
    print()

    notes_hz = [147.0, 185.0, 220.0, 262.0, 330.0, 392.0]
    notes = []
    for f0 in notes_hz:
        vv = dict(v); vv['f0_hz'] = f0; vv['duration_s'] = 2.0
        notes.append(signal_test(vv, seed=int(f0))[0])

    mm = sx.extract_multi(notes, sr, name="test_multi", n_partials=16, n_resonators=3)

    print(f"  {len(mm.f0_list)} notes : " + ", ".join(f"{f:.0f}" for f in mm.f0_list) + " Hz")
    print(f"  résidu du modèle additif : {mm.residual_db:.2f} dB")
    print()
    print(f"  {'':<26} {'attendu':>10}   {'1 note':>10}   {'N notes':>10}")
    print("  " + "-" * 62)

    une_note_f = best['freq_hz'] if m.resonators else float('nan')
    une_note_q = best['q'] if m.resonators else float('nan')
    if mm.resonators:
        r = max(mm.resonators, key=lambda x: x['gain_db'])
        print(f"  {'résonance du corps (Hz)':<26} {v['resonance_hz']:>10.0f}   "
              f"{une_note_f:>10.0f}   {r['freq_hz']:>10.0f}")
        print(f"  {'facteur Q':<26} {v['resonance_q']:>10.1f}   "
              f"{une_note_q:>10.1f}   {r['q']:>10.1f}")
    else:
        print("  aucune résonance isolée sur le jeu de notes")

    print()
    print("  Source identifiée (niveau par rang harmonique, dB) :")
    for k, lvl in enumerate(mm.source_levels_db[:8], start=1):
        print(f"    rang {k:2d}   {lvl:+6.1f}")
    print(f"  pente de source : {mm.source_slope_db_per_oct:+.2f} dB/octave de rang")
    print("  (le signal de test a une source **plate** : tous les partiels à")
    print("   amplitude 1 avant le corps — une pente proche de 0 est le bon résultat)")

    if args.wav:
        d = Path(args.wav); d.mkdir(parents=True, exist_ok=True)
        from scipy.io.wavfile import write
        for nom, sig in [("1_original", y), ("2_resynth_additive", resyn['additive']),
                         ("3_resynth_source_filter", resyn['source_filter'])]:
            p = d / f"{nom}.wav"
            write(str(p), sr, (np.clip(sig, -1, 1) * 32767).astype('int16'))
            print(f"  → {p}")

    print()
    print("=" * 78)
    return 0


if __name__ == '__main__':
    sys.exit(main())

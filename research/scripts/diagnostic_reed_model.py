#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
DIAGNOSTIC — le modèle d'anche auto-oscille-t-il, et dans quel régime ?
================================================================================

Un modèle d'anche n'est utilisable pour la synthèse que s'il **auto-oscille** :
souffle constant -> son périodique entretenu. S'il ne fait que sonner puis
s'éteindre, ce qu'on entend est un transitoire, pas une note.

Ce script vérifie trois choses, dans l'ordre où elles peuvent invalider tout
le reste :

  1. **Régime physique** — pressions, course du bout, ouverture, volume
     restent-ils dans des valeurs possibles pour un accordéon ?
  2. **Entretien** — l'amplitude se maintient-elle, ou décroît-elle ?
  3. **Seuil de Hopf** — existe-t-il une pression en dessous de laquelle rien
     ne démarre et au-dessus de laquelle ça sonne ? (`seuil.py`,
     `bifurcation.py` reposent sur ce seuil.)

Un échec ici n'est pas un bug de code : c'est le modèle qui ne décrit pas
encore l'instrument. Voir `docs/vers_un_modele_jouable.md`.

USAGE
    python3 diagnostic_reed_model.py
================================================================================
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from banc_recherche.reed_model import ReedModel

# Ordres de grandeur d'un accordéon réel (sources : pratique de l'accordage,
# pression de soufflet usuelle, géométrie d'une anche de voix medium).
REEL = dict(
    surpression_pa=(200.0, 3000.0),      # pression de soufflet en jeu
    course_mm=(0.05, 1.5),               # amplitude crête-crête du bout
    ouverture_mm=(0.0, 0.5),             # jeu languette/plaque
)


def _spectre(x, fs):
    x = x - x.mean()
    sp = np.abs(np.fft.rfft(x * np.hanning(x.size)))
    f = np.fft.rfftfreq(x.size, 1 / fs)
    return f, sp


def diagnostic(rm, fs=44100.0, dur=0.5, q_in=3e-5):
    r = rm.simulate(dur, fs, q_in=q_in)
    p, pos, V = r.pressure, r.position, r.volume
    patm = rm.cav.patm

    print("-" * 78)
    print("1. RÉGIME PHYSIQUE")
    print("-" * 78)
    surp = (p.min() - patm, p.max() - patm)
    course = (pos.max() - pos.min()) * 1e3
    ouv = ((rm.cav.gap + pos.min()) * 1e3, (rm.cav.gap + pos.max()) * 1e3)

    def verdict(val, lo, hi):
        return "ok" if lo <= val <= hi else "HORS PLAGE"

    print(f"  surpression cavité   {surp[0]:+10.0f} à {surp[1]:+8.0f} Pa      "
          f"attendu ±{REEL['surpression_pa'][1]:.0f}   "
          f"{verdict(max(abs(surp[0]), abs(surp[1])), 0, REEL['surpression_pa'][1])}")
    print(f"  course du bout       {course:>10.3f} mm crête-crête   "
          f"attendu {REEL['course_mm'][0]}–{REEL['course_mm'][1]}   "
          f"{verdict(course, *REEL['course_mm'])}")
    print(f"  ouverture min/max    {ouv[0]:+10.3f} à {ouv[1]:+8.3f} mm  "
          f"(négatif = l'anche traverse sa plaque)   "
          f"{'ok' if ouv[0] >= -1e-6 else 'HORS PLAGE'}")
    print(f"  volume de cavité     {V.min()/rm.V0:>10.3f} à {V.max()/rm.V0:>8.3f} × V0  "
          f"(cavité rigide -> devrait rester ≈ 1)   "
          f"{'ok' if abs(V.max()/rm.V0 - 1) < 0.2 else 'HORS PLAGE'}")

    print()
    print("-" * 78)
    print("2. ENTRETIEN DE L'OSCILLATION")
    print("-" * 78)
    fen = [(0.05, 0.10), (0.20, 0.25), (0.40, 0.45)]
    sigmas = []
    for a, b in fen:
        s = p[int(a * fs):int(b * fs)]
        sigmas.append(s.std())
        print(f"  écart-type sur [{a:.2f}, {b:.2f}] s : {s.std():>10.1f} Pa")
    if sigmas[0] > 0 and sigmas[-1] < 0.5 * sigmas[0]:
        print("  -> AMORTI : l'amplitude décroît. Ce n'est pas une auto-oscillation,")
        print("     c'est un transitoire qui s'éteint.")
        entretenu = False
    elif sigmas[-1] < 1e-6:
        print("  -> MUET : rien ne démarre.")
        entretenu = False
    else:
        print("  -> ENTRETENU : amplitude stable = cycle limite.")
        entretenu = True

    f, sp = _spectre(p[int(0.3 * fs):], fs)
    print(f"  fréquence dominante en fin de simulation : {f[np.argmax(sp)]:.1f} Hz "
          f"(résolution {f[1]:.1f} Hz)")
    w = np.sqrt(np.clip(np.linalg.eigvals(rm.Minv @ rm.K).real, 0, None)) / (2 * np.pi)
    print(f"  fréquences propres de l'anche : " + ", ".join(f"{x:.1f}" for x in np.sort(w)) + " Hz")
    return entretenu


def seuil_hopf(rm, fs=44100.0, dur=0.25):
    print()
    print("-" * 78)
    print("3. SEUIL DE HOPF (débit d'entrée croissant)")
    print("-" * 78)
    print(f"  {'q_in (m³/s)':>12} {'amplitude (Pa)':>16} {'course (mm)':>13}")
    amps = []
    for q_in in (5e-6, 1e-5, 3e-5, 8e-5, 2e-4):
        r = rm.simulate(dur, fs, q_in=q_in)
        seg = r.pressure[int(0.6 * dur * fs):]
        amp = float(np.std(seg - seg.mean()))
        crs = float(r.position.max() - r.position.min()) * 1e3
        amps.append(amp)
        print(f"  {q_in:>12.0e} {amp:>16.1f} {crs:>13.3f}")
    if len(amps) > 1 and amps[-1] < amps[0]:
        print("  -> l'amplitude DÉCROÎT quand l'excitation augmente : incohérent")
        print("     avec une bifurcation de Hopf (au-dessus du seuil, l'amplitude")
        print("     doit croître comme √(p − p_seuil)).")


def main():
    print("=" * 78)
    print("DIAGNOSTIC DU MODÈLE D'ANCHE (banc_recherche.reed_model)")
    print("=" * 78)
    rm = ReedModel(n_modes=2, zeta=0.01)
    print(f"  cavité {rm.cav.length*1e3:.0f}×{rm.cav.width*1e3:.0f}×"
          f"{rm.cav.height*1e3:.0f} mm · jeu {rm.cav.gap*1e3:.1f} mm · "
          f"cd={rm.cav.cd} · V0={rm.V0*1e6:.1f} cm³")
    print()
    entretenu = diagnostic(rm)
    seuil_hopf(rm)
    print()
    print("=" * 78)
    if not entretenu:
        print("CONCLUSION : le modèle n'auto-oscille pas en l'état.")
        print("Corrections nécessaires : voir docs/vers_un_modele_jouable.md")
        return 1
    print("CONCLUSION : auto-oscillation confirmée.")
    return 0


if __name__ == '__main__':
    sys.exit(main())

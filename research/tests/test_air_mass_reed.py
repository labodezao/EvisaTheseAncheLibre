"""Anche à masse d'air (Adachi 2026) : cohérence interne du modèle.

Lot 1 : équilibre, identités des équations, géométrie, convergence numérique,
Python pur contre numba. Pas encore de validation contre l'article.
Numpy seul ; simulations courtes.
"""
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from banc_recherche import air_mass_reed
from banc_recherche.air_mass_reed import (AirMassReedModel, adachi_c4,
                                          mean_frequency)
from banc_recherche.slot_stack import SlotStack

RACINE = Path(__file__).resolve().parents[1]     # dossier research/


def _modele():
    return AirMassReedModel(adachi_c4(35))


@pytest.mark.parametrize('p0', [100.0, 500.0, 1000.0, 3000.0])
def test_equilibre_annule_la_derivee(p0):
    """À l'équilibre, ẋ, v̇ et U̇ sont nuls et U suit la loi de pertes."""
    m = _modele()
    st = m.equilibrium(p0)
    d = m.deriv(st, p0)
    P = m._P
    w0sq, x_rep = P[0], P[3]
    assert abs(d[0]) <= 1e-9 * math.sqrt(w0sq) * x_rep      # ẋ = v = 0
    assert abs(d[1]) <= 1e-9 * w0sq * x_rep                 # v̇
    # U̇ : échelle g·p0 = S/(ρ d) · p0 (accélération du débit sans pertes)
    S = m.area(st[0])
    echelle = S / (m.p.rho * 0.5 * math.sqrt(S / math.pi)) * p0
    assert abs(d[2]) <= 1e-6 * echelle
    p = m.p
    U = S * math.sqrt(p0 / (p.K_p * p.rho / 2 * S ** 2 / p.chamber_section_m2 ** 2
                            + p.K_r * p.rho / 2))
    assert st[2] == pytest.approx(U, rel=1e-9)


def test_identite_equation_5():
    """p_r = p − ρ (d/S) dU/dt, avec d = 0,5 √(S/π), S = S(x)."""
    m = _modele()
    r = m.simulate(0.2, 1000.0, fs=44100.0, oversample=8)
    S = np.array([m.area(x) for x in r.tip])
    d = 0.5 * np.sqrt(S / math.pi)
    pr = r.chamber_pressure - m.p.rho * d / S * r.dflow
    assert np.allclose(pr, r.reed_pressure, rtol=1e-6, atol=1e-6 * np.abs(r.reed_pressure).max())


@pytest.mark.parametrize('x', [-1e-3, 0.0, 0.3e-3, 2e-3])
def test_aire_equation_4(x):
    m = _modele()
    p = m.p
    attendu = (p.length_m + p.width_m) * math.sqrt(max(x, 0.0) ** 2 + p.gap_m ** 2)
    assert m.area(x) == pytest.approx(attendu, rel=1e-12)


def test_pile_de_fente_se_ferme_puis_se_rouvre():
    pile = SlotStack.accordion(1.0e-3, 0.3e-3, tongue_m=0.3e-3)
    sans = _modele()
    avec = AirMassReedModel(adachi_c4(35, x_rest_m=0.3e-3, stack=pile))
    for x in np.linspace(-1e-3, 2e-3, 13):
        assert avec.area(x) == pytest.approx(sans.area(x), rel=1e-12)
    # sorti de l'autre côté de la plaque : la section se rouvre
    assert avec.area(-2e-3) > avec.area(-0.5e-3)


def test_convergence_en_oversample():
    m = _modele()
    f = [m.simulate(1.0, 1000.0, fs=44100.0, oversample=o).frequency() for o in (4, 16)]
    assert all(np.isfinite(f))
    assert abs(f[0] - f[1]) < 0.01


def _tip_final(dur=0.05):
    m = _modele()
    return float(m.simulate(dur, 1000.0).tip[-1])


def test_python_pur_egale_numba():
    code = ("from banc_recherche import air_mass_reed as a\n"
            "m = a.AirMassReedModel(a.adachi_c4(35))\n"
            "print(repr(float(m.simulate(0.05, 1000.0).tip[-1])))\n")
    env = dict(os.environ, BANC_SANS_NUMBA='1')
    env['PYTHONPATH'] = str(RACINE) + os.pathsep + env.get('PYTHONPATH', '')
    tmp = os.environ.get('BANC_TMP', 'J:/claude/tmp/these-excitateur')
    os.makedirs(tmp, exist_ok=True)
    out = subprocess.run([sys.executable, '-c', code], env=env, cwd=tmp,
                         capture_output=True, text=True, timeout=300)
    assert out.returncode == 0, out.stderr
    pur = float(out.stdout.strip().splitlines()[-1])
    if not air_mass_reed.NUMBA:
        return                      # rien à comparer : ce processus est déjà en Python pur
    ici = _tip_final()
    assert abs(pur - ici) <= 1e-9 * abs(ici)


def test_mean_frequency_sinusoide():
    fs = 44100.0
    t = np.arange(int(fs)) / fs
    assert mean_frequency(np.sin(2 * math.pi * 123.456 * t), fs) == pytest.approx(123.456, abs=1e-4)


def test_chambre_compressible():
    m = AirMassReedModel(adachi_c4(35, chamber_volume_m3=7.9e-6))
    r = m.simulate(0.1, 1000.0, fs=44100.0, oversample=8)
    for a in (r.tip, r.flow, r.chamber_pressure, r.reed_pressure):
        assert np.all(np.isfinite(a))
    st = m.equilibrium(1000.0)
    d = m.deriv(st, 1000.0)
    P = m._P
    assert abs(d[0]) <= 1e-9 * math.sqrt(P[0]) * P[3]
    assert abs(d[1]) <= 1e-9 * P[0] * P[3]
    S = m.area(st[0])
    assert abs(d[2]) <= 1e-6 * S / (m.p.rho * 0.5 * math.sqrt(S / math.pi)) * 1000.0
    assert abs(d[3]) <= 1e-9 * P[15] * st[2]
    assert abs(d[4]) <= 1e-6 * 1000.0 / P[16]


def test_divergence_signalee_ou_finie():
    m = _modele()
    try:
        r = m.simulate(0.05, 1000.0, fs=2000.0, oversample=1)
    except FloatingPointError as e:
        assert 'oversample' in str(e)
    else:
        assert np.all(np.isfinite(r.tip))

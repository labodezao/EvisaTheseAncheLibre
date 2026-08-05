import numpy as np

from banc_recherche import profile as prof


def test_parabola_curvature():
    x = np.linspace(0, 10, 201)
    y = 0.02 * (x - 5) ** 2               # courbure constante d²y/dx² = 0.04
    pr = prof.from_scan(x, y, mm_per_unit=1.0)
    interior = pr.curvature[5:-5]
    assert abs(np.median(interior) - 0.04) < 0.002
    assert pr.max_deflection > 0


def test_detrend_removes_tilt():
    x = np.linspace(0, 10, 101)
    y = 3.0 * x + 1.0                     # pente pure : courbure nulle
    pr = prof.from_scan(x, y, detrend=True)
    assert np.allclose(pr.deflection_mm, 0.0, atol=1e-9)
    assert abs(pr.max_curvature) < 1e-6


def test_parse_scan_lines():
    lines = ["S 0.000 100", "S 0.200 120", "bruit", "S 0.400 140", "S END"]
    pos, val = prof.parse_scan_lines(lines)
    assert list(pos) == [0.0, 0.2, 0.4]
    assert list(val) == [100.0, 120.0, 140.0]

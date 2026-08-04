from banc_recherche import material


def test_young_modulus_roundtrip():
    E0 = 200e9            # acier ~200 GPa
    L, t, rho = 0.020, 0.0005, 7850.0
    f1 = material.resonance_frequency(E0, L, t, rho, mode=1)
    E = material.youngs_modulus(f1, L, t, rho, mode=1)
    assert abs(E - E0) / E0 < 1e-6


def test_higher_mode_roundtrip():
    E0 = 110e9            # laiton ~110 GPa
    L, t, rho = 0.025, 0.0004, 8500.0
    f2 = material.resonance_frequency(E0, L, t, rho, mode=2)
    E = material.youngs_modulus(f2, L, t, rho, mode=2)
    assert abs(E - E0) / E0 < 1e-6


def test_density_from_mass():
    rho = material.density_from_mass(1.57e-3, 0.020, 0.010, 0.001)  # 1.57 g pour 0.2 cm³
    assert abs(rho - 7850.0) < 1.0

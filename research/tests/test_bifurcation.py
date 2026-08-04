import numpy as np

from banc_recherche import bifurcation as bif


def test_hopf_amplitude_fit_recovers_threshold():
    # Branche super-critique : A = sqrt(k (μ − μc)) pour μ > μc.
    mu = np.linspace(0, 10, 200)
    muc, k = 3.0, 0.5
    A = np.sqrt(np.clip(k * (mu - muc), 0, None))
    fit = bif.hopf_amplitude_fit(mu, A, amp_floor=1e-6)
    assert abs(fit.threshold - muc) < 0.1
    assert abs(fit.slope - k) < 0.05
    assert fit.r2 > 0.99


def test_diagram_detects_subcritical_hysteresis():
    mu_up = np.linspace(0, 10, 200)
    mu_dn = mu_up[::-1]
    # démarre à 6 en montée, s'éteint à 4 en descente → hystérésis
    amp_up = (mu_up > 6).astype(float)
    amp_dn = (mu_dn > 4).astype(float)
    bd = bif.diagram(mu_up, amp_up, mu_dn, amp_dn, amp_thresh=0.5)
    assert 5.5 < bd.mu_on < 6.5
    assert 3.5 < bd.mu_off < 4.5
    assert bd.hysteresis > 1.0
    assert bd.kind == "souscritique"


def test_diagram_supercritical_no_hysteresis():
    mu = np.linspace(0, 10, 200)
    A = np.sqrt(np.clip(0.5 * (mu - 3), 0, None))
    bd = bif.diagram(mu, A, mu[::-1], A[::-1], amp_thresh=0.05)
    assert abs(bd.hysteresis) < 0.3
    assert bd.kind == "supercritique"

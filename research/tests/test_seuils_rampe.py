"""Seuils d'auto-entretien sur rampe : démarrage, extinction, plaquage, reprise.

Signaux de synthèse dont on connaît la vérité : une « anche » qui sonne
(harmoniques) entre deux pressions, du souffle (bruit) partout ailleurs.
"""
import numpy as np
import pytest

from banc_recherche import seuil
from banc_recherche.leak import (accumulation_flow, decay_time_s,
                                 equivalent_hole_mm, hole_leak_lpm,
                                 leak_flow_curve)

FS = 16000


def _reed(t, f0=220.0):
    return sum(a * np.sin(2 * np.pi * k * f0 * t)
               for k, a in zip(range(1, 6), (1, .5, .3, .2, .1)))


def test_clarte_separe_note_et_souffle():
    rng = np.random.default_rng(0)
    t = np.arange(FS) / FS
    note = 0.2 * _reed(t) + 0.01 * rng.standard_normal(t.size)
    souffle = 0.2 * rng.standard_normal(t.size)
    fn = seuil.frame_features(note, FS)
    fs_ = seuil.frame_features(souffle, FS)
    assert np.median(fn.clarity) > 0.9
    assert np.median(fs_.clarity) < 0.5
    assert abs(np.nanmedian(fn.f0) - 220.0) < 2.0


def _synth_ramp(p_on=150., p_off=110., p_choke=700., p_unchoke=620.,
                p_max=800., rate=50., seed=1):
    """Rampe 0→p_max→0 à `rate` Pa/s ; l'anche obéit à un automate à
    hystérésis (démarrage/extinction en bas, plaquage/reprise en haut)."""
    rng = np.random.default_rng(seed)
    T = 2 * p_max / rate
    t = np.arange(int(T * FS)) / FS
    p = np.where(t < T / 2, rate * t, p_max - rate * (t - T / 2))
    state = np.zeros(t.size, bool)
    on = False; choked = False
    for i in range(t.size):
        rising = t[i] < T / 2
        if rising:
            if not on and not choked and p[i] >= p_on and p[i] < p_choke:
                on = True
            if on and p[i] >= p_choke:
                on = False; choked = True
        else:
            if choked and p[i] <= p_unchoke:
                choked = False; on = True
            if on and p[i] <= p_off:
                on = False
        state[i] = on
    sig = 0.05 * rng.standard_normal(t.size) * (0.2 + p / p_max)   # souffle
    sig = sig + state * (0.3 * _reed(t))
    return t, p, sig


def _analyse(t, p, sig):
    ft = seuil.frame_features(sig, FS)
    pf = np.interp(ft.t, t, p)
    osc = seuil.oscillating(ft.level_db, ft.clarity, ft.t)
    return seuil.ramp_thresholds(ft.t, pf, osc)


def test_quatre_seuils_sur_une_rampe():
    t, p, sig = _synth_ramp()
    r = _analyse(t, p, sig)
    tol = 6.0     # Pa : une trame de 25 ms à 50 Pa/s + anti-rebond
    assert r.p_on == pytest.approx(150., abs=tol)
    assert r.p_choke == pytest.approx(700., abs=tol)
    assert r.p_unchoke == pytest.approx(620., abs=tol)
    assert r.p_off == pytest.approx(110., abs=tol)
    assert r.choke_reached
    assert r.hysteresis > 0                 # sous-critique
    assert r.usable_range == pytest.approx(550., abs=2 * tol)
    assert r.ratio == pytest.approx(700. / 150., rel=0.06)


def test_sans_plaquage_la_plage_va_au_sommet():
    t, p, sig = _synth_ramp(p_choke=1e9, p_unchoke=1e9, p_max=500.)
    r = _analyse(t, p, sig)
    assert not r.choke_reached
    assert np.isnan(r.p_choke)
    assert r.usable_range == pytest.approx(500. - 150., abs=10.)


def test_retard_capteur_fabrique_une_fausse_hysteresis():
    """Un capteur en retard de 0,4 s à 50 Pa/s lit 20 Pa trop bas en montée
    et 20 Pa trop haut en descente : il **cache** 40 Pa d'hystérésis (ici,
    il en invente une négative). La correction `lag_s` la retire."""
    t, p, sig = _synth_ramp(p_on=150., p_off=150., p_choke=1e9, p_unchoke=1e9,
                            p_max=400.)
    lag = 0.4
    p_late = np.interp(t - lag, t, p)               # ce que lit le capteur
    ft = seuil.frame_features(sig, FS)
    osc = seuil.oscillating(ft.level_db, ft.clarity, ft.t)
    brut = seuil.ramp_thresholds(ft.t, np.interp(ft.t, t, p_late), osc)
    corr = seuil.ramp_thresholds(ft.t, np.interp(ft.t, t, p_late), osc, lag_s=lag)
    assert brut.hysteresis < -25.0
    assert abs(corr.hysteresis) < 10.0


def test_cycles_repetes_et_statistiques():
    t1, p1, s1 = _synth_ramp(seed=1, p_max=800.)
    t2, p2, s2 = _synth_ramp(seed=2, p_max=800.)
    t = np.concatenate([t1, t1[-1] + 1 / FS + t2])
    p = np.concatenate([p1, p2]); sig = np.concatenate([s1, s2])
    ft = seuil.frame_features(sig, FS)
    osc = seuil.oscillating(ft.level_db, ft.clarity, ft.t)
    summ = seuil.cycles_thresholds(ft.t, np.interp(ft.t, t, p), osc)
    assert len(summ.cycles) == 2
    assert summ.mean["p_on"] == pytest.approx(150., abs=6.)
    assert summ.mean["p_choke"] == pytest.approx(700., abs=6.)


def test_extrapolation_a_vitesse_nulle():
    rates = [5., 10., 20., 40.]
    p_on = [150. + 0.3 * r for r in rates]          # retard proportionnel
    p0, slope = seuil.zero_rate_threshold(rates, p_on)
    assert p0 == pytest.approx(150., abs=1e-6)
    assert slope == pytest.approx(0.3, abs=1e-6)


def test_loi_de_debit_orifice():
    p = np.linspace(50, 1500, 40)
    q = 0.8 * p ** 0.5
    c, n, r2 = seuil.flow_law(p, q)
    assert n == pytest.approx(0.5, abs=1e-6) and c == pytest.approx(0.8, rel=1e-6)
    # 20 mm² sous 900 Pa ≈ 46 L/min : l'aire efficace se retrouve.
    q_m3s = 20e-6 * np.sqrt(2 * 900 / 1.2)
    assert seuil.effective_area_mm2(900., q_m3s) == pytest.approx(20., rel=1e-6)


def test_deux_anches_separees_et_comparees():
    t = np.arange(int(1.5 * FS)) / FS
    a = np.sin(2 * np.pi * 220 * t)
    b = 0.5 * np.sin(2 * np.pi * 330 * t) * (t > 0.75)       # B entre à 0,75 s
    tt, lv = seuil.reed_presence(a + b, FS, [220., 330.], frame_s=0.25, hop_s=0.05)
    early, late = tt < 0.5, tt > 1.0
    assert lv[late, 1].mean() - lv[early, 1].mean() > 30     # B apparaît
    assert abs(lv[late, 0].mean() - lv[early, 0].mean()) < 1  # A ne bouge pas
    with pytest.raises(ValueError):
        seuil.reed_presence(a, FS, [440., 443.], frame_s=0.25)  # musette trop serrée
    cmp = seuil.compare_pair(150., 180., 130., q_a=5., q_b=6., q_pair=10.)
    assert cmp.help_pa == pytest.approx(20.) and cmp.q_excess == pytest.approx(-1.)


def test_analyse_run_depuis_traces_alignees():
    t, p, sig = _synth_ramp(rate=100.)
    ft = seuil.frame_features(sig, FS)
    pf = np.interp(ft.t, t, p)
    q = 0.9 * np.sqrt(pf)                      # L/min, loi d'orifice
    res = seuil.analyse_run(ft.t, pf, ft.level_db, ft.clarity, q=q)
    assert res.summary.mean["p_on"] == pytest.approx(150., abs=10.)
    assert res.flow[1] == pytest.approx(0.5, abs=0.02)


# ---- Fuites : débit, trou équivalent, critères en secondes --------------
def test_chute_de_pression_donne_le_debit_et_le_type_de_fuite():
    V = 2e-3                                   # 2 L (pièce + bouteille tampon)
    for n_true, c in ((0.5, 5e-4), (1.0, 1e-5)):   # c : L/min à 1 Pa^n
        t = np.linspace(0, 60, 3001)
        p = np.empty_like(t); p[0] = 800.
        for i in range(1, t.size):             # dp/dt = -(p_atm/V)·q
            q = c * p[i - 1] ** n_true / 60000.
            p[i] = p[i - 1] - 101325. / V * q * (t[i] - t[i - 1])
        lf = leak_flow_curve(t, p, V, p_ref=500.)
        assert lf.n == pytest.approx(n_true, abs=0.03)
        assert lf.q_ref_lpm == pytest.approx(c * 500. ** n_true, rel=0.03)


def test_trou_equivalent_et_temps_de_chute():
    q = hole_leak_lpm(1.0, 500.)               # trou de 1 mm sous 500 Pa
    assert 0.7 < q < 0.95                      # ~0,8 L/min
    assert equivalent_hole_mm(q, 500.) == pytest.approx(1.0, rel=1e-6)
    # Plus le volume est grand, plus la chute est lente (proportionnel).
    t1 = decay_time_s(0.5, 1e-3)
    t5 = decay_time_s(0.5, 5e-3)
    assert t5 == pytest.approx(5 * t1, rel=1e-9)


def test_cloche_d_accumulation():
    V = 20e-6                                  # cloche de 20 cm³
    q_true = 1e-3                              # L/min
    t = np.linspace(0, 10, 101)
    p = 101325. / V * (q_true / 60000.) * t    # montée linéaire
    assert accumulation_flow(t, p, V) == pytest.approx(q_true, rel=1e-6)

"""Anche fermée par le souffle derrière un volume amont fini (`upstream_reed`).

Paramètres centraux SUPPOSÉS du module (levée 0,4 mm, plaque 1,0 mm, jeu 30 µm,
R_s 3·10⁶, V_d 1 cm³, orifice 25 mm² sur 6 mm), lame de laiton uniforme
équivalente, sans tuyau. Stabilité linéaire surtout ; quelques simulations
courtes. Numpy seul (numba accélère si présent).
"""
import math

import numpy as np
import pytest

from banc_recherche.coupled_reeds import (CoupledReedsModel, Orifice, ReedSetting,
                                          Voicing)
from banc_recherche.reed_oscillator import Chamber, FreeReedModel, Slot
from banc_recherche.upstream_reed import (BRASS_E_PA, BRASS_RHO, ZETA, Blade,
                                          UpstreamReed)

NOTES = {'Fa3': 174.61, 'Do4': 261.63, 'Fa4': 349.23, 'Fa5': 698.46}


def reed(note, volume_cm3, **kw):
    return UpstreamReed(Blade.for_note(NOTES[note]), upstream_volume_m3=volume_cm3 * 1e-6, **kw)


def band(note, volume_cm3, **kw):
    return reed(note, volume_cm3, **kw).instability_band()


def kinds(crossings):
    return [c.kind for c in crossings]


def free_reed(blade, **kw):
    sec = np.array([[blade.length_m, BRASS_RHO, blade.width_m, blade.thickness_m, BRASS_E_PA]])
    return FreeReedModel(sections=sec, n_modes=1, zeta=ZETA, **kw)


# ---- a. référence : CoupledReedsModel ---------------------------------------
HOLE, PALLET, VN, VD = Orifice(25e-6, 6e-3), Orifice(3e-4, 0.010), 4e-6, 1e-6


@pytest.fixture(scope='module')
def reference():
    """Volume amont énorme, R_s minuscule : la pression à l'anche est celle de
    la source, comme dans `CoupledReedsModel`. Le réseau aval (V_d, trou, canal
    V_n, clapet) est le même des deux côtés."""
    u = reed('Fa3', 1e6, source_resistance=10.0, downstream_volume_m3=VD,
             stage2=(VN, HOLE, PALLET))
    b, st = u.blade, u.setting
    r1 = free_reed(b, slot=Slot(width_m=b.width_m))
    voicing = Voicing(chamber_m3=VD, hole=HOLE, channel_m3=VN, pallet=PALLET, shared_chamber=True)
    model = CoupledReedsModel(reeds=[r1, r1], voicing=voicing, settings=[st, st],
                              muted=(False, True), sweep=1.0, zeta=ZETA)
    idx = [1, 4, 5, 6, 7]                      # x1, p_ch, q_h, p_n, q_p
    scale = np.array([1e-4, 10, 1e-5, 10, 1e-5])
    rows = [0, 4, 5, 6, 7]                     # équations : bilan des forces, p_ch, q_h, p_n, q_p
    norm = np.array([model.k[0] / model.m[0] * 1e-4, 1e5, 1e5, 1e5, 1e5])

    def repo_growth(p0):
        s, _ = u.equilibrium(p0)
        w = np.array([s[1], s[3], s[4], s[5], s[6]]) / scale

        def f(w_):
            full = np.zeros(10)
            full[idx] = w_ * scale
            return np.array(model.deriv(list(full), p0))[rows] / norm
        for _ in range(30):                    # Newton, jacobien numérique
            jac = np.array([(f(w + 1e-7 * e) - f(w - 1e-7 * e)) / 2e-7 for e in np.eye(5)]).T
            dw = np.linalg.solve(jac, -f(w))
            w = w + dw
            if np.abs(dw).max() < 1e-12:
                break
        full = np.zeros(10)
        full[idx] = w * scale
        scl = np.array([0.1, 1e-4, 0.1, 1e-4, 100, 1e-5, 100, 1e-5, 1e-5, 1e-5])
        jac = np.zeros((10, 10))
        for j in range(10):
            h = 1e-5 * scl[j]
            a, c = full.copy(), full.copy()
            a[j] += h
            c[j] -= h
            jac[:, j] = (np.array(model.deriv(list(a), p0)) - np.array(model.deriv(list(c), p0))) / (2 * h)
        ev = np.linalg.eigvals(jac)
        i = int(np.argmax(ev.real))
        return float(ev[i].real), abs(float(ev[i].imag)) / (2 * math.pi)

    def crossing(lo, hi):
        sgn = repo_growth(lo)[0] > 0
        for _ in range(40):
            mid = math.sqrt(lo * hi)
            if (repo_growth(mid)[0] > 0) == sgn:
                lo = mid
            else:
                hi = mid
        return math.sqrt(lo * hi)

    on, off = crossing(5.0, 40.0), crossing(300.0, 600.0)
    return u, on, off, repo_growth(on * 1.0005)[1]


def test_reference_coupled_reeds(reference):
    u, on, off, f_on = reference
    mine = u.instability_band(1.0, 4000.0)
    assert kinds(mine) == ['demarrage', 'fin']
    assert mine[0].p0_pa == pytest.approx(on, rel=1e-3)        # 13,875 contre 13,874 Pa
    assert mine[1].p0_pa == pytest.approx(off, rel=1e-3)       # 472,046 Pa
    assert mine[0].f_hz == pytest.approx(f_on, rel=1e-3)       # 173,18 Hz


def test_reference_amplitude_300_pa(reference):
    """1,6932 mm : amplitude établie de `CoupledReedsModel` à 300 Pa (même
    réseau ; simulation de 1,5 s relevée une fois, trop longue pour un test)."""
    r = reference[0].simulate(300.0)
    assert r.status == 'etabli'
    assert r.amplitude_m * 1e3 == pytest.approx(1.6932, rel=3e-3)


# ---- b. fait d'atelier 1 : volume amont et démarrage ------------------------
@pytest.mark.parametrize('note', ['Do4', 'Fa4'])
def test_atelier_1_grave_muet_a_30_parle_a_336(note):
    assert band(note, 30) == []
    assert 'demarrage' in kinds(band(note, 336))


def test_atelier_1_fa5_parle_a_121_et_plus_bas_a_336():
    assert band('Fa5', 30) == []
    on121 = band('Fa5', 121)[0]
    on336 = band('Fa5', 336)[0]
    assert on121.kind == on336.kind == 'demarrage'
    assert on336.p0_pa < on121.p0_pa                          # 522 contre 666 Pa


# ---- c. fait d'atelier 2 : amplitude à pression donnée ----------------------
def test_atelier_2_amplitude_plus_petite_a_121_qu_a_336():
    a121 = reed('Fa5', 121).simulate(1000.0)
    a336 = reed('Fa5', 336).simulate(1000.0)
    assert a121.status == a336.status == 'etabli'
    assert a121.amplitude_m < a336.amplitude_m                # 0,559 contre 0,707 mm


# ---- d. fait d'atelier 3 : plaquage ------------------------------------------
def test_atelier_3_l_instabilite_cesse_bout_a_la_levee():
    fins = [c for note, v in (('Do4', 336), ('Fa4', 336), ('Fa4', 121))
            for c in band(note, v) if c.kind == 'fin']
    assert len(fins) == 3
    assert all(0.85 <= c.y_sur_levee <= 1.0 for c in fins)    # 0,98 ; 0,99 ; 0,89


def test_atelier_3_plaquage_monte_avec_la_levee():
    def fin(lift):
        b = Blade.for_note(NOTES['Fa4'])
        st = ReedSetting(lift_m=lift, tongue_m=b.thickness_m, plate_m=1e-3, clearance_m=30e-6)
        c = UpstreamReed(b, st, upstream_volume_m3=336e-6).instability_band()
        return [x for x in c if x.kind == 'fin'][0].p0_pa
    assert fin(0.3e-3) < fin(0.5e-3)                          # 1440 contre 2409 Pa


# ---- e. la note jouée --------------------------------------------------------
def test_note_sous_la_lame_et_baisse_avec_la_pression():
    u = reed('Fa4', 336)
    r6, r10 = u.simulate(600.0), u.simulate(1000.0)
    assert r6.status == r10.status == 'etabli'
    assert r10.f_hz < r6.f_hz < u.blade.f0_hz                 # 345,2 puis 343,0 pour 349,2 Hz


# ---- f. contraste : la loi qui OUVRE donne l'inverse -------------------------
def _free_reed_p_on(volume_cm3):
    b = Blade.for_note(NOTES['Fa4'])
    r = free_reed(b, slot=Slot(width_m=b.width_m), chamber=Chamber(volume_m3=volume_cm3 * 1e-6))
    return r.hopf_threshold()[1]


def test_contraste_free_reed_model_seuil_monte_avec_le_volume():
    """`FreeReedModel` (le souffle ouvre) : seuil 74 Pa à 30 cm3, 828 Pa à
    121 cm3. L'atelier voit l'inverse (muet à 30, parle à 121 ou 336) : la
    cause est le sens de la loi, pas un réglage."""
    assert _free_reed_p_on(30) < _free_reed_p_on(121)
    assert band('Fa4', 30) == [] and band('Fa4', 121) != []   # loi fermée : l'inverse


def test_contraste_etouffement_proportionnel_a_max_open_moins_levee():
    b = Blade.for_note(NOTES['Fa4'])
    rapport = []
    for lev in (0.05e-3, 0.1e-3, 0.2e-3, 0.4e-3):
        slot = Slot(width_m=b.width_m, rest_offset_m=lev, max_open_m=0.5e-3)
        haut = free_reed(b, slot=slot).instability_band()[1]
        rapport.append(haut[1] / (0.5e-3 - lev))
    assert max(rapport) / min(rapport) == pytest.approx(1.0, abs=0.02)


# ---- constructeur de lame ----------------------------------------------------
def test_lame_pour_note_joue_la_note():
    assert Blade.for_note(698.46).f0_hz == pytest.approx(698.46, rel=3e-3)
    direct = Blade(m=1e-4, k=1e-4 * (2 * math.pi * 200.0) ** 2, gamma=5e-5)
    assert direct.f0_hz == pytest.approx(200.0)

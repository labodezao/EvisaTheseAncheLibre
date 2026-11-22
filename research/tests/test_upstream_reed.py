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
from banc_recherche import upstream_reed as ur
from banc_recherche.upstream_reed import (BRASS_E_PA, BRASS_RHO, ZETA, Blade,
                                          UpstreamReed, added_air_mass)

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


# ---- g. inertie de la fente (Ricot, Caussé, Misdariis 2005) -------------------
def _blade_eig(u, p0):
    """Valeur propre de la lame (la plus proche de sa fréquence propre, à
    partie imaginaire positive) à l'équilibre de pression `p0`."""
    s, _ = u.equilibrium(p0)
    ev = np.linalg.eigvals(u.jacobian(s, p0))
    w0 = 2.0 * math.pi * u.blade.f0_hz
    cand = [e for e in ev if 0.5 * w0 < e.imag < 1.5 * w0]
    return max(cand, key=lambda e: e.real)


def _sigma(u, p0, t_end=1.0, dt=2e-6):
    """Taux de croissance mesuré en simulation (pente du log de l'enveloppe,
    maxima de |bout - équilibre| après 0,05 s), depuis un kick de 1 µm."""
    t, y, _, _, _ = u.trace(p0, t_end, dt=dt)
    s_eq, _ = u.equilibrium(p0)
    d = np.abs(y - u._par[ur.P_PHI] * s_eq[1])
    pk = np.where((d[1:-1] >= d[:-2]) & (d[1:-1] > d[2:]) & (t[1:-1] > 0.05))[0] + 1
    return float(np.polyfit(t[pk], np.log(d[pk]), 1)[0])


def test_inertie_limite_k0_nul_rejoint_le_modele_sans_inertie():
    """`L_r -> 0` : seuils, plaquage et fréquences du modèle quasi stationnaire."""
    ref = band('Fa4', 336)
    inert = band('Fa4', 336, gap_inertia='ricot', k0=1e-6)
    assert kinds(inert) == kinds(ref) == ['demarrage', 'fin']
    for a, b in zip(inert, ref):
        assert a.p0_pa == pytest.approx(b.p0_pa, rel=0.02)
        assert a.f_hz == pytest.approx(b.f_hz, rel=0.02)
    r0 = reed('Fa4', 336).simulate(600.0)
    r1 = reed('Fa4', 336, gap_inertia='ricot', k0=1e-6).simulate(600.0)
    assert r0.status == r1.status == 'etabli'
    assert r1.amplitude_m == pytest.approx(r0.amplitude_m, rel=0.02)
    assert r1.f_hz == pytest.approx(r0.f_hz, rel=0.02)


def test_inertie_k0_geometrique_et_option_invalide():
    u = reed('Fa4', 336, gap_inertia='ricot', k0=None, inertia_reach_m=5e-3)
    e = math.sqrt(u.lift_m ** 2 + 30e-6 ** 2)                 # bout au repos : h = levée
    w_eff = u._par[ur.P_WEFF]
    assert u.gap_inertance(0.0) == pytest.approx(1.2 * math.log(2 * 5e-3 / e) / math.pi / w_eff,
                                                 rel=1e-12)
    assert reed('Fa4', 336, gap_inertia='ricot', k0=4.5).gap_inertance(0.0) == \
        pytest.approx(1.2 * 4.5 / w_eff, rel=1e-12)
    with pytest.raises(ValueError):
        reed('Fa4', 336, gap_inertia='autre')


def test_inertie_pas_de_temps_divise_par_deux():
    """Convergence : amplitude après 0,3 s à 600 Pa (K0 géométrique), pas de
    2 µs contre 1 µs, à 2 %."""
    u = reed('Fa4', 336, gap_inertia='ricot', k0=None)
    amp = []
    for dt in (2e-6, 1e-6):
        y = u.trace(600.0, 0.3, dt=dt)[1]
        amp.append(0.5 * (y[-3000:].max() - y[-3000:].min()))
    assert amp[0] > 3e-6                                      # la lame a démarré
    assert amp[0] == pytest.approx(amp[1], rel=0.02)


# -- b. solution connue : amortissement négatif à pression imposée --------------
def _fixed_pressure_reed(zeta=ZETA):
    """Lame réelle de Fa3, volumes énormes, `sweep = 0` : Δp imposé."""
    b = Blade(m=0.1311e-3, k=157.8, gamma=30.0e-6, zeta=zeta)
    st = ReedSetting(lift_m=0.4e-3, tongue_m=1e-3, plate_m=1e-3, clearance_m=30e-6)
    return UpstreamReed(b, st, upstream_volume_m3=1.0, downstream_volume_m3=1.0,
                        source_resistance=10.0, sweep=0.0, gap_inertia='ricot', k0=4.5)


def _c_neg(u, p0):
    """`alpha·G·V0·L_r·da/dx` à l'équilibre (négatif : da/dx < 0) et `c`."""
    par = u._par
    s, _ = u.equilibrium(p0)
    hx = 1e-9
    dadx = (ur._area_series(s[1] + hx, par)[0] - ur._area_series(s[1] - hx, par)[0]) / (2 * hx)
    part = ur._area_series(s[1], par)[1]
    v0 = math.sqrt(2.0 * (s[2] - s[3]) / par[ur.P_RHO])
    return (par[ur.P_ALPHA] * part * par[ur.P_G] * v0 * u.gap_inertance(s[1]) * dadx,
            par[ur.P_C])


def test_amortissement_negatif_formule_contre_linearisation():
    """`c_neg = alpha·G·V0·L_r·da/dx` : limite basse fréquence. La valeur propre
    donne `c_eff = -2m·Re(lambda)` ; l'écart à `c + c_neg` vient de
    `1/(1 + (omega·tau)^2)`, `tau = L_r·Q/(2Δp)` (relaxation de Q_r)."""
    u = _fixed_pressure_reed()
    m = u.blade.m
    for p0 in (50.0, 100.0, 200.0, 500.0):
        lam = _blade_eig(u, p0)
        s, _ = u.equilibrium(p0)
        cn, c = _c_neg(u, p0)
        c_eff = -2.0 * m * lam.real
        assert c_eff == pytest.approx(c + cn, abs=0.06 * abs(cn))          # formule brute
        tau = u.gap_inertance(s[1]) * s[4] / (2.0 * (s[2] - s[3]))
        corrige = c + cn / (1.0 + (lam.imag * tau) ** 2)
        assert c_eff == pytest.approx(corrige, abs=0.005 * abs(cn))        # avec la relaxation


def test_amortissement_negatif_seuil_simule_a_15_pct_de_l_analytique():
    u = _fixed_pressure_reed()
    lo, hi = 20.0, 1000.0                                     # c + c_neg(p) = 0 par dichotomie
    for _ in range(50):
        mid = math.sqrt(lo * hi)
        cn, c = _c_neg(u, mid)
        lo, hi = (mid, hi) if c + cn > 0 else (lo, mid)
    p_an = math.sqrt(lo * hi)
    assert 50.0 < p_an < 300.0
    s_bas, s_haut = _sigma(u, 0.85 * p_an), _sigma(u, 1.15 * p_an)
    assert s_bas < 0.0 < s_haut                               # le seuil simulé est dans ±15 %
    assert s_haut == pytest.approx(_blade_eig(u, 1.15 * p_an).real, abs=0.05)
    assert s_bas == pytest.approx(_blade_eig(u, 0.85 * p_an).real, abs=0.05)


# -- c. cas de l'article (section V) ---------------------------------------------
def _article_reed(zeta, k0=4.5):
    """Acier (210 GPa, 7850), l = 22,9 mm, h = 2,5 mm, f0 = 795 Hz (épaisseur
    déduite de f0), jeu a = 0,14 mm, levée x0 = 0,2 mm, pression imposée.
    L'article ne donne ni masse ni amortissement : `zeta` reste libre ; la
    plaque (1 mm) n'est pas dans l'article et ne joue pas (la lame n'y entre pas)."""
    e_pa, rho, l, w, f0 = 210e9, 7850.0, 22.9e-3, 2.5e-3, 795.0
    t = f0 * l ** 2 / (0.1615 * math.sqrt(e_pa / rho))
    b = Blade.uniform(l, w, t, e_pa, rho, zeta)
    st = ReedSetting(lift_m=0.2e-3, tongue_m=t, plate_m=1.0e-3, clearance_m=0.14e-3)
    return UpstreamReed(b, st, upstream_volume_m3=1.0, downstream_volume_m3=1.0,
                        source_resistance=10.0, gap_inertia='ricot', k0=k0)


def _article_zeta_limit():
    """Plus grand zeta pour lequel l'équilibre à 40 Pa est instable (valeur
    propre de la lame, dichotomie)."""
    lo, hi = 1e-5, 1e-2
    for _ in range(40):
        mid = math.sqrt(lo * hi)
        if _blade_eig(_article_reed(mid), 40.0).real > 0:
            lo = mid
        else:
            hi = mid
    return math.sqrt(lo * hi)


def test_article_acier_795_hz_oscille_a_40_pa_pour_la_moitie_du_zeta_limite():
    assert _article_reed(0.004).blade.f0_hz == pytest.approx(795.0, rel=2e-3)
    z_lim = _article_zeta_limit()
    assert _blade_eig(_article_reed(1.05 * z_lim), 40.0).real < 0     # au-dessus : plus d'auto-oscillation
    u = _article_reed(0.5 * z_lim)
    r = u.simulate(40.0, dt=4e-6, tmax=3.0)
    assert r.amplitude_m > 1e-4                                       # >> kick de 1 µm : elle oscille
    assert r.f_hz == pytest.approx(795.0, rel=0.01)


def test_masse_d_air_ajoutee_eq_9():
    l, h, rho = 22.9e-3, 2.5e-3, 1.2
    ref = 8 / (9 * math.pi) * rho * l * h * (l * l + l * h + h * h) / (l + h)
    assert added_air_mass(l, h, rho) == pytest.approx(ref, rel=1e-12)
    assert added_air_mass(l, h, rho) < 0.02 * Blade.uniform(l, h, 0.5e-3, 210e9, 7850.0).m

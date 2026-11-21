"""Étage soufflet : le geste du bras devient une pression bornée.

Trois comportements demandés (Ewen, 20/11/2026) : une demande en marche donne
une rampe bornée, un changement de sens produit son creux, un trémolo plus
rapide que la main est lissé. Les seuils des tests se déduisent des
paramètres de l'étage, pas d'un réglage pour que ça passe.
"""
import ctypes

import numpy as np
import pytest

from banc_recherche import hybrid, live, soufflet as so

FS = 2000.0


def _t(dur):
    return np.arange(int(dur * FS)) / FS


def _pente_db(x, fs=FS):
    db = 20.0 * np.log10(np.maximum(np.abs(x), 1e-9))
    return np.diff(db) * fs


def _t_bras_min(s, p):
    """Temps minimal du bras pour aller de 0 à p : linéaire puis en dB."""
    g = s.p_genou_pa
    if p <= g:
        return p / g / s.k_montee
    return (1.0 + np.log(p / g)) / s.k_montee


# -- bornes sourcées ------------------------------------------------------------
def test_chaque_borne_a_sa_source_et_son_statut():
    for cle, b in so.BORNES.items():
        assert b["statut"] in so.STATUTS, cle
        assert b["source"].strip(), cle
        assert b["unite"], cle
        assert b["valeur"] is not None, cle
    # ce qui n'est ni mesuré ni écrit est provisoire, et le JSON le dit
    j = so.bornes_json()
    assert j["temps_mort_inversion_s"]["provisoire"]
    assert j["gamma_niveau_pression"]["statut"] == "non décidé"
    assert not j["pente_montee_db_s"]["provisoire"]


def test_souplesse_et_fuite_retrouvent_les_chiffres_ecrits():
    # 10 L : 7e-8 m³/Pa ; 1 L/min à 500 Pa : un trou d'un peu plus de 1 mm
    assert so.souplesse_air(0.010) == pytest.approx(7.08e-8, rel=0.01)
    d = 2.0 * np.sqrt(so.section_fuite(1.0, 500.0, 0.61) / np.pi)
    assert 1.0e-3 < d < 1.2e-3
    s = so.Soufflet()
    assert s.debit_fuite(500.0) == pytest.approx(1.0 * so.L_MIN, rel=1e-9)


# -- 1. marche → rampe bornée ------------------------------------------------------
def test_une_marche_donne_une_rampe_bornee():
    s = so.Soufflet()
    t = _t(1.5)
    d = np.where(t >= 0.1, 1000.0, 0.0)
    d[t >= 0.9] = 0.0
    r = s.simuler(d, FS, n_anches=3)

    # le bras tient exactement les pentes mesurées, au-dessus du genou
    # (les deux bouts de chaque pas au-dessus : sous le genou, la pente est
    # en Pa/s, et un pas qui le traverse mélange les deux lois)
    g = s.p_genou_pa
    haut = (np.abs(r.p_bras[1:]) > g) & (np.abs(r.p_bras[:-1]) > g)
    pb = _pente_db(r.p_bras)[haut]
    assert pb.max() <= s.montee_db_s / s.gamma + 1e-6
    assert pb.min() >= -s.descente_db_s / s.gamma - 1e-6

    # la pression suit ; la résistance de la source et la souplesse ajoutent
    # un peu (la fuite des anches change avec p) : 25 % au plus
    hp = (np.abs(r.p[1:]) > g) & (np.abs(r.p[:-1]) > g)
    pp = _pente_db(r.p)[hp]
    assert pp.max() <= 1.25 * s.montee_db_s / s.gamma
    assert pp.min() >= -1.25 * s.descente_db_s / s.gamma

    # pas d'échelon : la pression ne précède jamais le bras
    tenue = r.p[(t > 0.6) & (t < 0.9)]
    p_fin = tenue.mean()
    i90 = np.argmax(r.p >= 0.9 * p_fin)
    t90 = r.t[i90] - 0.1
    assert t90 >= _t_bras_min(s, 0.9 * p_fin)
    assert t90 <= _t_bras_min(s, 0.9 * p_fin) + 0.1      # mais elle y arrive
    assert r.p.max() <= 1.01 * p_fin                     # sans dépassement

    # trois anches ouvertes font baisser la pression (source à résistance
    # interne, 04_soufflet_fr.md l. 9)
    assert p_fin < 1000.0
    r0 = so.Soufflet().simuler(d, FS, n_anches=0)
    assert r0.p[(t > 0.6) & (t < 0.9)].mean() > p_fin


# -- 2. changement de sens → creux ------------------------------------------------
def test_un_changement_de_sens_produit_son_creux():
    s = so.Soufflet()
    t = _t(2.0)
    d = np.where(t < 1.0, 1000.0, -1000.0)
    r = s.simuler(d, FS, n_anches=3)
    p_fin = abs(r.p[(t > 0.7) & (t < 1.0)].mean())

    # le bras reste à force nulle pendant le temps mort, ni plus ni moins
    zero = (r.p_bras == 0.0) & (t > 0.5)
    assert abs(zero.sum() / FS - s.temps_mort_s) <= 2.0 / FS

    # la pression passe par zéro : un vrai creux, pas un fondu
    fen = (t > 0.9) & (t < 1.7)
    assert np.abs(r.p[fen]).min() < 0.01 * p_fin

    # durée sous le genou : au moins la traversée linéaire du bras et le
    # temps mort, moins le retard de l'air
    sous = (np.abs(r.p[fen]) < s.p_genou_pa).sum() / FS
    t_min = 1.0 / s.k_descente + s.temps_mort_s + 1.0 / s.k_montee
    assert sous >= t_min - 2.0 * s.tau_air

    # puis l'autre sens, à la même pression
    assert r.p[-1] < 0
    assert abs(r.p[-1]) == pytest.approx(p_fin, rel=0.02)


def test_le_temps_mort_n_existe_qu_au_changement_de_sens():
    """Relâcher puis repousser repart aussitôt ; relâcher puis tirer attend."""
    t = _t(1.5)

    def depart(signe):
        d = np.where(t < 0.5, 1000.0, 0.0)
        d[t >= 0.8] = signe * 1000.0
        r = so.Soufflet().simuler(d, FS)
        return r.t[np.argmax((t > 0.8) & (np.abs(r.p_bras) > 50.0))]

    s = so.Soufflet()
    ecart = depart(-1.0) - depart(+1.0)
    assert s.temps_mort_s - 1.0 / FS <= ecart <= s.temps_mort_s + 3.0 / FS


# -- 3. trémolo trop rapide → lissé -------------------------------------------------
def _profondeur(s, f, dur=2.0):
    t = _t(dur)
    d = 1000.0 * (1.0 + 0.5 * np.sin(2 * np.pi * f * t))
    r = s.simuler(d, FS, n_anches=3)
    w = t > 1.0
    return np.ptp(r.p[w]) / np.ptp(d[w])


def test_un_tremolo_plus_rapide_que_la_main_est_lisse():
    s = so.Soufflet()
    lent = _profondeur(s, 1.0)
    rapide = _profondeur(s, 12.0)            # au-delà de la bande de 8 Hz
    assert lent > 0.9                        # le bras suit un geste lent
    assert rapide < 0.5                      # pas un trémolo de 12 Hz
    assert rapide < 0.5 * lent


def test_un_secouement_de_soufflet_trop_rapide_ne_monte_pas():
    """Poussé-tiré à 12 Hz (24 changements de sens par seconde)."""
    s = so.Soufflet()
    t = _t(1.5)
    for f, attendu in ((1.0, 0.9), (12.0, None)):
        d = 1000.0 * np.sign(np.sin(2 * np.pi * f * t) + 1e-12)
        r = s.simuler(d, FS, n_anches=3)
        crete = np.abs(r.p[t > 0.5]).max()
        if attendu:
            assert crete > attendu * 900.0
        else:
            assert crete < s.p_genou_pa      # reste sous le genou
            assert crete < 0.2 * 1000.0


# -- branchement dans la chaîne ------------------------------------------------------
def test_niveau_pour_traduit_dans_l_unite_de_la_voix():
    ex = hybrid.FreeReedExciter()
    assert so.niveau_pour(ex, -580.0) == pytest.approx(580.0 / ex.source_impedance)
    assert so.niveau_pour(hybrid.SingleReedExciter(), 1200.0) == pytest.approx(1200.0)
    with pytest.raises(ValueError):
        so.niveau_pour(hybrid.BowExciter(), 100.0)
    with pytest.raises(ValueError):
        so.niveau_pour(hybrid.FreeReedExciter(source_impedance=np.inf), 100.0)


def test_pression_demandee_suit_la_loi_du_rendu():
    # gain (cc/127)² au rendu, niveau ∝ p^gamma : p = p_max·e^(2/gamma)
    assert so.pression_demandee(1.0, 1, 3000.0) == pytest.approx(3000.0)
    assert so.pression_demandee(0.5, -1, 3000.0) == pytest.approx(-750.0)
    assert so.pression_demandee(0.0, 1, 3000.0) == 0.0


def test_la_voix_accepte_une_commande_qui_varie():
    voix = hybrid.build('accordeon', 220.0)
    lv = 2.9e-6
    a = voix.simulate(0.02, fs=11025, level=lv, oversample=4)
    b = voix.simulate(0.02, fs=11025, level=np.full(int(0.02 * 11025), lv),
                      oversample=4)
    np.testing.assert_allclose(a.response, b.response)
    with pytest.raises(ValueError):
        voix.simulate(0.02, fs=11025, level=np.ones(3), oversample=4)


def test_jouer_geste_soufflet_voix():
    """Toute la chaîne : sans pression, rien ; en poussant, la voix parle."""
    voix = hybrid.build('accordeon', 220.0)
    fs_s = 2000.0
    n = int(0.25 * fs_s)
    muet, _ = so.jouer(voix, np.zeros(n), fs=11025, fs_soufflet=fs_s,
                       oversample=4)
    assert np.max(np.abs(muet.response)) < 1e-2
    t = np.arange(n) / fs_s
    pousse = np.where(t > 0.01, 600.0, 0.0)
    res, rs = so.jouer(voix, pousse, fs=11025, fs_soufflet=fs_s, oversample=4)
    # la commande de la voix est la pression du soufflet derrière R
    p_audio = np.interp(res.t, rs.t, rs.p)
    np.testing.assert_allclose(res.level,
                               np.abs(p_audio) / voix.exciter.source_impedance)
    assert np.max(np.abs(res.response)) > 10 * np.max(np.abs(muet.response))


# -- live.Synth : le pont Python, sans le moteur C ------------------------------------
class _MoteurFactice:
    """Remplace le C : rend le niveau reçu, pour lire ce que la voix reçoit."""

    def hv_reset(self, state):
        pass

    def hv_render(self, params, state, level, out, n):
        out[:n] = level.value


@pytest.fixture
def synth_soufflet(monkeypatch):
    monkeypatch.setattr(live, 'engine_library', lambda force=False: _MoteurFactice())
    params = live._Params()
    params.src_admit = 1.0 / 2.0e8
    inst = live.Instrument(name='accordeon', lo=60, hi=60, samplerate=48000.0,
                           level_default=2.9e-6, control_unit='m³/s')
    inst._params = {60: params}
    return live.Synth(inst, polyphony=2, soufflet=so.Soufflet())


def test_synth_avec_soufflet_pression_commune_et_touche_vivante(synth_soufflet):
    syn = synth_soufflet
    syn.expression = 0.0                    # soufflet au repos
    syn.note_on(60, 127)                     # la vélocité ne change rien
    syn.render(512)
    v = next(v for v in syn.voices if v.note == 60)
    assert v.active and v.tenue             # touche tenue : la voix attend l'air
    syn.expression = np.sqrt(600.0 / syn.p_max)   # demande de 600 Pa
    for _ in range(60):                      # 0,64 s
        syn.render(512)
    assert syn.pression == pytest.approx(600.0, rel=0.1)
    assert v.level == pytest.approx(abs(syn.pression) / 2.0e8, rel=1e-6)
    syn.note_off(60)
    syn.render(512)
    assert v.target == 0.0                   # soupape fermée : plus d'air

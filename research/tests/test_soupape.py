"""La soupape de clavier de l'accordéon : l'ouverture et la fermeture de la touche.

Avant : `Voice.note_on` posait le niveau d'un coup (claquement : la crête des
5 premières ms valait 0,5 à 5,9 fois celle de la tenue) et `note_off` ramenait
la commande à 0 par un glissement par bloc. La soupape est une conductance en
série avec le passage de la source, G = src_admit x a(t), a de 0 à 1 : elle
multiplie l'apport P_s*G ET la fuite -p*G, c'est-à-dire tout le débit de la
source (`hv_exciter`, `q_src *= valve`). Ouverture en demi-cosinus sur
`ouverture_ms`, fermeture de même sur `fermeture_ms`, avancées échantillon par
échantillon dans le C.

Les durées par défaut (`live.OUVERTURE_MS`, `live.FERMETURE_MS`) sont
PROVISOIRES, étalonnées par `soupape/etalonne.py` et `soupape/ferme.py`. Ce que
la mesure ne tient pas n'est pas testé : à 1000 Pa le délai du rang 1 est de 2
à 9 ms, hors de la plage de la banque réelle (13 à 29 ms) ; il est dit dans
`test_delai_du_rang_1_a_1000_pa_hors_plage_est_connu`.
"""
import pathlib

import numpy as np
import pytest

from banc_recherche import embedded as emb
from banc_recherche import hybrid, live

pytestmark = pytest.mark.skipif(
    live._compilateur()[0] is None, reason="pas de compilateur C")

SR = 48000
NOTES = (53, 69, 88)
BLOC = 64
REF = pathlib.Path(__file__).with_name('ref_soupape_ouverte.npz')
#: plage du délai du rang 1 à -6 dB de la banque réelle V3 (13 à 29 ms)
PLAGE_MS = (13.0, 29.0)


def _f(n):
    return 440.0 * 2.0 ** ((n - 69) / 12.0)


@pytest.fixture(scope='module')
def insts():
    return {n: live.build_instrument('accordeon', lo=n, hi=n, accord_timbre=False)
            for n in NOTES}


def _voix(inst, note, P, **kw):
    cp = inst.params_for(note)
    v = live.Voice()
    v.note_on(cp, note, P * float(cp.src_admit), **kw)
    return v


def _rendre(v, duree, silence=0.0):
    bl = np.zeros(BLOC, np.float32)
    out = []
    for _ in range(int(round(duree * SR)) // BLOC):
        bl[:] = 0.0
        v.render(bl, glide=1.0, silence=silence)
        out.append(bl.copy())
    return np.concatenate(out).astype(float)


def _tenue(x):
    return x[int(1.0 * SR):int(2.0 * SR)]


def _rang1(x, f0):
    """Enveloppe du rang 1 : démodulation à f0, moyenne glissante d'une période
    passée deux fois (phase nulle)."""
    t = np.arange(len(x)) / SR
    z = x * np.exp(-2j * np.pi * f0 * t)
    n = int(round(SR / f0))
    w = np.ones(n) / n
    for _ in range(2):
        z = np.convolve(z, w, mode='same')
    return 2.0 * np.abs(z)


def _delai_rang1_ms(x, f0):
    """Temps depuis le début de la note jusqu'à -6 dB du rang 1 de la tenue."""
    e = _rang1(x, f0)
    niveau = np.sqrt(np.mean(_tenue(e) ** 2))
    return float(np.argmax(e >= niveau * 10 ** (-6.0 / 20.0)) / SR * 1000.0)


def _claquement(x):
    """Crête des 5 premières ms / crête de la tenue."""
    return float(np.abs(x[:int(0.005 * SR)]).max() / np.abs(_tenue(x)).max())


def _cents_moyens(x, f_nom, a=1.5, b=2.5):
    """Hauteur du rang 1 sur [a, b] s, en cents re f_nom : pente de la phase."""
    t = np.arange(len(x)) / SR
    z = x * np.exp(-2j * np.pi * f_nom * t)
    n = int(round(SR / f_nom))
    w = np.ones(n) / n
    for _ in range(2):
        z = np.convolve(z, w, mode='same')
    i, j = int(a * SR), int(b * SR)
    ph = np.unwrap(np.angle(z[i:j]))
    pente = np.polyfit(t[i:j], ph, 1)[0]
    return 1200.0 * np.log2((f_nom + pente / (2 * np.pi)) / f_nom)


# -- ouverture ---------------------------------------------------------------

@pytest.mark.parametrize('P', (300.0, 1000.0))
@pytest.mark.parametrize('note', NOTES)
def test_pas_de_claquement_a_l_ouverture_par_defaut(insts, note, P):
    x = _rendre(_voix(insts[note], note, P), 2.5)
    assert _claquement(x) < 0.1


@pytest.mark.parametrize('note', NOTES)
def test_l_echelon_claque_la_mesure_le_voit(insts, note):
    """Contrôle de la mesure : sans soupape (ouverture_ms = 0) le claquement
    dépasse 0,1 à au moins une pression ; sinon l'indice ne verrait rien."""
    c = [_claquement(_rendre(_voix(insts[note], note, P, ouverture_ms=0), 2.5))
         for P in (300.0, 1000.0)]
    assert max(c) > 0.1, c


@pytest.mark.parametrize('note', NOTES)
def test_delai_du_rang_1_dans_la_plage_a_300_pa(insts, note):
    x = _rendre(_voix(insts[note], note, 300.0), 2.5)
    d = _delai_rang1_ms(x, _f(note))
    assert PLAGE_MS[0] <= d <= PLAGE_MS[1], d


def test_delai_du_rang_1_a_1000_pa_hors_plage_est_connu(insts):
    """Écart de la mesure, dit et non masqué : à 1000 Pa l'ouverture par défaut
    ne met pas le rang 1 dans les 13 à 29 ms de la banque réelle. Le jour où
    ça change (loi de durée par pression), ce test doit être réécrit avec la
    mesure, pas ajusté."""
    d = [_delai_rang1_ms(_rendre(_voix(insts[n], n, 1000.0), 2.5), _f(n))
         for n in NOTES]
    assert all(v < PLAGE_MS[0] for v in d), d


def test_la_valeur_par_defaut_est_marquee_provisoire():
    src = pathlib.Path(live.__file__).read_text(encoding='utf-8')
    i = src.index('OUVERTURE_MS = ')
    assert 'PROVISOIRE' in src[max(0, i - 2500):i]
    assert 'NON DÉCIDÉ' in src[max(0, i - 2500):i]


@pytest.mark.parametrize('P', (300.0, 1000.0))
def test_ouverture_nulle_redonne_l_ancien_son(insts, P):
    """`ouverture_ms = 0` : la soupape reste à 1, le son du moteur d'avant, à
    l'échantillon près (référence rendue par le commit précédent). Égal bit à
    bit sur le compilateur de référence (MSVC) ; l'écart toléré, 1e-6 de la
    crête, ne laisse passer que l'arrondi d'un autre compilateur."""
    ref = np.load(REF)['p%d' % P]
    v = _voix(insts[69], 69, P, ouverture_ms=0)
    bl = np.zeros(BLOC, np.float32)
    out = []
    for _ in range(len(ref) // BLOC):
        bl[:] = 0.0
        v.render(bl, glide=1.0, silence=0.0)
        out.append(bl.copy())
    x = np.concatenate(out)
    assert np.max(np.abs(x - ref)) <= 1e-6 * np.max(np.abs(ref))


def test_la_tenue_ne_change_pas_apres_etablissement(insts):
    """Niveau à 0,1 dB et hauteur à 0,1 cent de la tenue sans soupape."""
    for note in NOTES:
        for P in (300.0, 1000.0):
            a = _rendre(_voix(insts[note], note, P), 2.5)
            b = _rendre(_voix(insts[note], note, P, ouverture_ms=0), 2.5)
            na = np.sqrt(np.mean(a[int(1.5 * SR):] ** 2))
            nb = np.sqrt(np.mean(b[int(1.5 * SR):] ** 2))
            assert abs(20 * np.log10(na / nb)) < 0.1, (note, P)
            ha = _cents_moyens(a, _f(note))
            hb = _cents_moyens(b, _f(note))
            assert abs(ha - hb) < 0.1, (note, P, ha, hb)


# -- fermeture ---------------------------------------------------------------

@pytest.mark.parametrize('note', NOTES)
def test_fermeture_sans_saut(insts, note):
    """Au `note_off` la plus grande différence entre deux échantillons ne passe
    pas celle de la tenue : la sortie s'éteint sans claquer."""
    v = _voix(insts[note], note, 300.0)
    x = _rendre(v, 1.5)
    v.note_off()
    y = _rendre(v, 0.3)
    assert np.max(np.abs(np.diff(y))) <= np.max(np.abs(np.diff(x[-4800:])))


@pytest.mark.parametrize('note', NOTES)
def test_la_voix_se_libere_apres_la_fermeture(insts, note):
    v = _voix(insts[note], note, 300.0)
    _rendre(v, 1.0)
    assert v.active
    v.note_off()
    _rendre(v, 0.6, silence=1e-6)
    assert not v.active


def test_la_fermeture_ne_touche_pas_le_niveau_de_la_source(insts):
    """Le soufflet n'est pas la touche : `note_off` ferme la soupape, la
    commande de la source reste ce qu'elle était."""
    v = _voix(insts[69], 69, 300.0)
    niveau = v.level
    _rendre(v, 0.5)
    v.note_off()
    assert v.target == niveau and v.level == niveau
    assert v.state.valve_to == 0.0


# -- soupape fermée ----------------------------------------------------------

@pytest.mark.parametrize('note', NOTES)
def test_soupape_fermee_silence(insts, note):
    """a = 0 : la chambre est isolée de la source, même sous 1000 Pa de
    soufflet, la voix ne sonne pas (sous le seuil de libération du moteur)."""
    v = _voix(insts[note], note, 1000.0)
    live.engine_library().hv_valve_start(live.ctypes.byref(v.state), 0.0, 0.0, 0)
    x = _rendre(v, 0.5)
    assert np.abs(x).max() < 1e-6


# -- la soupape est la même dans le C et dans son miroir Python -----------------

def _params(f0=220.0):
    return emb.params_from_voice(
        hybrid.accordeon(f0_hz=f0, source_impedance=2.0e8), samplerate=float(SR),
        name='accordeon')


def _c(p, niveau, n, ouverture_ms):
    cp, _ = live._to_c_params(p)
    v = live.Voice()
    v.note_on(cp, 57, niveau, ouverture_ms=ouverture_ms)
    bl = np.zeros(256, np.float32)
    out = []
    for _ in range(n // 256):
        v.render(bl, glide=1.0, silence=0.0)
        out.append(bl.copy())
    return np.concatenate(out).astype(float), v


def _valve_c(p, n_ouv, n):
    """La soupape du C, échantillon par échantillon, et le son qui va avec."""
    cp, _ = live._to_c_params(p)
    v = live.Voice()
    v.note_on(cp, 57, 2.9e-6, ouverture_ms=n_ouv / SR * 1000.0)
    bl = np.zeros(1, np.float32)
    seq, out = [], []
    for _ in range(n):
        v.render(bl, glide=1.0, silence=0.0)
        seq.append(float(v.state.valve))
        out.append(float(bl[0]))
    return np.array(seq), np.array(out)


def test_la_soupape_du_c_suit_le_demi_cosinus():
    """La rotation en float32 du C s'écarte du demi-cosinus exact de moins de
    1e-5 (mesuré : 4,3e-6 sur 480 échantillons) et finit exactement à 1."""
    n_ouv = 480
    seq, _ = _valve_c(_params(), n_ouv, n_ouv + 20)
    k = np.arange(1, n_ouv + 21)
    exact = np.where(k >= n_ouv, 1.0, 0.5 * (1.0 - np.cos(np.pi * k / n_ouv)))
    assert np.max(np.abs(seq - exact)) < 1e-5
    assert seq[-1] == 1.0


def test_le_miroir_python_suit_le_c():
    """Le miroir float64, rejoué avec la soupape du C échantillon par
    échantillon, donne le même niveau de tenue (mesuré : 1,2e-6 d'écart
    relatif de RMS sur les 4096 derniers échantillons, 1,6e-6 sans soupape) ;
    la forme d'onde reste à 1e-3 de la crête (mesuré : 1,0e-3 avec soupape,
    2,8e-4 sans : float32 contre float64 déphase la montée, qui est plus longue
    avec la rampe), bornée ici à 3e-3."""
    n, n_ouv = 24576, 480
    p = _params()
    seq, _ = _valve_c(p, n_ouv, n)
    c = _c(p, 2.9e-6, n, n_ouv / SR * 1000.0)[0]
    py = emb.RealtimeVoice(p)
    py.valve_start(0.0, 1.0, n_ouv)
    it = iter(seq)

    def pas():
        py.valve = next(it)
    py._valve_pas = pas
    m, _ = py.render(n, 2.9e-6)
    rms = lambda x: np.sqrt(np.mean(x[-4096:] ** 2))
    assert abs(rms(c) / rms(m) - 1.0) < 1e-4
    fin = slice(4096, None)
    assert np.max(np.abs(c[fin] - m[fin])) / np.max(np.abs(m[fin])) < 3e-3

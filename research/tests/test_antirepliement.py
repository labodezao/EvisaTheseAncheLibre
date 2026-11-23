"""Pas de repliement à la sortie du moteur : le filtre elliptique avant décimation.

Le moteur calcule à 192 kHz (suréchantillonnage 4) et sort à 48 kHz. Sans
filtre (une moyenne de 4 pas), les partiels au-dessus de 24 kHz se repliaient
dans la bande, battaient avec les partiels de la note et faisaient bouger le
centroïde de plusieurs centaines de hertz pour 0,15 cent de décalage de lame
(note 57, lame large : raies repliées à -34 dB). On vérifie ici :

- la réponse du filtre (ondulation, atténuation, stabilité en float32) ;
- l'énergie hors harmoniques d'une note tenue, sous un seuil tiré de la mesure
  après correction (avec marge) ; avec l'ancien moteur, elle le dépasse.
"""
import numpy as np
import pytest
from scipy import signal

from banc_recherche import embedded as emb
from banc_recherche import live

SR = 48000.0


# -- le filtre ----------------------------------------------------------------

def _sos6(n, sr=SR):
    return np.array([[c[0], c[1], c[2], 1.0, c[3], c[4]]
                     for c in emb.antirepliement_sos(n, sr)])


def test_pas_de_filtre_sans_surechantillonnage():
    assert emb.antirepliement_sos(1, SR) == []


@pytest.mark.parametrize('n', [2, 4, 8])
def test_la_reponse_du_filtre_tient_son_cahier_des_charges(n):
    fs = SR * n
    sos = _sos6(n)
    assert len(sos) <= emb.HV_MAX_AA
    f = np.concatenate([np.linspace(1.0, 18000.0, 1000),
                        np.linspace(28000.0, fs / 2.0, 4000)])
    _, h = signal.sosfreqz(sos, worN=f, fs=fs)
    db = 20 * np.log10(np.abs(h))
    assert np.max(np.abs(db[:1000])) < 0.1        # ondulation jusqu'à 18 kHz
    assert np.max(db[1000:]) <= -80.0             # >= 80 dB à partir de 28 kHz


@pytest.mark.parametrize('n', [2, 4, 8])
def test_le_filtre_est_stable_et_tient_en_float32(n):
    """Pôles dans le cercle unité, coefficients arrondis en float32 : la bande
    passante bouge de moins de 0,01 dB et le cahier des charges tient encore
    (ondulation < 0,1 dB, atténuation >= 80 dB). Dans la bande atténuée on ne
    compare pas les deux réponses point à point : elles y passent par des zéros."""
    fs = SR * n
    sos = _sos6(n)
    sos32 = sos.astype(np.float32).astype(np.float64)
    for r in sos32:
        assert np.max(np.abs(np.roots([1.0, r[4], r[5]]))) < 1.0
    fp = np.linspace(1.0, 18000.0, 1000)
    fa = np.linspace(28000.0, fs / 2.0, 4000)
    _, p64 = signal.sosfreqz(sos, worN=fp, fs=fs)
    _, p32 = signal.sosfreqz(sos32, worN=fp, fs=fs)
    assert np.max(np.abs(20 * np.log10(np.abs(p32) / np.abs(p64)))) < 0.01
    assert np.max(np.abs(20 * np.log10(np.abs(p32)))) < 0.1
    _, a32 = signal.sosfreqz(sos32, worN=fa, fs=fs)
    assert np.max(20 * np.log10(np.abs(a32))) <= -80.0
    # et l'état en float32, sur du bruit : l'erreur reste 100 dB sous le signal
    rng = np.random.default_rng(0)
    x = rng.standard_normal(6000).astype(np.float32)
    z = np.zeros((len(sos), 2), np.float32)
    c = sos.astype(np.float32)
    y = np.empty(len(x), np.float32)
    for i, v in enumerate(x):
        for k in range(len(c)):
            o = c[k, 0] * v + z[k, 0]
            z[k, 0] = c[k, 1] * v - c[k, 4] * o + z[k, 1]
            z[k, 1] = c[k, 2] * v - c[k, 5] * o
            v = o
        y[i] = v
    ref = signal.sosfilt(sos, x.astype(np.float64))
    assert (y - ref).std() < 1e-5 * ref.std()


# -- l'énergie hors harmoniques ------------------------------------------------

def _hors_harmoniques_db(x, note):
    """Énergie des bins hors des harmoniques de la note (±3 Hz + 0,02 %), en dB
    sous l'énergie totale, sur 1,5 s à 4 s."""
    f0n = 440.0 * 2 ** ((note - 69) / 12)
    seg = np.asarray(x[int(1.5 * SR):], float)
    nf = 1 << 20
    a = np.abs(np.fft.rfft((seg - seg.mean()) * np.hanning(len(seg)), nf))
    fr = np.fft.rfftfreq(nf, 1 / SR)
    m = (fr > f0n * 0.97) & (fr < f0n * 1.03)
    f0 = fr[np.argmax(np.where(m, a, 0.0))]
    harm = np.zeros(len(fr), bool)
    for k in range(1, int(SR / 2 / f0) + 1):
        harm |= np.abs(fr - k * f0) < 3.0 + 2e-4 * k * f0
    return 10 * np.log10(np.sum(a[~harm] ** 2) / np.sum(a ** 2))


# Mesuré après correction (notes 57 et 84, défaut et lame large : -53,6, -46,0,
# -52,4 et -52,2 dB) puis majoré de 3 dB.
SEUIL_DB = {(57, None): -50.5, (57, 127): -43.0, (84, None): -49.0, (84, 127): -49.0}


@pytest.fixture(scope='module')
def acc():
    return live.build_instrument('accordeon', lo=57, hi=84, accord_timbre=False)


@pytest.mark.skipif(live._compilateur()[0] is None, reason="pas de compilateur C")
@pytest.mark.parametrize('note,largeur', sorted(SEUIL_DB, key=str))
def test_pas_de_repliement_dans_une_note_tenue(acc, note, largeur):
    s = live.Synth(acc, polyphony=1,
                   timbre={'largeur': largeur} if largeur is not None else None)
    s.pression_mesuree = True
    s.expression = 0.5
    s.note_on(note, 100)
    n = int(4.0 * SR)
    x = np.concatenate([s.render(256) for _ in range(n // 256)])
    e = _hors_harmoniques_db(x, note)
    print('note', note, 'largeur', largeur, 'hors harmoniques %.1f dB' % e)
    assert e < SEUIL_DB[(note, largeur)]

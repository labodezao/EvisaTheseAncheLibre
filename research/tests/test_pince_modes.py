"""Son pincé à plusieurs modes (pince_modes), comparaison au modèle (fem/comparer_pince) et
feuille de soufflerie (fem/souffle) : tout sur des signaux de synthèse dont on connaît la réponse."""
import math
import os
import sys
import wave

import numpy as np
import pytest

from banc_recherche import pince_modes as pm

FEM = os.path.join(os.path.dirname(__file__), "..", "fem")
sys.path.insert(0, os.path.abspath(FEM))

FS = 48000


def pincements(modes, n=4, duree=2.5, silence=0.3, bruit=1e-4, secteur=0.0, harmonique=0.0, graine=1):
    """n pincements d'une somme de sinusoïdes amorties (f, zeta, amplitude) ; option : un
    harmonique 2 du premier mode (rayonnement non linéaire) et un ronflement à 50 Hz."""
    rng = np.random.default_rng(graine)
    morceaux = []
    for k in range(n):
        t = np.arange(int(duree * FS)) / FS
        y = np.zeros_like(t)
        for f, z, a in modes:
            w = 2 * np.pi * f
            y += a * (0.7 + 0.3 * k / max(1, n - 1)) * np.exp(-z * w * t) * np.sin(w * math.sqrt(1 - z * z) * t + k)
        if harmonique:
            f1, z1, _ = modes[0]
            y += harmonique * np.exp(-2 * z1 * 2 * np.pi * f1 * t) * np.sin(2 * 2 * np.pi * f1 * t)
        morceaux.append(np.concatenate([np.zeros(int(silence * FS)), y]))
    x = np.concatenate(morceaux + [np.zeros(int(silence * FS))])
    x = x + bruit * rng.standard_normal(x.size)
    if secteur:
        x = x + secteur * np.sin(2 * np.pi * 50 * np.arange(x.size) / FS)
    return x


def test_esprit_exact_sans_bruit():
    n = np.arange(200)
    lam = np.array([0.99 * np.exp(0.3j), 0.95 * np.exp(-0.7j)])
    z = 1.0 * lam[0] ** n + 0.5 * lam[1] ** n
    l, a = pm.esprit(z, 2)
    o = np.argsort(np.angle(l))
    assert np.allclose(np.sort(np.angle(l)), np.sort(np.angle(lam)), atol=1e-9)
    assert np.allclose(np.abs(l[o]), np.abs(lam[np.argsort(np.angle(lam))]), atol=1e-9)
    assert sorted(np.abs(a)) == pytest.approx([0.5, 1.0], abs=1e-8)


def test_quatre_modes_harmonique_et_secteur():
    """Les modes de l'anche de matrix.txt (Elmer) : f à 1e-4 près, zeta à 3 % ; l'harmonique 2
    du mode 1 est reconnu comme tel ; le 50 Hz (qui ne décroît pas) n'est pas un mode."""
    vrais = [(67.54, 2e-3, 1.0), (842.3, 4e-3, 0.3), (1676.5, 6e-3, 0.1), (2699.4, 5e-3, 0.08)]
    x = pincements(vrais, harmonique=0.05, secteur=3e-4)
    r = pm.analyser(x, FS, f_max=4000)
    assert r.n_pincements == 4
    modes = r.vrais_modes()
    assert len(modes) == 4
    for (f, z, _), m in zip(vrais, modes):
        assert m.f_hz == pytest.approx(f, rel=1e-4)
        assert m.zeta == pytest.approx(z, rel=0.03)
        assert m.n_pincements == 4
    harm = [m for m in r.modes if m.nature.startswith("harmonique")]
    assert len(harm) == 1 and harm[0].f_hz == pytest.approx(2 * 67.54, rel=1e-4)
    assert "2.0 fois plus vite" in harm[0].nature
    assert all(abs(m.f_hz - 50) > 1 for m in r.modes)


def test_resonateur_de_chambre_tres_amorti():
    """Anche sur sa chambre : le résonateur d'air (Q = 20) s'éteint en 30 ms, il est vu quand même."""
    vrais = [(67.49, 2.2e-3, 1.0), (845.0, 4e-3, 0.3), (1140.5, 0.025, 0.4)]
    r = pm.analyser(pincements(vrais, n=5, bruit=3e-4, graine=2), FS, f_max=3000)
    modes = r.vrais_modes()
    assert len(modes) == 3
    assert modes[2].f_hz == pytest.approx(1140.5, rel=1e-3)
    assert modes[2].zeta == pytest.approx(0.025, rel=0.05)
    assert modes[0].zeta == pytest.approx(2.2e-3, rel=0.03)


def test_fichier_wav_16_bits(tmp_path):
    x = pincements([(440.0, 3e-3, 0.5), (2750.0, 5e-3, 0.2)], n=3, duree=1.5)
    ch = tmp_path / "pince.wav"
    with wave.open(str(ch), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(FS)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
    r = pm.analyser_fichier(str(ch), f_max=4000)
    assert [round(m.f_hz) for m in r.vrais_modes()] == [440, 2750]
    assert r.vrais_modes()[0].zeta == pytest.approx(3e-3, rel=0.05)
    pm.ecrire_csv(r, str(tmp_path / "modes.csv"))
    assert (tmp_path / "modes.csv").read_text(encoding="utf-8").startswith("fichier;f_hz")


# --- La comparaison au modèle ------------------------------------------------------------------
def test_racines_languette_chambre():
    cp = pytest.importorskip("comparer_pince")
    m, k, g = 2.72e-4, 49.0, 4.9e-5
    f0 = math.sqrt(k / m) / (2 * math.pi)
    # sans couplage : la languette et le résonateur, chacun chez soi
    fl, fr = cp.racines_languette_chambre(m, k, 0.0, 27.0, 155.0, 1140.0)
    assert fl == pytest.approx(f0, rel=1e-12) and fr == pytest.approx(1140.0, rel=1e-12)
    # avec couplage, sous f_H : l'air ajoute de la masse, la languette descend ; le résonateur monte
    fl, fr = cp.racines_languette_chambre(m, k, g, 27.0, 155.0, 1140.0)
    assert fl < f0 and fr > 1140.0
    # petit couplage : masse ajoutée g^2 (L_f + L_t) au premier ordre
    att = f0 / math.sqrt(1 + g * g * (27.0 + 155.0) / m)
    assert fl == pytest.approx(att, rel=1e-5)


def test_recalage_kappa_trou_et_pertes():
    cp = pytest.importorskip("comparer_pince")
    mode1 = dict(m_eff_kg=4.9e-5, k_eff_N_m=374.0, gamma_m2=3.3e-5)
    res = dict(f_H=1450.0, L_t=150.0, L_f=25.0, S_trou=200e-6, l_eff=0.025)
    # un décalage « mesuré » fabriqué avec kappa^2 = 0,5 est retrouvé
    p_half = cp.prediction_chambre(mode1, res, kappa=math.sqrt(0.5))
    assert cp.recaler_kappa(mode1, res, p_half["decalage_cents"]) == pytest.approx(0.5, rel=0.01)
    # un résonateur mesuré 5 % plus bas : le trou est plus long, d'environ (1/0,95)^2
    f_res = cp.prediction_chambre(mode1, res)["f_resonateur"] * 0.95
    l_eff, Lt, C = cp.recaler_trou(mode1, res, f_res)
    assert Lt / res["L_t"] == pytest.approx(1 / 0.95 ** 2, rel=0.01)
    # R-L-C série : la résistance redonne l'amortissement
    R = cp.resistance_pertes(0.03, Lt, C)
    assert R / 2 * math.sqrt(C / Lt) == pytest.approx(0.03, rel=1e-12)


def _anche_grave():
    pytest.importorskip("yaml")
    from banc_recherche.banque_anches import charger_yaml
    return next(a for a in charger_yaml(os.path.join(FEM, "anche", "anches_r12.yaml")) if a.id == "R12-grave")


def _resultat(freqs, zeta=3e-3):
    r = pm.ResultatModes(fichier="synthese", n_pincements=3)
    r.modes = [pm.ModeMesure(f, 0.0, zeta, 0.0, 1 / (2 * zeta), zeta * 2 * math.pi * f, -10.0, 3) for f in freqs]
    return r


def test_comparer_seule_juge_la_forme():
    """Toutes les fréquences x 1,02 : seule l'échelle bouge (épaisseur ou E), les rapports
    restent ; le mode 2 seul déplacé de 10 % : c'est la forme qui est fausse."""
    cp = pytest.importorskip("comparer_pince")
    anche = _anche_grave()
    modele, _ = cp.modes_modele(anche)
    flex = [m for m in modele if m["type"] == "flexion"][:3]
    fm = [m["f_elmer"] or m["f_eb"] for m in flex]
    lignes, paires, _ = cp.comparer_seule(anche, _resultat([1.02 * f for f in fm]))
    assert 1 in paires
    v = [l["verdict"] for l in lignes if l["grandeur"].startswith("mode 2")][0]
    assert "la forme est juste" in v
    lignes, _, _ = cp.comparer_seule(anche, _resultat([fm[0], 1.10 * fm[1], fm[2]]))
    v = [l["verdict"] for l in lignes if l["grandeur"].startswith("mode 2")][0]
    assert "FORME est en cause" in v


def test_comparer_chambre_recale_kappa():
    cp = pytest.importorskip("comparer_pince")
    anche = _anche_grave()
    res = cp.reseau_chambre(anche.id)
    _, mode1 = cp.modes_modele(anche)
    if res is None or mode1 is None:
        pytest.skip("pas de calcul Elmer versé pour R12-grave")
    p = cp.prediction_chambre(mode1, res, kappa=math.sqrt(0.6))
    f_seule = p["f_seule"]
    mes = _resultat([p["f_chambre"], 845.0, p["f_resonateur"]])
    mes.modes[2].zeta = 0.03
    lignes = cp.comparer_chambre(anche, mes, f1_seule=f_seule, mode1=mode1)
    assert "kappa^2 = 0.60" in lignes[0]["verdict"]
    assert "trou l_eff" in lignes[1]["verdict"]


# --- La soufflerie -----------------------------------------------------------------------------
def _ecrire_wav(ch, x):
    with wave.open(str(ch), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(FS)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def test_feuille_de_soufflerie(tmp_path):
    sf = pytest.importorskip("souffle")
    # un son de jeu dont l'harmonique 2 est PLUS fort que le fondamental (anche grave)
    t = np.arange(int(2.0 * FS)) / FS
    f_jeu = 66.2
    x = 0.1 * np.sin(2 * np.pi * f_jeu * t) + 0.3 * np.sin(2 * np.pi * 2 * f_jeu * t + 1) \
        + 0.1 * np.sin(2 * np.pi * 3 * f_jeu * t)
    _ecrire_wav(tmp_path / "jeu.wav", x)
    feuille = tmp_path / "feuille.csv"
    feuille.write_text(
        "type;cycle;sens;p_lue_Pa;sonne;fichier;t0_s;t1_s;remarque\n"
        "zero;;;101 310;;;;;avant ; 19 degrés\n"
        "palier;1;monte;101 320;non;;;;\n"
        "palier;1;monte;101 326;non;;;;\n"
        "palier;1;monte;101 332;oui;;;;\n"
        "palier;1;descend;101 326;oui;;;;\n"
        "palier;1;descend;101 320;non;;;;\n"
        "palier;2;monte;101 326;non;;;;\n"
        "palier;2;monte;101 332;oui;;;;\n"
        "palier;2;descend;101 320;oui;;;;\n"
        "palier;2;descend;101 314;non;;;;\n"
        "jeu;1;;101 332;oui;jeu.wav;0,2;1,8;1,2 fois le seuil\n"
        "zero;;;101 312;;;;;après\n", encoding="utf-8")
    r = sf.analyser(str(feuille))
    assert r["zero_Pa"] == pytest.approx(101311.0)
    assert [c["p_on"] for c in r["cycles"]] == pytest.approx([18.0, 18.0])
    assert [c["p_off"] for c in r["cycles"]] == pytest.approx([12.0, 6.0])
    assert r["cycles"][0]["u_on"] == pytest.approx(3.0)
    assert r["rapport_on_off"] == pytest.approx(18.0 / 9.0)
    assert r["jeux"][0]["f_jeu_Hz"] == pytest.approx(f_jeu, abs=1e-3)
    d = sf.pour_recalage(str(feuille))
    assert d["p_on_Pa"] == pytest.approx(18.0) and d["f_jeu_Hz"] == pytest.approx(f_jeu, abs=1e-3)


def test_reed_model_un_amortissement_par_mode():
    """Les zeta mesurés au son pincé (un par mode) passent au modèle RK4, en liste comme en
    tableau ; avant, « 2 * [z1, z2] » répétait la liste et le constructeur échouait."""
    from banc_recherche.reed_model import ReedModel
    a = ReedModel(zeta=[2e-3, 4e-3])
    b = ReedModel(zeta=np.array([2e-3, 4e-3]))
    assert np.allclose(a.C, b.C)
    # chaque mode propre est amorti de son zeta : Phi^T C Phi = diag(2 zeta w)
    w2, Phi = a._eig_generalise()
    d = Phi.T @ a.C @ Phi
    assert np.allclose(np.diag(d), 2 * np.array([2e-3, 4e-3]) * np.sqrt(w2), rtol=1e-8)
    assert np.allclose(ReedModel(zeta=0.01).C, ReedModel(zeta=[0.01, 0.01]).C)

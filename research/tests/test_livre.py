"""Le livre promet qu'on peut refaire les calculs. On vérifie qu'il dit vrai.

Un chapitre qui cite une fonction qui n'existe plus est un chapitre qui ment,
et celui-ci s'intitule *la nature ne ment pas*. Ces tests exécutent exactement
l'API citée dans `docs/livre/`, pour qu'un renommage casse le test avant de
casser la promesse.
"""
import pathlib
import re

import numpy as np
import pytest

from banc_recherche import bifurcation, seuil

LIVRE = pathlib.Path(__file__).resolve().parents[1] / "docs" / "livre"


def _rampes(p_demarre=2.0, p_eteint=1.6, n=400):
    """Montée puis descente, avec une hystérésis fabriquée exprès.

    L'amplitude suit `A = √(p − p_c)` au-dessus du seuil : c'est la forme de
    Stuart-Landau que le chapitre 2 annonce, et qui doit donc se retrouver.
    """
    p_up = np.linspace(0.0, 3.0, n)
    p_dn = p_up[::-1]
    return (p_up, np.sqrt(np.clip(p_up - p_demarre, 0.0, None)),
            p_dn, np.sqrt(np.clip(p_dn - p_eteint, 0.0, None)))


def test_l_extrait_du_chapitre_2_tourne_vraiment():
    """Les deux appels imprimés dans « Le mesurer soi-même, avec presque rien »."""
    p_up, a_up, p_dn, a_dn = _rampes()

    s = seuil.detect(np.r_[p_up, p_dn], np.r_[a_up, a_dn], amp_thresh=0.05)
    assert s.p_on == pytest.approx(2.0, abs=0.05)
    assert s.p_off == pytest.approx(1.6, abs=0.05)
    assert s.hysteresis == pytest.approx(s.p_on - s.p_off, abs=1e-9)

    d = bifurcation.diagram(p_up, a_up, p_dn, a_dn, amp_thresh=0.05)
    assert d.kind in ('supercritique', 'souscritique')
    assert d.hopf.threshold == pytest.approx(2.0, abs=0.05)
    assert d.hopf.r2 > 0.99


def test_une_hysteresis_franche_se_lit_souscritique():
    """« p_on > p_off » : la dette que la Partie I laisse à la Partie II."""
    p_up, a_up, p_dn, a_dn = _rampes(2.0, 1.6)
    d = bifurcation.diagram(p_up, a_up, p_dn, a_dn, amp_thresh=0.05)
    assert d.mu_on > d.mu_off
    assert d.kind == 'souscritique'


def test_la_racine_carree_de_stuart_landau_est_bien_celle_qu_on_annonce():
    """`A² ∝ (μ − μc)` : la pente de l'ajustement, pas seulement son r²."""
    p_up, a_up, _, _ = _rampes(2.0)
    fit = bifurcation.hopf_amplitude_fit(p_up, a_up)
    assert fit.slope == pytest.approx(1.0, rel=0.05)   # A² = 1·(μ − 2)
    assert fit.threshold == pytest.approx(2.0, abs=0.05)


# -----------------------------------------------------------------------------
# Le contrat d'écriture, celui de CLAUDE.md : les encarts sont à Ewen.
# -----------------------------------------------------------------------------

def test_les_encarts_ton_experience_restent_vides():
    """⟢ est une invitation, pas un texte à écrire à sa place.

    Un encart rempli par le programme serait une biographie inventée. Le test
    vérifie qu'aucun ⟢ n'est suivi d'un récit : une consigne, une question,
    jamais un souvenir.
    """
    fichiers = sorted(LIVRE.glob("*.md"))
    assert fichiers, "aucun chapitre rédigé : le test n'a rien à garder"
    for f in fichiers:
        texte = f.read_text(encoding='utf-8')
        encarts = re.findall(r"⟢(.+?)(?:\n\n|\n---)", texte, flags=re.S)
        assert encarts, f"{f.name} : pas d'encart ⟢"
        for e in encarts:
            # une invitation tient en quelques lignes et ne raconte rien
            assert len(e.split()) < 60, f"{f.name} : encart trop long, on a écrit à sa place"
            assert " j'ai " not in e.lower() and " je " not in e.lower(), \
                f"{f.name} : un encart parle à la première personne"


def test_chaque_partie_porte_les_trois_fils():
    """Dehors, dedans, vivant — tressés, pas empilés.

    Le test parcourt toutes les parties rédigées, pas seulement la première :
    une partie qui oublierait sa « Résonance intérieure » ne serait plus le
    livre qu'on a annoncé, elle serait un cours.
    """
    parties = sorted(p for p in LIVRE.glob("*.md")
                     if not p.name.startswith("00_"))
    assert parties, "aucune partie rédigée"
    for p in parties:
        # le texte est rendu à la ligne : on compare sur une version dont les
        # blancs sont normalisés, sinon une phrase coupée échappe au test.
        ch = " ".join(p.read_text(encoding='utf-8').split())
        assert "Résonance intérieure" in ch, f"{p.name} : le dedans manque"
        assert "⟢" in ch, f"{p.name} : le vivant manque"
        # la contrainte matérielle qui ne doit jamais sauter : tout doit
        # rester faisable avec une carte son et un micro.
        assert "presque rien" in ch or "Un micro suffit" in ch, \
            f"{p.name} : plus de protocole accessible"


def test_le_prelude_annonce_les_trois_fils_et_la_precaution():
    """Le prélude doit poser la retenue : aucune équivalence n'est prétendue."""
    pr = " ".join((LIVRE / "00_prelude.md").read_text(encoding='utf-8').split())
    assert "vibromètre laser" in pr          # la contrainte matérielle, dite
    assert "ne prétends nulle part" in pr    # la précaution épistémique


# -----------------------------------------------------------------------------
# Partie III : Tresp ≈ 2,2·τ, la traduction qui relie la mesure à la théorie
# -----------------------------------------------------------------------------

def test_tresp_vaut_bien_deux_fois_la_constante_de_temps():
    """Le chapitre 5 annonce `T(10→90) = τ·(ln10 − ln(10/9)) ≈ 2,20·τ`.

    C'est ce qui permet de traduire une attaque mesurée au micro en un
    `σ = 1/τ`, donc en une distance au seuil. Si le rapport n'y est pas, le
    chapitre raconte une histoire.
    """
    from banc_recherche import analysis

    sr = 48000
    t = np.arange(0.0, 0.5, 1.0 / sr)
    for tau in (0.010, 0.030, 0.060):
        sig = (1.0 - np.exp(-t / tau)) * np.sin(2 * np.pi * 440.0 * t)
        tresp = analysis.attack(sig, sr).tresp_ms / 1000.0
        assert tresp / tau == pytest.approx(2.2, rel=0.25)


def test_une_attaque_plus_lente_donne_un_tresp_plus_long():
    """La monotonie, qui est ce sur quoi le chapitre s'appuie vraiment."""
    from banc_recherche import analysis

    sr = 48000
    t = np.arange(0.0, 0.6, 1.0 / sr)
    mesures = []
    for tau in (0.005, 0.020, 0.050, 0.100):
        sig = (1.0 - np.exp(-t / tau)) * np.sin(2 * np.pi * 440.0 * t)
        mesures.append(analysis.attack(sig, sr).tresp_ms)
    assert mesures == sorted(mesures)

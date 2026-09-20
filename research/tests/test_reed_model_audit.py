"""Garde-fous issus de l'audit du modèle d'anche.

Ces tests figent des propriétés **physiques** (pas seulement numériques) :
une matrice d'amortissement doit être symétrique, une base modale doit
retrouver la solution analytique. Ils ont attrapé un amortissement non
symétrique — voir `docs/audit_modele_anche.md`.
"""
import numpy as np

from banc_recherche import modal
from banc_recherche.reed_model import ReedModel, SECTIONS_DEFAULT


def test_base_modale_retrouve_le_cantilever_analytique():
    """Poutre uniforme : l'assemblage doit redonner la formule encastré-libre."""
    L, b, h, E, rho = 50e-3, 4.8e-3, 0.4e-3, 2.1e11, 7800.0
    EI = E * b * h ** 3 / 12.0
    rhoA = rho * b * h
    attendu = [(modal.bl_sigma(n)[0] ** 2) / (2 * np.pi * L ** 2) * np.sqrt(EI / rhoA)
               for n in (1, 2, 3)]
    obtenu = np.sort(modal.natural_frequencies_np([[L, rho, b, h, E]], n_modes=3))
    for a, o in zip(attendu, obtenu):
        assert abs(o - a) / a < 1e-3


def test_amortissement_symetrique():
    """C doit être symétrique : sinon elle injecte de l'énergie selon la
    direction du mouvement, ce qui n'est pas un amortissement."""
    rm = ReedModel(n_modes=2, zeta=0.01)
    assert np.allclose(rm.C, rm.C.T, atol=1e-12)


def test_amortissement_semi_defini_positif():
    """C ne doit jamais pouvoir fournir d'énergie (valeurs propres >= 0)."""
    rm = ReedModel(n_modes=3, zeta=0.02)
    assert np.min(np.linalg.eigvalsh(rm.C)) > -1e-12


def test_amortissement_proportionnel_a_zeta():
    """Doubler ζ doit doubler C — sinon l'amortissement n'est pas modal."""
    c1 = ReedModel(n_modes=2, zeta=0.01).C
    c2 = ReedModel(n_modes=2, zeta=0.02).C
    assert np.allclose(c2, 2 * c1, rtol=1e-9)


def test_frequences_propres_triees_et_coherentes():
    """Les ω du modèle doivent coïncider avec `modal` et être triées."""
    rm = ReedModel(n_modes=3, zeta=0.01)
    f_modele = rm.omega / (2 * np.pi)
    f_modal = np.sort(modal.natural_frequencies_np(SECTIONS_DEFAULT, n_modes=3))
    assert np.all(np.diff(f_modele) > 0)
    assert np.allclose(f_modele, f_modal, rtol=1e-6)


def test_matrice_de_masse_non_diagonale():
    """Constat d'audit : la base cantilever uniforme n'est PAS la base propre
    de l'anche multi-tronçon. C'est justement ce qui rendait `M @ diag(2ζω)`
    invalide — si ce test devient faux, la correction n'est plus nécessaire."""
    M, _ = modal.assemble(SECTIONS_DEFAULT, 2)
    couplage = abs(M[0, 1]) / np.sqrt(abs(M[0, 0] * M[1, 1]))
    assert couplage > 0.1

import numpy as np

from banc_recherche.doe_analysis import taguchi


def test_sn_smaller_better():
    # y constant a → S/N = −20 log10(a)
    assert abs(taguchi.sn_smaller([2.0, 2.0, 2.0]) - (-20 * np.log10(2.0))) < 1e-9


def test_sn_larger_better():
    assert abs(taguchi.sn_larger([2.0, 2.0, 2.0]) - (-10 * np.log10(0.25))) < 1e-9


def test_sn_nominal_higher_when_less_variance():
    tight = taguchi.sn_nominal([10.0, 10.1, 9.9, 10.0])
    loose = taguchi.sn_nominal([10.0, 12.0, 8.0, 10.0])
    assert tight > loose         # moins de variance = meilleur S/N

import numpy as np

from banc_recherche.batch import RESULT_COLUMNS, _mean_after


def test_result_columns_match_legacy():
    # Colonnes du plan_exp.csv d'origine (Data_analysis.py).
    assert RESULT_COLUMNS == [
        "P_pos", "S_plus", "P_plus", "i_Clap", "Calculs_Surf", "Press_In_Mean",
        "Debit_In_Mean", "Impedence", "PuiHydro", "Tresp", "Intensity", "Freq0",
        "Form1", "Form2", "Form3", "Form4",
    ]
    assert len(RESULT_COLUMNS) == 16


def test_mean_after_ignores_zeros():
    v = np.array([0.0, 0.0, 900.0, 902.0, 898.0])
    assert abs(_mean_after(None, v, 0.0) - 900.0) < 1e-9


def test_mean_after_all_zero_is_nan():
    v = np.zeros(5)
    assert np.isnan(_mean_after(None, v, 0.0))

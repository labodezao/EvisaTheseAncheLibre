"""Analyse par lot d'une campagne HDF5 → `plan_exp.csv`.

Port fidèle de la **boucle principale** de `Data_analysis.py` (celle qui suit la
fonction `PraatCalcs`, restée sur le Drive). Rejoue, hors banc, l'analyse de
toute une grille déjà mesurée :

  pour chaque point (Ppos, Section, Pression, Clapet) du HDF5 écrit par
  `Mesures.py` :
    - reconstruit le son (canal micro) → `analysis.praat_calcs`
      (Tresp, formants F1–F4, pitch, intensité) ;
    - moyenne pression `P` et débit `Q` après `Tresp` → impédance `P/Q`
      et puissance hydraulique `P·Q` ;
    - empile une ligne de résultats.
  → DataFrame 16 colonnes exporté en `plan_exp.csv` (mêmes colonnes qu'avant).

Ce module ne dépend pas du banc : il travaille sur les fichiers de campagne.
"""
from __future__ import annotations

from typing import Callable

import numpy as np

from . import analysis, impedance, campaigns

RESULT_COLUMNS = [
    "P_pos", "S_plus", "P_plus", "i_Clap", "Calculs_Surf", "Press_In_Mean",
    "Debit_In_Mean", "Impedence", "PuiHydro", "Tresp", "Intensity", "Freq0",
    "Form1", "Form2", "Form3", "Form4",
]


def _mean_after(series_t, series_v, t_zero):
    """Moyenne d'une série (temps, valeur) après l'instant `t_zero` (NaN-safe)."""
    v = np.asarray(series_v, dtype="float64")
    v = v[np.asarray(series_t) > t_zero] if series_t is not None else v
    v = v[v != 0]
    return float(np.nanmean(v)) if v.size else float("nan")


def analyse_campaign(h5_path: str, samplerate: int = 48000,
                     csv_path: str = "plan_exp.csv",
                     progress: Callable[[int, int, str], None] | None = None):
    """Analyse toute la grille d'un HDF5 de campagne et écrit `plan_exp.csv`.

    Renvoie le `pandas.DataFrame` des résultats.
    """
    import pandas as pd

    f, present = campaigns.open_campaign(h5_path)
    try:
        params = np.asarray(present["Measure_params"])
        n_sec, n_pres, n_clap = int(params[0]), int(params[1]), int(params[2])
        surf = present.get("Calculs_Surf")
        acou = present["Mesures_Press_Acoustique"]
        press = present.get("Mesures_Press")
        debit = present.get("Mesures_Debit")

        total = 2 * n_sec * n_pres * n_clap
        rows = []
        k = 0
        for p_pos in range(2):
            for s in range(n_sec):
                for p in range(n_pres):
                    for c in range(n_clap):
                        k += 1
                        if progress:
                            progress(k, total, f"Ppos{p_pos} Sec{s} Pres{p} Clap{c}")
                        sig = np.asarray(acou[p_pos, s, p, c, 1], dtype="float64")
                        if not np.any(sig):
                            continue
                        try:
                            r = analysis.praat_calcs(sig / 2 ** 31, samplerate)
                        except Exception:
                            continue
                        t0 = r.t_zero_s
                        # Pression / débit après Tresp (canaux [.., 1, :] du HDF5).
                        p_in = q_in = float("nan")
                        if press is not None:
                            p_ser = np.asarray(press[p_pos, s, p, c, 1])
                            p_in = _mean_after(None, p_ser, t0)
                        if debit is not None:
                            q_ser = np.asarray(debit[p_pos, s, p, c, 1])
                            q_in = _mean_after(None, q_ser, t0)
                        z = p_in / q_in if q_in not in (0.0,) and not np.isnan(q_in) else float("nan")
                        pui = p_in * q_in
                        surf_v = float(surf[p_pos, s, p, c]) if surf is not None else float("nan")
                        intensity = float(np.nanmean(r.intensity_db)) if r.intensity_db.size else float("nan")
                        rows.append([
                            p_pos, s, p, c, surf_v, p_in, q_in, z, pui,
                            r.tresp_s, intensity, r.mean_fund_hz,
                            r.f1, r.f2, r.f3, r.f4,
                        ])
        df = pd.DataFrame(rows, columns=RESULT_COLUMNS)
        df.to_csv(csv_path, index=False)
        return df
    finally:
        f.close()

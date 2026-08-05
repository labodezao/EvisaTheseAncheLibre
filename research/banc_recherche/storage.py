"""Stockage HDF5 + export CSV (schéma `plan_exp`).

Reprend le rôle du HDF5 de `Mesures.py` : chaque point de mesure conserve les
signaux bruts (audio, pression, débit) et les scalaires dérivés (Tresp,
formants, impédance…). L'export CSV reproduit `plan_exp.csv`.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

import numpy as np

try:
    import h5py
except Exception:
    h5py = None


@dataclass
class Point:
    idx: int
    section_mm: float
    pressure_pa: float
    clapet_deg: float
    position: int
    # scalaires dérivés
    f0_hz: float = float("nan")
    tresp_ms: float = float("nan")
    impedance: float = float("nan")
    pui_hydro: float = float("nan")
    formants: tuple = ()
    # signaux bruts (facultatif ; lourds → HDF5)
    audio: np.ndarray | None = field(default=None, repr=False)
    pressure: np.ndarray | None = field(default=None, repr=False)
    flow: np.ndarray | None = field(default=None, repr=False)
    accel: np.ndarray | None = field(default=None, repr=False)   # voie accéléromètre


class Store:
    """Ouvre un fichier HDF5 et y écrit les points (groupe par point)."""

    def __init__(self, path: str):
        if h5py is None:
            raise RuntimeError("h5py indisponible")
        self.path = path
        self._f = h5py.File(path, "a")

    def write(self, pt: Point):
        g = self._f.require_group(f"point_{pt.idx:04d}")
        for k, v in asdict(pt).items():
            if isinstance(v, np.ndarray):
                if v is not None:
                    if k in g:
                        del g[k]
                    g.create_dataset(k, data=v, compression="gzip")
            elif isinstance(v, (int, float, str, tuple)):
                g.attrs[k] = np.array(v) if isinstance(v, tuple) else v
        self._f.flush()

    def close(self):
        self._f.close()


def export_csv(points: list[Point], path: str):
    """Table scalaire des points (sans signaux) → plan_exp.csv."""
    import pandas as pd
    rows = []
    for p in points:
        rows.append({
            "point": p.idx, "section_mm": p.section_mm, "pressure_pa": p.pressure_pa,
            "clapet_deg": p.clapet_deg, "position": p.position, "f0_hz": p.f0_hz,
            "tresp_ms": p.tresp_ms, "impedance": p.impedance, "pui_hydro": p.pui_hydro,
            **{f"F{i+1}": (p.formants[i] if i < len(p.formants) else float("nan"))
               for i in range(4)},
        })
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    return df

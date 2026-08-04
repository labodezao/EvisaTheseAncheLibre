"""Relecture des campagnes de mesures existantes (HDF5 `Mesures.py` + `.npy`).

Permet à la nouvelle GUI de rouvrir les données de thèse déjà acquises
(`Measure_dataset_nSec…nPres…nClap….hdf5`, `d_Mesures_*.npy`) pour rejouer
l'analyse (`analysis.praat_calcs`, `impedance.compute`) sans le banc.
"""
from __future__ import annotations

import glob
import os

import numpy as np

try:
    import h5py
except Exception:
    h5py = None


# Datasets écrits par l'ancien Mesures.py (dimensions : Ppos, Section, Pression,
# Clapet, 2[data/temps], échantillons).
HDF5_DATASETS = (
    "Mesures_Press", "MesuresTemperature", "Mesures_Debit",
    "Mesures_Press_Acoustique", "Mesures_Press_Pos", "Calculs_Surf",
    "Measure_params",
)


def find_hdf5(path: str = "data/"):
    return sorted(glob.glob(os.path.join(path, "*.hdf5")) + glob.glob(os.path.join(path, "*.h5")))


def open_campaign(h5_path: str):
    """Ouvre un HDF5 de campagne, renvoie (handle, dict des datasets présents)."""
    if h5py is None:
        raise RuntimeError("h5py indisponible")
    f = h5py.File(h5_path, "r")
    present = {k: f[k] for k in f.keys()}
    return f, present


def acoustic_slice(f, p_pos: int, section: int, pressure: int, clapet: int) -> np.ndarray:
    """Extrait le signal acoustique d'un point de la grille (canal micro)."""
    ds = f["Mesures_Press_Acoustique"]
    return np.asarray(ds[p_pos, section, pressure, clapet, 1])


def load_npy(path: str) -> np.ndarray:
    """Charge un `.npy` de campagne (mmap pour les gros fichiers, ex. 2 Go)."""
    return np.load(path, mmap_mode="r")

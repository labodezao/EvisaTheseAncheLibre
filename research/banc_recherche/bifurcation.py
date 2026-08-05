"""Diagrammes et analyse de **bifurcation** de l'anche vue comme oscillateur
auto-entretenu non linéaire.

Le déclenchement de l'oscillation quand la pression (ou la vitesse de soufflet)
croît est une **bifurcation de Hopf** :

- **super-critique** : l'amplitude du cycle limite croît continûment,
  `A² ∝ (μ − μc)` près du seuil (forme normale de Stuart-Landau) ;
- **sous-critique** : saut d'amplitude + **hystérésis** (`μ_on > μ_off`), typique
  des anches — bistabilité entre l'anche muette et l'anche qui sonne.

On construit le diagramme amplitude(paramètre), on ajuste la branche de Hopf, on
classe la bifurcation et on mesure l'hystérésis (relié à `seuil.detect`).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class HopfFit:
    threshold: float     # μc : paramètre au seuil (A² → 0)
    slope: float         # pente de A² vs μ (∝ 1/coefficient de Landau)
    r2: float            # qualité de l'ajustement linéaire A² = slope·(μ − μc)


@dataclass
class BifurcationDiagram:
    param_up: np.ndarray
    amp_up: np.ndarray
    param_down: np.ndarray
    amp_down: np.ndarray
    mu_on: float                 # seuil en montée (apparition)
    mu_off: float                # seuil en descente (extinction)
    hysteresis: float            # μ_on − μ_off (> 0 ⇒ sous-critique)
    kind: str                    # 'supercritique' | 'souscritique' | 'indéterminé'
    hopf: HopfFit | None = field(default=None)


def hopf_amplitude_fit(param, amplitude, amp_floor=0.0) -> HopfFit:
    """Ajuste la branche super-critique : `A² = slope·(μ − μc)` sur les points où
    l'anche oscille (amplitude > `amp_floor`). Régression de A² sur μ ;
    `μc` = intersection avec A² = 0."""
    param = np.asarray(param, dtype="float64")
    amplitude = np.asarray(amplitude, dtype="float64")
    on = amplitude > amp_floor
    if on.sum() < 2:
        return HopfFit(float("nan"), float("nan"), float("nan"))
    x = param[on]
    y = amplitude[on] ** 2
    A = np.vstack([x, np.ones_like(x)]).T
    (slope, intercept), *_ = np.linalg.lstsq(A, y, rcond=None)
    yhat = A @ np.array([slope, intercept])
    ss_res = float(((y - yhat) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum()) or 1.0
    mu_c = -intercept / slope if slope != 0 else float("nan")
    return HopfFit(mu_c, float(slope), 1.0 - ss_res / ss_tot)


def _first_crossing(param, amplitude, thresh, rising):
    """Premier paramètre où l'amplitude franchit `thresh` (montée ou descente)."""
    param = np.asarray(param); amplitude = np.asarray(amplitude)
    above = amplitude > thresh
    idx = np.where(above)[0] if rising else np.where(~above)[0]
    return float(param[idx[0]]) if len(idx) else float("nan")


def diagram(param_up, amp_up, param_down=None, amp_down=None,
            amp_thresh=None) -> BifurcationDiagram:
    """Construit le diagramme de bifurcation depuis une rampe montante (et,
    facultativement, descendante) du paramètre de contrôle.

    `amp_thresh` : seuil d'amplitude marquant l'oscillation (défaut : 10 % du max).
    """
    param_up = np.asarray(param_up, dtype="float64")
    amp_up = np.asarray(amp_up, dtype="float64")
    amax = np.nanmax(amp_up) if amp_up.size else 1.0
    thr = amp_thresh if amp_thresh is not None else 0.1 * amax
    mu_on = _first_crossing(param_up, amp_up, thr, rising=True)

    if param_down is not None:
        param_down = np.asarray(param_down, dtype="float64")
        amp_down = np.asarray(amp_down, dtype="float64")
        mu_off = _first_crossing(param_down, amp_down, thr, rising=False)
    else:
        param_down = np.array([]); amp_down = np.array([]); mu_off = mu_on

    hyst = mu_on - mu_off if np.isfinite(mu_on) and np.isfinite(mu_off) else float("nan")
    if not np.isfinite(hyst):
        kind = "indéterminé"
    elif hyst > 0.02 * abs(mu_on if mu_on else 1.0):
        kind = "souscritique"        # hystérésis franche
    else:
        kind = "supercritique"
    hopf = hopf_amplitude_fit(param_up, amp_up, amp_floor=thr)
    return BifurcationDiagram(param_up, amp_up, param_down, amp_down,
                              mu_on, mu_off, hyst, kind, hopf)


def order_parameter(signal, fs, win_s=0.05):
    """Paramètre d'ordre = amplitude RMS glissante du signal (proxy du cycle
    limite). Utile pour tracer amplitude vs paramètre le long d'une rampe."""
    signal = np.asarray(signal, dtype="float64")
    w = max(1, int(win_s * fs))
    sq = np.convolve(signal ** 2, np.ones(w) / w, mode="same")
    return np.sqrt(sq)

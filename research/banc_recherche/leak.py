"""Détection de fuites d'air.

1. **Décroissance de pression** (`fit_decay`) : mesure globale d'étanchéité
   (τ, conductance) — commande firmware `LEAKTEST`.
2. **Localisation par détection synchrone / lock-in** (`acoustic_leak_strength`,
   `lockin`) : on module la pression du soufflet à `f_mod` ; chaque fuite
   rayonne un sifflement dont l'intensité clignote à `f_mod`. Le lock-in de
   l'enveloppe du sifflement à `f_mod` extrait la fuite du bruit ambiant (gain
   de S/N énorme) → carte de fuite en promenant un micro. C'est le principe de
   l'amplificateur à détection synchrone appliqué à l'acoustique de fuite, avec
   le **soufflet comme modulateur** — cheap et propre à ce banc.

Couvre l'annexe « Leaks detection » et « Sealing material influence ».
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class LeakResult:
    p0: float            # pression initiale (Pa)
    tau: float           # temps caractéristique (s)
    half_life: float     # demi-vie (s)
    conductance: float   # V/τ si volume fourni, sinon NaN


def fit_decay(t: np.ndarray, p: np.ndarray, volume_m3: float | None = None) -> LeakResult:
    """Ajuste `p(t) = p₀·e^{−t/τ}` par régression linéaire sur `ln(p)`.

    `t` en s, `p` en Pa (relatifs, > 0). Ignore les points ≤ 0.
    """
    t = np.asarray(t, dtype="float64")
    p = np.asarray(p, dtype="float64")
    mask = p > 0
    t, p = t[mask], p[mask]
    if t.size < 3:
        return LeakResult(float("nan"), float("nan"), float("nan"), float("nan"))
    A = np.vstack([t, np.ones_like(t)]).T
    slope, intercept = np.linalg.lstsq(A, np.log(p), rcond=None)[0]
    # Pente non significativement négative (bruit numérique) = aucune fuite.
    tau = float(-1.0 / slope) if slope < -1e-9 else float("inf")
    p0 = float(np.exp(intercept))
    half = tau * np.log(2.0) if np.isfinite(tau) else float("inf")
    cond = (volume_m3 / tau) if (volume_m3 and np.isfinite(tau) and tau > 0) else float("nan")
    return LeakResult(p0, tau, half, cond)


# ---- Localisation par détection synchrone (lock-in) ------------------------
def _bandpass(sig, fs, lo, hi):
    """Passe-bande par masque FFT (numpy seul)."""
    x = np.asarray(sig, dtype="float64")
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(x.size, 1.0 / fs)
    X[(f < lo) | (f > hi)] = 0.0
    return np.fft.irfft(X, x.size)


def _envelope(sig):
    """Enveloppe d'amplitude (|signal analytique|, Hilbert par FFT)."""
    x = np.asarray(sig, dtype="float64")
    n = x.size
    X = np.fft.fft(x)
    h = np.zeros(n)
    if n % 2 == 0:
        h[0] = h[n // 2] = 1
        h[1:n // 2] = 2
    else:
        h[0] = 1
        h[1:(n + 1) // 2] = 2
    return np.abs(np.fft.ifft(X * h))


def lockin(sig, fs, f_ref):
    """Détection synchrone : amplitude et phase de la composante de `sig` à
    `f_ref`. Renvoie (R, phase). Rejette tout ce qui ne bat pas à `f_ref`."""
    x = np.asarray(sig, dtype="float64")
    x = x - x.mean()
    t = np.arange(x.size) / fs
    i = np.mean(x * np.cos(2 * np.pi * f_ref * t))     # composante en phase
    q = np.mean(x * np.sin(2 * np.pi * f_ref * t))     # composante en quadrature
    return 2.0 * float(np.hypot(i, q)), float(np.arctan2(q, i))


def acoustic_leak_strength(mic, fs, f_mod, hiss_band=(4000.0, 20000.0)):
    """Force de fuite à la position du micro, par détection synchrone.

    La pression du soufflet est modulée à `f_mod` : on isole la bande de
    sifflement (`hiss_band`), on prend son enveloppe, et on fait le lock-in de
    cette enveloppe à `f_mod`. Grand = fuite proche. Robuste au bruit ambiant.
    """
    hi = min(hiss_band[1], fs / 2 * 0.98)
    band = _bandpass(mic, fs, hiss_band[0], hi)
    env = _envelope(band)
    r, _ = lockin(env, fs, f_mod)
    return r


def leak_map(recordings, fs, f_mod, hiss_band=(4000.0, 20000.0)):
    """Carte de fuite : force par position. `recordings` = liste de (label, mic).
    Renvoie [(label, force)] trié décroissant (la 1re = fuite la plus probable)."""
    out = [(lab, acoustic_leak_strength(m, fs, f_mod, hiss_band)) for lab, m in recordings]
    return sorted(out, key=lambda kv: kv[1], reverse=True)


def tdoa_delay(mic1, mic2, fs):
    """Décalage temporel (s) entre deux micros par corrélation croisée — pour
    trianguler une fuite (le signe indique de quel côté elle est)."""
    a = np.asarray(mic1, dtype="float64"); b = np.asarray(mic2, dtype="float64")
    n = min(a.size, b.size)
    a, b = a[:n] - a[:n].mean(), b[:n] - b[:n].mean()
    corr = np.correlate(a, b, mode="full")
    lag = int(np.argmax(corr)) - (n - 1)
    return lag / fs


# ---- Débit de fuite en L/min (protocole de fabrication, 03/10/2026) --------
# La chute de pression d'un volume fermé ne dit pas seulement « ça fuit » :
# avec le volume, elle donne le **débit de fuite** à chaque pression, et la
# forme de la loi débit-pression dit **quel genre** de fuite c'est.
#
#   Q = (V / p_atm) · |dp/dt|          (gaz parfait, transformation lente, isotherme)
#
# - trou franc, fente courte : Q ∝ p^0,5 (Bernoulli) ;
# - pores, bois de bout, peau, collage poreux, fente longue : Q ∝ p^1 (visqueux).
P_ATM = 101325.0       # Pa
RHO = 1.2              # kg/m³


@dataclass
class LeakFlow:
    p: np.ndarray        # pression au milieu de chaque intervalle (Pa)
    q_lpm: np.ndarray    # débit de fuite (L/min)
    c: float             # loi q = c · p^n (q en L/min, p en Pa)
    n: float             # exposant : ~0,5 trou ; ~1 pores / fente longue
    r2: float
    q_ref_lpm: float     # débit à la pression de référence
    p_ref: float
    hole_mm: float       # diamètre du trou rond qui fuirait autant à p_ref (Cd = 0,6)


def leak_flow_curve(t, p, volume_m3, p_ref=500.0, p_atm=P_ATM, smooth_n=5,
                    p_min=20.0) -> LeakFlow:
    """Débit de fuite le long d'une chute de pression, et sa loi q = c·p^n.

    `t` (s), `p` (Pa, relatif à l'air ambiant), `volume_m3` = volume fermé
    **total** (pièce testée + tuyaux + volume tampon). Les points sous `p_min`
    (bruit du capteur) sont écartés."""
    t = np.asarray(t, dtype="float64")
    p = np.asarray(p, dtype="float64")
    if smooth_n > 1 and p.size >= smooth_n:
        k = np.ones(smooth_n) / smooth_n
        p = np.convolve(np.pad(p, (smooth_n // 2, smooth_n - 1 - smooth_n // 2),
                               mode="edge"), k, mode="valid")
    dpdt = np.gradient(p, t)
    q = volume_m3 / p_atm * (-dpdt) * 60000.0          # L/min
    ok = (p > p_min) & (q > 0) & np.isfinite(q)
    pp, qq = p[ok], q[ok]
    nan = float("nan")
    if pp.size < 3:
        return LeakFlow(pp, qq, nan, nan, nan, nan, p_ref, nan)
    X = np.log(pp); Y = np.log(qq)
    A = np.vstack([X, np.ones_like(X)]).T
    (n, lc), *_ = np.linalg.lstsq(A, Y, rcond=None)
    yhat = A @ np.array([n, lc])
    ss = float(((Y - Y.mean()) ** 2).sum()) or 1.0
    r2 = 1.0 - float(((Y - yhat) ** 2).sum()) / ss
    c = float(np.exp(lc))
    q_ref = c * p_ref ** n
    return LeakFlow(pp, qq, c, float(n), r2, float(q_ref), p_ref,
                    equivalent_hole_mm(q_ref, p_ref))


def equivalent_hole_mm(q_lpm, p_pa, cd=0.6, rho=RHO):
    """Diamètre (mm) du trou rond qui laisserait fuir `q_lpm` sous `p_pa`
    (orifice en paroi mince, coefficient de débit `cd`). Une image parlante :
    « ta caisse fuit comme un trou de 1,2 mm »."""
    q = np.asarray(q_lpm, dtype="float64") / 60000.0
    v = np.sqrt(2 * np.maximum(np.asarray(p_pa, dtype="float64"), 0) / rho)
    area = np.where(v > 0, q / (cd * np.maximum(v, 1e-30)), np.nan)
    d = 2 * np.sqrt(np.maximum(area, 0) / np.pi) * 1e3
    return float(d) if np.ndim(d) == 0 else d


def hole_leak_lpm(d_mm, p_pa, cd=0.6, rho=RHO):
    """Débit (L/min) d'un trou rond de `d_mm` sous `p_pa` : l'inverse de
    `equivalent_hole_mm`, pour fixer un budget de fuite."""
    a = np.pi * (np.asarray(d_mm, dtype="float64") * 1e-3) ** 2 / 4
    return cd * a * np.sqrt(2 * np.asarray(p_pa, dtype="float64") / rho) * 60000.0


def decay_time_s(q_lpm, volume_m3, p_start=500.0, p_end=400.0, n=0.5,
                 p_atm=P_ATM):
    """Temps de chute de `p_start` à `p_end` d'un volume fermé dont la fuite
    vaut `q_lpm` **à p_start** et suit q ∝ p^n. Sert à écrire un critère en
    secondes à partir d'un budget en L/min (et inversement)."""
    q0 = q_lpm / 60000.0
    k = q0 / p_start ** n                       # q = k p^n (m³/s)
    a = p_atm / volume_m3 * k                   # dp/dt = -a p^n
    if abs(n - 1.0) < 1e-9:
        return float(np.log(p_start / p_end) / a)
    return float((p_start ** (1 - n) - p_end ** (1 - n)) / ((1 - n) * a))


def accumulation_flow(t, p, bell_volume_m3, p_atm=P_ATM):
    """Méthode de la **cloche d'accumulation** : une petite cloche étanche
    (imprimée en 3D, joint mousse) posée sur une soupape ou un joint, côté
    air libre, pendant que l'instrument est sous pression. La fuite remplit la
    cloche : la pression y monte. Débit (L/min) = V_cloche / p_atm · dp/dt,
    pente prise par moindres carrés sur le début de la montée.

    Très sensible : avec 20 cm³ et un capteur au dixième de pascal, on voit
    ~10⁻⁵ L/min. Une soupape à la fois, sans démonter."""
    t = np.asarray(t, dtype="float64"); p = np.asarray(p, dtype="float64")
    if t.size < 3:
        return float("nan")
    A = np.vstack([t, np.ones_like(t)]).T
    slope = np.linalg.lstsq(A, p, rcond=None)[0][0]
    return float(bell_volume_m3 / p_atm * slope * 60000.0)

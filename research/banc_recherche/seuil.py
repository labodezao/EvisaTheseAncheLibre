"""Seuils d'auto-entretien de l'anche (rampe de pression + hystérésis).

Reprend `mes_seuil_autoentretien.py` : on monte lentement la pression jusqu'au
démarrage de l'oscillation (`p_on`), puis on redescend jusqu'à l'extinction
(`p_off`). L'écart `p_on - p_off` = hystérésis, caractéristique de l'anche.

Depuis le 03/10/2026, le module mesure aussi **le haut de la plage** (terme de
Bernard Bonin : « seuils d'auto-entretien ») :

- `p_choke` : en montée, la pression où l'anche **se plaque** (elle se tait
  alors que la pression monte encore) ;
- `p_unchoke` : en descente, la pression où elle **repart** après le plaquage ;
- la **plage utile** `p_choke - p_on` et le **rapport** `p_choke / p_on`.

Il dit si l'anche oscille par deux indices du son, pas un seul :
le **niveau** (dB) et la **périodicité** (clarté NSDF de McLeod, 0 à 1). Le
souffle seul monte en niveau avec la pression, mais il n'est pas périodique :
sans la clarté, on prendrait le bruit d'air pour une note.

Il trace enfin le niveau sonore et le débit en fonction de la pression
(`bin_curve`, `flow_law`), et sépare deux anches jouées ensemble
(`reed_presence`), pour la question « deux anches démarrent-elles plus tôt
ou plus tard qu'une seule ? ».

Tout est en numpy seul (tests légers) ; rien n'est importé de lourd.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

RHO_AIR = 1.2          # kg/m³, air à ~20 °C


# ---------------------------------------------------------------------------
# 1. L'ancienne détection (gardée telle quelle : utilisée ailleurs et testée)
# ---------------------------------------------------------------------------
@dataclass
class ThresholdResult:
    p_on: float          # pression de démarrage (montée)
    p_off: float         # pression d'extinction (descente)
    hysteresis: float    # p_on - p_off


def detect(pressure: np.ndarray, amplitude: np.ndarray,
           amp_thresh: float) -> ThresholdResult:
    """Trouve p_on / p_off à partir des traces synchrones pression/amplitude.

    `pressure` et `amplitude` doivent couvrir une rampe montante puis descendante
    (concaténées). `amp_thresh` = seuil d'amplitude marquant l'oscillation.
    """
    pressure = np.asarray(pressure, dtype="float64")
    amplitude = np.asarray(amplitude, dtype="float64")
    peak = int(np.argmax(pressure))          # sommet de la rampe
    up_p, up_a = pressure[:peak + 1], amplitude[:peak + 1]
    dn_p, dn_a = pressure[peak:], amplitude[peak:]

    on_idx = np.where(up_a > amp_thresh)[0]
    off_idx = np.where(dn_a < amp_thresh)[0]
    p_on = float(up_p[on_idx[0]]) if len(on_idx) else float("nan")
    p_off = float(dn_p[off_idx[0]]) if len(off_idx) else float("nan")
    return ThresholdResult(p_on, p_off, p_on - p_off)


# ---------------------------------------------------------------------------
# 2. Indices du son, trame par trame : niveau, clarté, f0
# ---------------------------------------------------------------------------
@dataclass
class Features:
    t: np.ndarray          # centre des trames (s)
    level_db: np.ndarray   # niveau RMS (dB pleine échelle, ou dB SPL si étalonné)
    clarity: np.ndarray    # périodicité 0..1 (pic NSDF après le premier passage par 0)
    f0: np.ndarray         # fréquence estimée (Hz), nan si pas de pic


def _frames(x, n, hop):
    count = 1 + (x.size - n) // hop if x.size >= n else 0
    idx = np.arange(n)[None, :] + hop * np.arange(count)[:, None]
    return x[idx]


def frame_features(sig, fs, frame_s=0.05, hop_s=0.025, fmin=40.0, fmax=2500.0,
                   calib_db=0.0) -> Features:
    """Niveau, clarté (NSDF de McLeod) et f0, trame par trame.

    La clarté vaut ~1 pour un son périodique (anche qui sonne) et reste basse
    pour le souffle. Elle est prise au **plus haut pic après le premier
    passage par zéro** de la NSDF, comme chez McLeod & Wyvill (2005) : un bruit
    coloré garde une forte corrélation aux tout petits décalages, ce critère
    l'écarte.

    `frame_s` doit couvrir au moins deux périodes de la note la plus grave
    (50 ms : jusqu'à 40 Hz). `calib_db` s'ajoute au niveau (étalonnage du micro).
    """
    x = np.asarray(sig, dtype="float64")
    n = max(8, int(round(frame_s * fs)))
    hop = max(1, int(round(hop_s * fs)))
    fr = _frames(x, n, hop)
    if fr.shape[0] == 0:
        e = np.array([])
        return Features(e, e, e, e)
    fr = fr - fr.mean(axis=1, keepdims=True)
    rms = np.sqrt(np.mean(fr ** 2, axis=1))
    level = 20 * np.log10(rms + 1e-12) + calib_db

    # Autocorrélation par FFT (zéro-padding pour éviter le repliement circulaire).
    nfft = 1 << int(np.ceil(np.log2(2 * n)))
    F = np.fft.rfft(fr, nfft, axis=1)
    r = np.fft.irfft(np.abs(F) ** 2, nfft, axis=1)[:, :n]
    # m(τ) = Σ x_j² + x_{j+τ}² sur le recouvrement (sommes cumulées).
    cs = np.concatenate([np.zeros((fr.shape[0], 1)), np.cumsum(fr ** 2, axis=1)], axis=1)
    tau = np.arange(n)
    m = cs[:, n - tau] + (cs[:, n:n + 1] - cs[:, tau])
    nsdf = np.where(m > 0, 2 * r / np.maximum(m, 1e-30), 0.0)

    tmin = max(1, int(fs / fmax))
    tmax = min(n - 2, int(fs / fmin))
    nfr = fr.shape[0]
    clar = np.zeros(nfr)
    f0 = np.full(nfr, np.nan)
    for i in range(nfr):
        row = nsdf[i]
        neg = np.flatnonzero(row[:tmax + 1] < 0)
        if not neg.size:
            continue                       # jamais négative : bruit très grave ou silence
        lo = max(int(neg[0]), tmin)
        seg = row[lo:tmax + 1]
        if seg.size < 3:
            continue
        top = float(seg.max())
        if top <= 0:
            continue
        # Premier pic qui atteint 90 % du plus haut (McLeod & Wyvill) : les
        # multiples de la période ont presque la même hauteur, il faut le
        # premier, sinon on lit une octave ou une quinte trop bas.
        j = int(np.flatnonzero(seg >= 0.9 * top)[0])
        while j + 1 < seg.size and seg[j + 1] > seg[j]:
            j += 1
        k = lo + j
        clar[i] = float(seg[j])
        if 1 <= k < n - 1:
            a, b, c = row[k - 1], row[k], row[k + 1]
            den = a - 2 * b + c
            sh = 0.5 * (a - c) / den if abs(den) > 1e-12 else 0.0
            f0[i] = fs / (k + float(np.clip(sh, -0.5, 0.5)))
    t = (np.arange(fr.shape[0]) * hop + n / 2) / fs
    return Features(t, level, np.clip(clar, 0.0, 1.0), f0)


# ---------------------------------------------------------------------------
# 3. L'anche sonne-t-elle ? (deux indices + anti-rebond)
# ---------------------------------------------------------------------------
def noise_floor_db(level_db, clarity, clarity_noise=0.5):
    """Niveau du fond (souffle, pièce) : médiane des trames **non périodiques**.
    Repli : 10e centile du niveau."""
    level_db = np.asarray(level_db, dtype="float64")
    clarity = np.asarray(clarity, dtype="float64")
    sel = clarity < clarity_noise
    if sel.sum() >= 3:
        return float(np.median(level_db[sel]))
    return float(np.percentile(level_db, 10)) if level_db.size else float("nan")


def _debounce(state, t, hold_s):
    """Un changement d'état n'est retenu que s'il dure au moins `hold_s`
    (évite qu'un raté d'une trame ne compte comme un démarrage)."""
    state = np.asarray(state, dtype=bool).copy()
    t = np.asarray(t, dtype="float64")
    if state.size == 0 or hold_s <= 0:
        return state
    out = state.copy()
    cur = state[0]
    i = 0
    n = state.size
    while i < n:
        j = i
        while j < n and state[j] == state[i]:
            j += 1
        dur = (t[j - 1] - t[i]) if j - 1 > i else 0.0
        if state[i] != cur and dur < hold_s:
            out[i:j] = cur                     # trop court : on garde l'état précédent
        else:
            cur = state[i]
        i = j
    return out


def oscillating(level_db, clarity, t=None, clarity_min=0.8, margin_db=6.0,
                floor_db=None, hold_s=0.15):
    """Masque booléen « l'anche sonne » : périodique **et** au-dessus du fond.

    - `clarity_min` : périodicité minimale (0,8 par défaut ; le souffle reste
      sous 0,5 en général) ;
    - `margin_db` : marge au-dessus du fond (`floor_db`, estimé si absent) ;
    - `hold_s` : durée minimale d'un changement d'état (anti-rebond).
    """
    level_db = np.asarray(level_db, dtype="float64")
    clarity = np.asarray(clarity, dtype="float64")
    if floor_db is None:
        floor_db = noise_floor_db(level_db, clarity)
    raw = (clarity >= clarity_min) & (level_db >= floor_db + margin_db)
    if t is None:
        return raw
    return _debounce(raw, t, hold_s)


# ---------------------------------------------------------------------------
# 4. Les seuils sur une rampe montée-descente
# ---------------------------------------------------------------------------
@dataclass
class RampThresholds:
    p_on: float              # démarrage, en montée
    p_off: float             # extinction, en descente
    p_choke: float           # plaquage, en montée (nan si jamais atteint)
    p_unchoke: float         # reprise après plaquage, en descente (nan sinon)
    p_max: float             # sommet de la rampe
    hysteresis: float        # p_on - p_off (> 0 : bifurcation sous-critique)
    choke_hysteresis: float  # p_choke - p_unchoke
    usable_range: float      # p_choke - p_on (ou p_max - p_on si pas de plaquage)
    ratio: float             # p_choke / p_on (ou p_max / p_on)
    choke_reached: bool
    rate_on: float           # vitesse de rampe au démarrage (Pa/s)
    rate_off: float          # vitesse de rampe à l'extinction (Pa/s, négative)


def _smooth(x, n):
    if n <= 1 or x.size < n:
        return x
    k = np.ones(n) / n
    pad = np.pad(x, (n // 2, n - 1 - n // 2), mode="edge")
    return np.convolve(pad, k, mode="valid")


def _transitions(state, rising):
    s = state.astype(int)
    d = np.diff(s)
    return np.where(d == (1 if rising else -1))[0] + 1


def ramp_thresholds(t, p, osc, lag_s=0.0, smooth_n=5) -> RampThresholds:
    """Seuils d'une rampe **montée puis descente**, sur une base de temps commune.

    `t` (s), `p` (Pa) et `osc` (booléen « l'anche sonne ») ont la même longueur
    (utiliser `align` si la pression et le son ont deux horloges).

    `lag_s` corrige le **retard du capteur de pression** (filtre IIR du BMP280,
    filtre médian du firmware) : la vraie pression à l'instant t est celle lue
    à t + lag_s. Sans cette correction, le retard **fausse l'hystérésis** de
    2 × vitesse × retard, et dans le sens qui la cache : en montée le capteur
    lit trop bas (p_on paraît plus bas), en descente trop haut (p_off paraît
    plus haut). Le temps que met l'oscillation à grandir ou à mourir fait
    l'inverse (il gonfle l'hystérésis). Les deux sont proportionnels à la
    vitesse : `zero_rate_threshold` les retire ensemble.
    """
    t = np.asarray(t, dtype="float64")
    p = np.asarray(p, dtype="float64")
    osc = np.asarray(osc, dtype=bool)
    nan = float("nan")
    if t.size < 3:
        return RampThresholds(nan, nan, nan, nan, nan, nan, nan, nan, nan, False, nan, nan)
    if lag_s:
        p = np.interp(t + lag_s, t, p)
    ps = _smooth(p, smooth_n)
    peak = int(np.argmax(ps))
    rate = np.gradient(ps, t)

    up = slice(0, peak + 1)
    dn = slice(peak, t.size)
    o_up, o_dn = osc[up], osc[dn]
    p_up, p_dn = ps[up], ps[dn]

    on_tr = _transitions(o_up, rising=True)
    if o_up.size and o_up[0]:
        # Elle sonnait déjà au départ : le démarrage est sous le bas de la
        # rampe, inconnu. On cherche quand même le plaquage plus haut.
        on_tr = np.concatenate([[0], on_tr])
    p_on = float(p_up[on_tr[0]]) if on_tr.size and not o_up[0] else nan
    i_on = int(on_tr[0]) if on_tr.size else None

    p_choke = nan
    if i_on is not None:
        off_after = _transitions(o_up[i_on:], rising=False)
        if off_after.size:
            p_choke = float(p_up[i_on + off_after[0]])
    choke = np.isfinite(p_choke)

    p_unchoke = nan
    if choke:
        on_dn = _transitions(o_dn, rising=True)
        if on_dn.size:
            p_unchoke = float(p_dn[on_dn[0]])
    off_dn = _transitions(o_dn, rising=False)
    p_off = float(p_dn[off_dn[-1]]) if off_dn.size else nan

    p_max = float(ps[peak])
    top = p_choke if choke else p_max
    rng = top - p_on if np.isfinite(p_on) else nan
    ratio = top / p_on if np.isfinite(p_on) and p_on > 0 else nan
    r_on = float(rate[up][on_tr[0]]) if np.isfinite(p_on) else nan
    r_off = float(rate[dn][off_dn[-1]]) if off_dn.size else nan
    return RampThresholds(p_on, p_off, p_choke, p_unchoke, p_max,
                          p_on - p_off, p_choke - p_unchoke, rng, ratio,
                          bool(choke), r_on, r_off)


def split_cycles(t, p, min_rise=20.0, smooth_n=9):
    """Découpe un enregistrement en cycles montée-descente (rampes répétées).

    Renvoie une liste de tranches `slice(i0, i1)`, chacune allant d'un creux
    au creux suivant en passant par un sommet. `min_rise` (Pa) : amplitude
    minimale d'un aller ou d'un retour (évite de couper sur le bruit). Un
    enregistrement qui commence en descendant perd ce premier morceau ; un
    enregistrement qui finit en montant garde sa dernière montée seule."""
    p = _smooth(np.asarray(p, dtype="float64"), smooth_n)
    n = p.size
    if n < 3:
        return []
    piv = []                      # (indice, "min" | "max")
    trend = 0
    lo = hi = cand = 0
    for i in range(1, n):
        if trend == 0:
            if p[i] < p[lo]:
                lo = i
            if p[i] > p[hi]:
                hi = i
            if p[i] - p[lo] >= min_rise:
                piv.append((lo, "min")); trend = 1; cand = i
            elif p[hi] - p[i] >= min_rise:
                piv.append((hi, "max")); trend = -1; cand = i
        elif trend == 1:
            if p[i] > p[cand]:
                cand = i
            elif p[cand] - p[i] >= min_rise:
                piv.append((cand, "max")); trend = -1; cand = i
        else:
            if p[i] < p[cand]:
                cand = i
            elif p[i] - p[cand] >= min_rise:
                piv.append((cand, "min")); trend = 1; cand = i
    if trend != 0:
        piv.append((cand, "max" if trend == 1 else "min"))
    cycles = []
    for k, (i, kind) in enumerate(piv):
        if kind != "max" or k == 0 or piv[k - 1][1] != "min":
            continue
        a = piv[k - 1][0]
        b = piv[k + 1][0] if k + 1 < len(piv) else n - 1
        if b > a + 2:
            cycles.append(slice(a, b + 1))
    return cycles


@dataclass
class CycleSummary:
    cycles: list = field(default_factory=list)     # un RampThresholds par cycle
    mean: dict = field(default_factory=dict)       # moyenne par grandeur
    std: dict = field(default_factory=dict)        # écart-type par grandeur


_KEYS = ("p_on", "p_off", "p_choke", "p_unchoke", "hysteresis",
         "usable_range", "ratio")


def cycles_thresholds(t, p, osc, lag_s=0.0, min_rise=20.0) -> CycleSummary:
    """Seuils de chaque cycle d'un enregistrement à rampes répétées, puis
    moyenne et écart-type : le bruit rend le seuil **distribué**."""
    out = CycleSummary()
    t = np.asarray(t, dtype="float64"); p = np.asarray(p, dtype="float64")
    osc = np.asarray(osc, dtype=bool)
    for sl in split_cycles(t, p, min_rise=min_rise):
        out.cycles.append(ramp_thresholds(t[sl], p[sl], osc[sl], lag_s=lag_s))
    for k in _KEYS:
        v = np.array([getattr(c, k) for c in out.cycles], dtype="float64")
        out.mean[k] = float(np.nanmean(v)) if np.isfinite(v).any() else float("nan")
        out.std[k] = float(np.nanstd(v)) if np.isfinite(v).sum() > 1 else float("nan")
    return out


def zero_rate_threshold(rates, thresholds):
    """Seuil **quasi statique** par extrapolation à vitesse nulle.

    Deux effets décalent un seuil mesuré en rampe, tous deux proportionnels à
    la vitesse : le **retard du capteur** et le **retard à la bifurcation**
    (une oscillation qui démarre pendant une rampe apparaît plus tard que son
    seuil statique ; Bergeot et coll. 2013, sur la clarinette). On mesure à
    deux vitesses au moins et on prolonge la droite seuil(|vitesse|) jusqu'à 0.

    Renvoie (seuil_à_vitesse_nulle, pente en Pa par Pa/s)."""
    r = np.abs(np.asarray(rates, dtype="float64"))
    y = np.asarray(thresholds, dtype="float64")
    ok = np.isfinite(r) & np.isfinite(y)
    if ok.sum() < 2 or np.ptp(r[ok]) == 0:
        return float("nan"), float("nan")
    A = np.vstack([r[ok], np.ones(ok.sum())]).T
    (slope, icpt), *_ = np.linalg.lstsq(A, y[ok], rcond=None)
    return float(icpt), float(slope)


def align(t_ref, t_src, values):
    """Ramène une grandeur échantillonnée à `t_src` sur la base de temps `t_ref`
    (interpolation linéaire ; nan hors de l'intervalle commun)."""
    t_ref = np.asarray(t_ref, dtype="float64")
    t_src = np.asarray(t_src, dtype="float64")
    v = np.asarray(values, dtype="float64")
    out = np.interp(t_ref, t_src, v)
    out[(t_ref < t_src.min()) | (t_ref > t_src.max())] = np.nan
    return out


# ---------------------------------------------------------------------------
# 5. Courbes de fonctionnement : niveau, débit, rendement
# ---------------------------------------------------------------------------
def bin_curve(x, y, edges):
    """Moyenne de `y` par classes de `x` : renvoie (centres, moyenne, écart-type,
    effectif). Sert à tracer L(p), Q(p), f0(p) en montée ou en descente."""
    x = np.asarray(x, dtype="float64"); y = np.asarray(y, dtype="float64")
    edges = np.asarray(edges, dtype="float64")
    ok = np.isfinite(x) & np.isfinite(y)
    idx = np.digitize(x[ok], edges) - 1
    nb = edges.size - 1
    mean = np.full(nb, np.nan); std = np.full(nb, np.nan); cnt = np.zeros(nb, int)
    for k in range(nb):
        v = y[ok][idx == k]
        cnt[k] = v.size
        if v.size:
            mean[k] = v.mean()
            std[k] = v.std() if v.size > 1 else 0.0
    return 0.5 * (edges[:-1] + edges[1:]), mean, std, cnt


def flow_law(p, q):
    """Ajuste `q = C · p^n` (log-log). Un orifice franc donne n ≈ 0,5
    (Bernoulli) ; une fente longue et étroite, où la viscosité domine, tire vers
    n ≈ 1 (Poiseuille). Renvoie (C, n, r²)."""
    p = np.asarray(p, dtype="float64"); q = np.asarray(q, dtype="float64")
    ok = np.isfinite(p) & np.isfinite(q) & (p > 0) & (q > 0)
    if ok.sum() < 3:
        return float("nan"), float("nan"), float("nan")
    X = np.log(p[ok]); Y = np.log(q[ok])
    A = np.vstack([X, np.ones_like(X)]).T
    (n, lc), *_ = np.linalg.lstsq(A, Y, rcond=None)
    yhat = A @ np.array([n, lc])
    ss_tot = float(((Y - Y.mean()) ** 2).sum()) or 1.0
    r2 = 1.0 - float(((Y - yhat) ** 2).sum()) / ss_tot
    return float(np.exp(lc)), float(n), r2


def effective_area_mm2(p_pa, q_m3s, rho=RHO_AIR):
    """Aire efficace d'écoulement (mm²) : la section d'un orifice idéal qui
    laisserait passer le même débit sous la même pression (Bernoulli)."""
    p = np.asarray(p_pa, dtype="float64"); q = np.asarray(q_m3s, dtype="float64")
    v = np.sqrt(2 * np.maximum(p, 0) / rho)
    return np.where(v > 0, q / np.maximum(v, 1e-30) * 1e6, np.nan)


def slm_to_m3s(q_slm):
    """Litres par minute → m³/s."""
    return np.asarray(q_slm, dtype="float64") / 60000.0


def efficiency_db(level_db, p_pa, q_m3s):
    """Rendement **relatif** en dB : niveau sonore moins 10·log10(puissance
    pneumatique p·Q). Sa valeur absolue n'a de sens qu'avec un micro étalonné
    et une puissance acoustique ; ses **écarts** (d'une anche à l'autre, d'un
    réglage à l'autre, même micro, même place) en ont déjà."""
    w = np.asarray(p_pa, dtype="float64") * np.asarray(q_m3s, dtype="float64")
    return np.asarray(level_db, dtype="float64") - 10 * np.log10(np.maximum(w, 1e-30))


# ---------------------------------------------------------------------------
# 6. Deux anches ensemble : qui sonne ?
# ---------------------------------------------------------------------------
def reed_presence(sig, fs, freqs, frame_s=0.5, hop_s=0.1, half_bw_hz=None):
    """Niveau (dB) de chaque anche, trame par trame, lu dans une bande étroite
    autour de **sa** fondamentale.

    `freqs` : fréquences de jeu des anches (mesurées seules, à l'accordeur).
    La fenêtre doit séparer les deux raies : résolution ≈ 2/frame_s Hz. Deux
    anches à 440 et 443 Hz (musette ~12 cents) demandent frame_s ≥ 0,7 s ;
    sous cette limite, la fonction lève une erreur au lieu de mentir.
    Pour 16' + 8' (octave), la fondamentale de l'anche grave reste seule à sa
    place ; celle de l'aiguë se mêle à l'harmonique 2 de la grave : préférer
    alors la méthode de la bande de papier (une anche bloquée, puis l'autre).

    Renvoie (t, niveaux) avec niveaux de forme (n_trames, n_anches)."""
    x = np.asarray(sig, dtype="float64")
    freqs = np.asarray(freqs, dtype="float64")
    n = int(round(frame_s * fs)); hop = max(1, int(round(hop_s * fs)))
    res = 2.0 / frame_s
    if freqs.size > 1:
        gaps = np.diff(np.sort(freqs))
        if gaps.min() < res:
            raise ValueError(
                f"raies trop proches ({gaps.min():.2f} Hz) pour une fenêtre de "
                f"{frame_s} s (résolution ~{res:.2f} Hz) : allonger frame_s")
    hb = half_bw_hz if half_bw_hz is not None else (
        0.5 * np.diff(np.sort(freqs)).min() if freqs.size > 1 else 0.03 * freqs[0])
    fr = _frames(x, n, hop)
    if fr.shape[0] == 0:
        return np.array([]), np.zeros((0, freqs.size))
    w = np.hanning(n)
    X = np.abs(np.fft.rfft((fr - fr.mean(axis=1, keepdims=True)) * w, axis=1)) ** 2
    f = np.fft.rfftfreq(n, 1.0 / fs)
    out = np.empty((fr.shape[0], freqs.size))
    for i, f0 in enumerate(freqs):
        band = (f >= f0 - hb) & (f <= f0 + hb)
        out[:, i] = 10 * np.log10(X[:, band].sum(axis=1) / (np.sum(w ** 2) * n) + 1e-20)
    t = (np.arange(fr.shape[0]) * hop + n / 2) / fs
    return t, out


@dataclass
class PairComparison:
    p_on_a: float
    p_on_b: float
    p_on_pair: float
    help_pa: float          # min(p_on_a, p_on_b) - p_on_pair (> 0 : ensemble, elles démarrent plus tôt)
    q_a: float
    q_b: float
    q_pair: float
    q_excess: float         # q_pair - (q_a + q_b) à pression égale (< 0 : elles se partagent l'air)


def compare_pair(p_on_a, p_on_b, p_on_pair, q_a=float("nan"), q_b=float("nan"),
                 q_pair=float("nan")) -> PairComparison:
    """Compare une paire d'anches à chacune seule (même sommier, même
    pression de référence pour les débits).

    Si la paire démarre plus bas que la meilleure des deux, la chambre les
    couple et elles s'aident ; plus haut, elles se gênent. Le débit dit si la
    paire coûte plus ou moins d'air que la somme des deux."""
    help_pa = min(p_on_a, p_on_b) - p_on_pair
    q_ex = q_pair - (q_a + q_b)
    return PairComparison(p_on_a, p_on_b, p_on_pair, help_pa, q_a, q_b, q_pair, q_ex)


# ---------------------------------------------------------------------------
# 7. Tout d'un coup, depuis l'export de l'onglet Banc (ou un WAV + une trace P)
# ---------------------------------------------------------------------------
@dataclass
class RunAnalysis:
    summary: CycleSummary
    t: np.ndarray
    p: np.ndarray
    q: np.ndarray
    level_db: np.ndarray
    clarity: np.ndarray
    osc: np.ndarray
    floor_db: float
    flow: tuple = (float("nan"), float("nan"), float("nan"))   # (C, n, r²) de q = C·p^n


def analyse_run(t, p, level_db, clarity, q=None, lag_s=0.0, clarity_min=0.8,
                margin_db=6.0, hold_s=0.15, min_rise=20.0) -> RunAnalysis:
    """Chaîne complète sur des traces déjà alignées (une ligne par instant) :
    l'anche sonne-t-elle, seuils par cycle, loi de débit sur les instants où
    elle sonne."""
    t = np.asarray(t, dtype="float64"); p = np.asarray(p, dtype="float64")
    level_db = np.asarray(level_db, dtype="float64")
    clarity = np.nan_to_num(np.asarray(clarity, dtype="float64"), nan=0.0)
    q = np.full_like(p, np.nan) if q is None else np.asarray(q, dtype="float64")
    floor = noise_floor_db(level_db, clarity)
    osc = oscillating(level_db, clarity, t, clarity_min, margin_db, floor, hold_s)
    summ = cycles_thresholds(t, p, osc, lag_s=lag_s, min_rise=min_rise)
    flow = flow_law(p[osc], q[osc]) if np.isfinite(q).any() else (float("nan"),) * 3
    return RunAnalysis(summ, t, p, q, level_db, clarity, osc, floor, flow)


def read_bench_csv(path):
    """Lit l'export « Seuils » de l'onglet Banc (`seuils_*.csv`).
    Colonnes attendues : t_s, p_Pa, q_slm, level_db, clarity, f0_Hz (les
    lignes de commentaire commencent par #). Renvoie un dict de tableaux."""
    import csv
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        lines = [ln for ln in fh if ln.strip() and not ln.startswith("#")]
    rd = csv.DictReader(lines)
    for r in rd:
        rows.append(r)
    def col(name):
        v = []
        for r in rows:
            s = (r.get(name) or "").strip()
            try:
                v.append(float(s))
            except ValueError:
                v.append(float("nan"))
        return np.array(v, dtype="float64")
    return {k: col(k) for k in ("t_s", "p_Pa", "q_slm", "level_db", "clarity", "f0_Hz")}

# -*- coding: utf-8 -*-
"""Extraction des grandeurs de chaque enregistrement des campagnes 2023 (anche libre).

LECTURE SEULE des données de D:\\GoogleDrive\\python\\Mesure anches.
Sortie : journal\\recherche\\mesures_2023.csv (une ligne par enregistrement).

Par enregistrement :
- pneumatique (Pyboard, ~100 Hz) : pression (BMP280, unité à confirmer, sans doute Pa
  relatifs), débit (SFM3000, l/min standard), température (°C), moyennes sur la
  dernière seconde (régime établi) et sur le début (avant ouverture du clapet) ;
- acoustique (micro non étalonné, 48 kHz, int32 -> divisé par 2^31) : niveau RMS
  début / fin, fréquence de jeu f0 sur la fin (2,0 s -> fin), amplitude des 10
  premiers harmoniques, part de l'énergie portée par les harmoniques (harmonicité).

Lancer : J:\\claude\\venv\\Scripts\\python.exe extraire_mesures.py
"""
import csv, glob, os, re, datetime
import numpy as np
import h5py
from scipy.io import wavfile

B = r"D:\GoogleDrive\python\Mesure anches"
OUT = r"J:\claude\business-os\journal\recherche"

CAMPAGNES = {
    # nom : (dossier wav, source pneumatique, f0 nominale approx. en Hz)
    "2023-04-13 (d1_L)": ("data_d1_L", ("npy", "data_d1_L"), 73.4),
    "2023-04-16 (D#0_1_L_2v)": ("data_D#0_1_L_2v", ("h5", r"data_D#0_1_L_2v\Measure_datasetnSec8nPress8nClap8.hdf5"), 77.8),
    "2023-09-11 (data)": ("data", ("h5", r"data\Measure_datasetnSec8nPress8nClap8.hdf5"), 61.8),
}
SECTIONS_MM2 = [60, 75, 90, 105, 120, 135, 150, 180]  # int(position vis) x 15 mm (voir rapport)
CLAPET_DEG = [int((22 - 2) * (i / 7) + 2) for i in range(8)]
DAC = [int((3500 - 300) * (i / 7) + 300) for i in range(8)]


def serie_valide(x):
    """x : (2, n) avec ligne 0 = temps (pas ~0,01 s), ligne 1 = valeur. Renvoie (t, v) ou None."""
    t, v = np.asarray(x[0], float), np.asarray(x[1], float)
    n = int((t > 0).sum()) + 1
    t, v = t[:n], v[:n]
    if n < 50:
        return None
    d = np.diff(t[1:])
    if np.mean(np.abs(d - 0.01) < 0.003) < 0.9:  # cellule désalignée (transfert série)
        return None
    return t, v


def moyennes(tv, t0=0.0, t1=0.25, fin=1.0):
    if tv is None:
        return np.nan, np.nan
    t, v = tv
    a = v[(t >= t0) & (t < t1)]
    b = v[t >= t[-1] - fin]
    return (a.mean() if a.size else np.nan), (b.mean() if b.size else np.nan)


def analyse_audio(w, sr, fnom):
    w = w.astype(np.float64) / 2**31
    tete = w[: int(0.4 * sr)]
    fin = w[int(2.0 * sr):]
    fin = fin - fin.mean()
    res = {"rms_debut": tete.std(), "rms_fin": fin.std(), "crete": np.abs(w).max()}
    n = len(fin)
    nfft = 16 * n
    X = np.abs(np.fft.rfft(fin * np.hanning(n), nfft))
    f = np.fft.rfftfreq(nfft, 1 / sr)
    df = f[1]
    P = X**2

    def pic(fc, demi=0.06):
        lo, hi = int((fc * (1 - demi)) / df), int((fc * (1 + demi)) / df)
        i = lo + int(np.argmax(X[lo:hi]))
        if 0 < i < len(X) - 1:  # interpolation parabolique en dB
            a, b, c = np.log(X[i - 1] + 1e-30), np.log(X[i] + 1e-30), np.log(X[i + 1] + 1e-30)
            p = 0.5 * (a - c) / (a - 2 * b + c)
        else:
            p = 0.0
        return (i + p) * df, X[i]

    # f0 grossière : pic le plus fort parmi les 4 premiers harmoniques, ramené à k=1
    f1, _ = pic(fnom, 0.12)
    # raffinement : moyenne pondérée de f_k / k sur les harmoniques nets
    fk, ak = [], []
    for k in range(1, 11):
        fc, a = pic(k * f1, 0.02)
        fk.append(fc / k)
        ak.append(a)
    ak = np.array(ak)
    fk = np.array(fk)
    w8 = (ak * np.arange(1, 11)) ** 2
    f0 = float(np.sum(w8 * fk) / np.sum(w8))
    # harmonicité : énergie dans +-2,5 Hz autour de k f0 (k=1..20) / énergie 30-3000 Hz
    band = (f > 30) & (f < 3000)
    harm = np.zeros_like(band)
    for k in range(1, 21):
        harm |= np.abs(f - k * f0) < 2.5
    res["harmonicite"] = float(P[band & harm].sum() / P[band].sum())
    res["f0"] = f0
    ref = ak.max() if ak.max() > 0 else 1.0
    for k in range(10):
        res[f"H{k+1}_dB"] = 20 * np.log10(ak[k] / ref + 1e-12)
    res["centroide_harm"] = float(np.sum(np.arange(1, 11) * ak**2) / np.sum(ak**2))
    return res


def main():
    lignes = []
    for camp, (dw, (kind, src), fnom) in CAMPAGNES.items():
        if kind == "npy":
            Pn = np.load(os.path.join(B, src, "d_Mesures_Press.npy"), mmap_mode="r")
            Qn = np.load(os.path.join(B, src, "d_Mesures_Debit.npy"), mmap_mode="r")
            Tn = np.load(os.path.join(B, src, "d_MesuresTemperature.npy"), mmap_mode="r")
            get = lambda c: (Pn[c], Qn[c], Tn[c])
            h = None
        else:
            h = h5py.File(os.path.join(B, src), "r")
            get = lambda c, h=h: (h["Mesures_Press"][c], h["Mesures_Debit"][c], h["MesuresTemperature"][c])
        for fn in sorted(glob.glob(os.path.join(B, dw, "*.wav"))):
            k = tuple(map(int, re.findall(r"\d+", os.path.basename(fn))))
            ppos, sec, pp, cl = k
            sr, w = wavfile.read(fn)
            a = analyse_audio(w, sr, fnom)
            p, q, t = get(k)
            ps, qs, ts = serie_valide(p), serie_valide(q), serie_valide(t)
            p_deb, p_fin = moyennes(ps)
            q_deb, q_fin = moyennes(qs)
            _, t_fin = moyennes(ts)
            p_std = ps[1][ps[0] >= ps[0][-1] - 1.0].std() if ps is not None else np.nan
            lignes.append({
                "campagne": camp, "fichier": os.path.basename(fn),
                "horodatage": datetime.datetime.fromtimestamp(os.path.getmtime(fn)).isoformat(timespec="seconds"),
                "ppos": ppos, "isec": sec, "section_mm2": SECTIONS_MM2[sec], "ipress": pp, "dac": DAC[pp],
                "iclap": cl, "clapet_deg": CLAPET_DEG[cl],
                "p_debut": p_deb, "p_fin": p_fin, "p_fin_std": p_std, "q_debut": q_deb, "q_fin": q_fin,
                "T_fin": t_fin, "pneu_valide": int(ps is not None), **a,
            })
        if h is not None:
            h.close()
        print(camp, "ok", sum(1 for l in lignes if l["campagne"] == camp))
    cles = list(lignes[0].keys())
    with open(os.path.join(OUT, "mesures_2023.csv"), "w", newline="", encoding="utf-8") as fo:
        wr = csv.DictWriter(fo, fieldnames=cles)
        wr.writeheader()
        for l in lignes:
            wr.writerow({c: (f"{v:.6g}" if isinstance(v, float) else v) for c, v in l.items()})


if __name__ == "__main__":
    main()

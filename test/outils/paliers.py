"""Paliers de soufflet sur une anche seule : part du niveau, part du reste (audit du 10/10/2026,
docs/AUDIT-REPETABILITE.md).

    python test/outils/paliers.py session.wav images.jsonl sortie.csv

images.jsonl : node test/outils/images.mjs session.wav '{"mode":"auto"}' 0 107 > images.jsonl

1. Suivi court independant (T = 0.25 s) : pour chaque image du moteur, les
   partiels k = 1..6 de la note sont heterodynes, filtres, et leur phase
   depliee est ajustee par une droite ; fusion ponderee (A k)^2 des partiels
   qui concordent a 1.5 c de la mediane (comme le moteur, mais sur 0.25 s).
2. Decoupage en paliers : coupure a chaque creux de niveau (> 5 dB sous la
   mediane glissante), a chaque saut de la hauteur courte (> 2.5 c entre
   medianes de 0.5 s), a chaque changement de note. Paliers >= 1.2 s.
3. Par palier : dB moyen (partiel le plus fort), hauteur courte (mediane des
   60 % finaux), sigma intra, moteur (mediane des 60 % finaux), moteur a
   +1.0 s apres la premiere valeur fine (instant de validation le plus tot),
   moteur a la fin.
4. Par note : regression cents = a + b dB sur les paliers ; residu ; modele
   a deux ordonnees (paliers alternes = deux sens du soufflet) a pente commune.
"""
import sys, json, math, csv
import numpy as np, scipy.io.wavfile as wv
from scipy.signal import butter, sosfiltfilt

wav, jsonl, out = sys.argv[1], sys.argv[2], sys.argv[3]
T = 0.25
sr, x = wv.read(wav)
x = x.astype(float) / 32768.0
if x.ndim > 1:
    x = x.mean(1)
imgs = [json.loads(l) for l in open(jsonl, encoding='utf-8') if l.startswith('{')]
names = ['Do', 'Do#', 'Re', 'Re#', 'Mi', 'Fa', 'Fa#', 'Sol', 'Sol#', 'La', 'La#', 'Si']
nom = lambda m: names[m % 12] + str(m // 12 - 1)
midi_f = lambda m: 440.0 * 2 ** ((m - 69) / 12)


def suivi(seg, f0):
    tt = np.arange(len(seg)) / sr
    cs, ws, dbs = [], [], []
    for k in range(1, 7):
        fk = k * f0
        if fk > 0.45 * sr:
            break
        half = max(4.0, fk * (2 ** (60 / 1200) - 1))
        z = seg * np.exp(-2j * np.pi * fk * tt)
        sos = butter(4, half / (sr / 2), output='sos')
        zf = sosfiltfilt(sos, z.real) + 1j * sosfiltfilt(sos, z.imag)
        cut = int(0.03 * sr)
        zf = zf[cut:-cut]; tz = tt[cut:-cut]
        ph = np.unwrap(np.angle(zf))
        A = np.vstack([tz, np.ones_like(tz)]).T
        slope = np.linalg.lstsq(A, ph, rcond=None)[0][0]
        fm = (fk + slope / (2 * np.pi)) / k
        amp = np.abs(zf).mean()
        cs.append(1200 * math.log2(fm / f0)); ws.append((amp * k) ** 2); dbs.append(20 * math.log10(amp + 1e-12))
    cs, ws, dbs = np.array(cs), np.array(ws), np.array(dbs)
    med = np.median(cs[ws >= ws.max() * 0.01]) if (ws >= ws.max() * 0.01).any() else np.median(cs)
    ok = np.abs(cs - med) < 1.5
    if not ok.any():
        ok = ws == ws.max()
    c = float((cs[ok] * ws[ok]).sum() / ws[ok].sum())
    return c, float(dbs.max()), int(np.argmax(ws)) + 1, cs


rows = []
for im in imgs:
    m = im['m']
    if m is None or im['q']:
        continue
    n1 = int(round(im['t'] * sr)); n0 = n1 - int(round(T * sr))
    if n0 < 0 or n1 > len(x):
        continue
    c, db, kbest, cs = suivi(x[n0:n1], midi_f(m))
    v = im['v'][0] if im['v'] else None
    cm = v['c'] if v and v['c'] is not None else None
    rows.append(dict(t=im['t'], m=m, lv=im['lv'], cm=cm, h=bool(v and v['h']), st=bool(v and v['st']),
                     c=c, db=db, k=kbest, W=v['W'] if v else 0))

# --- paliers ---------------------------------------------------------------
pal = []
cur = None
tb = [r['t'] for r in rows]
for i, r in enumerate(rows):
    new = cur is None or r['m'] != cur['m'] or r['t'] - cur['rows'][-1]['t'] > 0.3
    if not new and len(cur['rows']) >= 6:
        ref = np.median([q['db'] for q in cur['rows'][-12:]])
        if r['db'] < ref - 5:
            new = True
        if len(cur['rows']) >= 12:
            a = np.median([q['c'] for q in cur['rows'][-6:]])
            b = np.median([q['c'] for q in rows[i:i + 6]]) if i + 6 <= len(rows) else r['c']
            if abs(a - b) > 2.5 and all(rows[j]['m'] == r['m'] for j in range(i, min(i + 6, len(rows)))):
                new = True
    if new:
        cur = dict(m=r['m'], rows=[])
        pal.append(cur)
    cur['rows'].append(r)

res = []
for p in pal:
    rs = p['rows']
    dur = rs[-1]['t'] - rs[0]['t']
    if dur < 1.2:
        continue
    # on ecarte les 0.4 premieres secondes (creux, transitoire du filtre)
    core = [r for r in rs if r['t'] >= rs[0]['t'] + 0.4]
    if len(core) < 8:
        continue
    fin = core[int(len(core) * 0.4):]
    c_court = np.median([r['c'] for r in fin]); s_court = np.std([r['c'] for r in fin])
    db = np.mean([r['db'] for r in fin]); db_min = min(r['db'] for r in core); db_max = max(r['db'] for r in core)
    cm_fin = [r['cm'] for r in fin if r['cm'] is not None]
    c_mot = np.median(cm_fin) if cm_fin else np.nan; s_mot = np.std(cm_fin) if cm_fin else np.nan
    fines = [r for r in rs if r['cm'] is not None and not r['h']]
    t_first = fines[0]['t'] if fines else None
    c_1s = np.nan; c_end = np.nan
    if t_first is not None:
        after = [r for r in rs if r['cm'] is not None and r['t'] >= t_first + 1.0]
        if after:
            c_1s = after[0]['cm']
        c_end = [r['cm'] for r in rs if r['cm'] is not None][-1]
    # pente intra-palier cents/dB (suivi court)
    dbs = np.array([r['db'] for r in core]); ccs = np.array([r['c'] for r in core])
    b_intra = np.polyfit(dbs, ccs, 1)[0] if dbs.max() - dbs.min() > 1.0 else np.nan
    res.append(dict(m=p['m'], t0=rs[0]['t'], t1=rs[-1]['t'], dur=dur, db=db, db_min=db_min, db_max=db_max,
                    c_court=c_court, s_court=s_court, c_mot=c_mot, s_mot=s_mot, c_1s=c_1s, c_end=c_end,
                    t_first=(t_first - rs[0]['t']) if t_first else np.nan, b_intra=b_intra, k=fin[len(fin) // 2]['k']))

with open(out, 'w', encoding='utf-8') as fh:
    fh.write('note;t0;t1;dur_s;dB;dB_min;dB_max;k;c_court;s_court;c_mot;s_mot;c_mot_1s;c_mot_fin;t_1re_fine;pente_intra_c_par_dB\n')
    for r in res:
        fh.write(f"{nom(r['m'])};{r['t0']:.2f};{r['t1']:.2f};{r['dur']:.2f};{r['db']:.1f};{r['db_min']:.1f};{r['db_max']:.1f};{r['k']};"
                 f"{r['c_court']:.2f};{r['s_court']:.2f};{r['c_mot']:.2f};{r['s_mot']:.2f};{r['c_1s']:.2f};{r['c_end']:.2f};{r['t_first']:.2f};{r['b_intra']:.3f}\n")

print(f"{'note':5s} {'t0':>7s} {'dur':>5s} {'dB':>6s} {'k':>2s} {'court':>7s} {'s':>5s} {'mot':>7s} {'s':>5s} {'mot+1s':>7s} {'fin':>7s} {'1re':>5s} {'c/dB':>6s}")
for r in res:
    print(f"{nom(r['m']):5s} {r['t0']:7.2f} {r['dur']:5.1f} {r['db']:6.1f} {r['k']:2d} {r['c_court']:7.2f} {r['s_court']:5.2f} {r['c_mot']:7.2f} {r['s_mot']:5.2f} {r['c_1s']:7.2f} {r['c_end']:7.2f} {r['t_first']:5.2f} {r['b_intra']:6.2f}")

# --- regressions par note ---------------------------------------------------
print('\nPar note : cents (court) = a + b dB ; residu ; deux sens alternes a pente commune')
by = {}
for i, r in enumerate(res):
    by.setdefault(r['m'], []).append(r)
for m, rs in by.items():
    if len(rs) < 3:
        continue
    db = np.array([r['db'] for r in rs]); c = np.array([r['c_court'] for r in rs])
    n = len(rs)
    sd_brut = c.std(ddof=1)
    b, a = np.polyfit(db, c, 1)
    resid = c - (a + b * db)
    sd1 = resid.std(ddof=1) if n > 2 else np.nan
    # deux sens alternes : colonnes [1_pair, 1_impair, dB]
    par = np.array([i % 2 for i in range(n)])
    X = np.vstack([par == 0, par == 1, db]).T.astype(float)
    coef, *_ = np.linalg.lstsq(X, c, rcond=None)
    r2 = c - X @ coef
    sd2 = r2.std(ddof=1) * math.sqrt((n - 1) / max(1, n - 3)) if n > 3 else np.nan
    # deux sens, sans niveau
    X0 = np.vstack([par == 0, par == 1]).T.astype(float)
    coef0, *_ = np.linalg.lstsq(X0, c, rcond=None)
    sd0 = (c - X0 @ coef0).std(ddof=1) * math.sqrt((n - 1) / max(1, n - 2))
    print(f"{nom(m):5s} n={n:2d} etendue dB {db.min():.1f}..{db.max():.1f} | sd brut {sd_brut:.2f} c | pente {b:+.3f} c/dB, residu {sd1:.2f} c | "
          f"2 sens seuls : residu {sd0:.2f} c | 2 sens + pente {coef[2]:+.3f} c/dB : residu {sd2:.2f} c")

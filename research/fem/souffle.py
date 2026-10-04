"""La soufflerie : seuils de démarrage et d'extinction, fréquence de jeu, à partir d'une
feuille de paliers remplie à la main et de quelques enregistrements.

Pourquoi une feuille à la main
------------------------------
Le capteur de pression (XGZP6847, lu en pression ABSOLUE) et le micro ne partagent pas la
même horloge. Plutôt que de les synchroniser, on monte la pression par paliers : à chaque
palier on lit la pression, on écoute, on note « sonne » ou « ne sonne pas ». Le seuil est
entre deux paliers ; son incertitude est la demi-marche. C'est le geste de la mesure de
seuil par escalier, robuste et sans électronique de plus.

La feuille (CSV, séparateur « ; », virgule ou point décimal)
------------------------------------------------------------
    type;cycle;sens;p_lue_Pa;sonne;fichier;t0_s;t1_s;remarque
    zero;;;101312;;;;;avant, soufflerie arrêtée
    palier;1;monte;101330;non;;;;
    palier;1;monte;101336;oui;;;;
    palier;1;descend;101333;oui;;;;
    palier;1;descend;101328;non;;;;
    jeu;1;;101380;oui;jeu_1p5.wav;;;1,5 fois le seuil
    zero;;;101318;;;;;après

- `zero` : la pression lue soufflerie ARRÊTÉE (la pression de la pièce), avant et après.
  Le script retranche leur moyenne et signale la dérive.
- `palier` : un palier de l'escalier (`monte` puis `descend`), dans l'ordre où on l'a fait.
- `jeu` : un enregistrement à pression fixe (fichier wav ou m4a, chemin relatif à la feuille ;
  `t0_s`, `t1_s` facultatifs pour n'en prendre qu'un morceau).
- Si la colonne `p_lue_Pa` est déjà une surpression (pas de ligne `zero`), le zéro vaut 0.

Ce qui sort
-----------
p_on et p_off par cycle (milieu de la marche, demi-marche d'incertitude), leurs médianes,
le rapport p_on / p_off (l'hystérésis, prédite par le modèle), et pour chaque
enregistrement la fréquence de jeu et le niveau. `pour_recalage()` rend le dictionnaire
attendu par `recalage.py` (p_on_Pa, f_jeu_Hz).

Usage (depuis `research\\fem\\`) :
  J:\\claude\\venv\\Scripts\\python.exe souffle.py feuille_R12-grave.csv
"""
from __future__ import annotations

import csv
import math
import os
import sys

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(ICI, "..")))           # research/


def _nombre(t):
    t = (t or "").strip().replace("\u202f", "").replace("\xa0", "").replace(" ", "").replace(",", ".")
    return float(t) if t else None


def _oui(t):
    return (t or "").strip().lower() in ("oui", "o", "1", "x", "yes", "y", "vrai")


def lire_feuille(chemin):
    """-> (zéros [Pa], paliers [dict], jeux [dict])."""
    zeros, paliers, jeux = [], [], []
    with open(chemin, encoding="utf-8-sig", errors="replace") as fh:
        lignes = [l for l in fh if l.strip() and not l.lstrip().startswith("#")]
    for r in csv.DictReader(lignes, delimiter=";"):
        surplus = r.pop(None, None)                              # un « ; » dans la remarque
        r = {(k or "").strip(): (v or "").strip() for k, v in r.items()}
        if surplus:
            r["remarque"] = " ; ".join([r.get("remarque", "")] + [x.strip() for x in surplus])
        t = r.get("type", "").lower()
        p = _nombre(r.get("p_lue_Pa"))
        if t == "zero" and p is not None:
            zeros.append(p)
        elif t == "palier" and p is not None:
            paliers.append(dict(cycle=int(_nombre(r.get("cycle")) or 1), sens=r.get("sens", "").lower(),
                                p=p, sonne=_oui(r.get("sonne"))))
        elif t == "jeu" and p is not None:
            jeux.append(dict(cycle=r.get("cycle", ""), p=p, fichier=r.get("fichier", ""),
                             t0=_nombre(r.get("t0_s")), t1=_nombre(r.get("t1_s")), remarque=r.get("remarque", "")))
    return zeros, paliers, jeux


def seuils_escalier(paliers, zero=0.0):
    """p_on (montée) et p_off (descente) par cycle : milieu entre le dernier palier qui ne
    sonne pas et le premier qui sonne (et l'inverse en descente). Rend une liste de dicts."""
    out = []
    for c in sorted({p["cycle"] for p in paliers}):
        res = dict(cycle=c, p_on=float("nan"), u_on=float("nan"), p_off=float("nan"), u_off=float("nan"))
        monte = [p for p in paliers if p["cycle"] == c and p["sens"].startswith("mont")]
        desc = [p for p in paliers if p["cycle"] == c and p["sens"].startswith("desc")]
        for i in range(1, len(monte)):
            if not monte[i - 1]["sonne"] and monte[i]["sonne"]:
                a, b = monte[i - 1]["p"] - zero, monte[i]["p"] - zero
                res.update(p_on=(a + b) / 2, u_on=abs(b - a) / 2)
                break
        for i in range(1, len(desc)):
            if desc[i - 1]["sonne"] and not desc[i]["sonne"]:
                a, b = desc[i - 1]["p"] - zero, desc[i]["p"] - zero
                res.update(p_off=(a + b) / 2, u_off=abs(b - a) / 2)
                break
        out.append(res)
    return out


def frequence_jeu(x, fs, t0=None, t1=None):
    """Fréquence de jeu (Hz) et niveau (dB pleine échelle) d'un son tenu : le milieu stable
    (10 % retirés de chaque côté), pic du spectre puis pente de la phase du fondamental."""
    from banc_recherche.coupled_reeds import dominant_frequency
    from banc_recherche.pince import _analytique, filtre_bande
    x = np.asarray(x, float)
    a = int((t0 or 0.0) * fs)
    b = int(t1 * fs) if t1 else x.size
    x = x[a:b] - np.mean(x[a:b])
    n = x.size
    x = x[int(0.1 * n): int(0.9 * n)]
    if x.size < int(0.1 * fs):
        raise ValueError("son trop court (moins de 0,1 s utile)")
    f0 = dominant_frequency(x, fs)
    # le pic le plus fort peut être un harmonique : le fondamental est le plus grave des pics
    # nets (à -30 dB du plus fort au plus) dont le pic fort est un multiple (2 à 6), à 1 % près
    N = 1 << int(np.ceil(np.log2(x.size)) + 2)
    S = np.abs(np.fft.rfft(x * np.hanning(x.size), N))
    fr = np.fft.rfftfreq(N, 1 / fs)
    loc = np.nonzero((S[1:-1] > S[:-2]) & (S[1:-1] >= S[2:]) & (S[1:-1] > 10 ** (-30 / 20) * S.max()))[0] + 1
    for i in loc:
        fl = float(fr[i])
        if fl < 20 or fl >= f0 * 0.99:
            continue
        k = round(f0 / fl)
        if 2 <= k <= 6 and abs(f0 / (k * fl) - 1) < 0.01:
            f0 = fl
            break
    y = filtre_bande(x, fs, f0, max(2.0, 0.03 * f0))
    ph = np.unwrap(np.angle(_analytique(y)))
    t = np.arange(ph.size) / fs
    c = slice(int(0.1 * ph.size), int(0.9 * ph.size))           # bords du filtre retirés
    f = float(np.polyfit(t[c], ph[c], 1)[0] / (2 * np.pi))
    niveau = float(20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-15))
    return f, niveau


def analyser(chemin_feuille):
    from banc_recherche.pince import lire_audio
    zeros, paliers, jeux = lire_feuille(chemin_feuille)
    zero = float(np.mean(zeros)) if zeros else 0.0
    alertes = []
    marches = np.diff(sorted({p["p"] for p in paliers})) if len(paliers) > 1 else np.array([])
    marche = float(np.median(marches)) if marches.size else float("nan")
    if len(zeros) >= 2:
        derive = max(zeros) - min(zeros)
        if math.isfinite(marche) and derive > 0.5 * marche:
            alertes.append(f"le zéro a dérivé de {derive:.1f} Pa pendant la série, plus que la demi-marche "
                           f"({marche / 2:.1f} Pa) : refaire un zéro entre chaque cycle")
    elif not zeros:
        alertes.append("pas de ligne « zero » : les pressions sont prises comme des surpressions")
    cyc = seuils_escalier(paliers, zero)
    on = [c["p_on"] for c in cyc if math.isfinite(c["p_on"])]
    off = [c["p_off"] for c in cyc if math.isfinite(c["p_off"])]
    p_on = float(np.median(on)) if on else float("nan")
    p_off = float(np.median(off)) if off else float("nan")
    base = os.path.dirname(os.path.abspath(chemin_feuille))
    lignes_jeu = []
    for j in jeux:
        ch = j["fichier"] if os.path.isabs(j["fichier"]) else os.path.join(base, j["fichier"])
        try:
            x, fs = lire_audio(ch)
            f, lv = frequence_jeu(x, fs, j["t0"], j["t1"])
        except (OSError, ValueError, RuntimeError) as e:
            alertes.append(f"{j['fichier']} : {e}")
            continue
        lignes_jeu.append(dict(fichier=j["fichier"], p_Pa=j["p"] - zero, f_jeu_Hz=f, niveau_dB=lv,
                               remarque=j["remarque"]))
    lignes_jeu.sort(key=lambda d: d["p_Pa"])
    return dict(zero_Pa=zero, marche_Pa=marche, cycles=cyc, p_on_Pa=p_on, p_off_Pa=p_off,
                rapport_on_off=p_on / p_off if (on and off and p_off > 0) else float("nan"),
                n_cycles=len(on), jeux=lignes_jeu, alertes=alertes)


def pour_recalage(chemin_feuille):
    """Le dictionnaire de `recalage.lire_seuils` : p_on médian, nombre de cycles, et la
    fréquence de jeu du plus bas enregistrement au-dessus du seuil (au plus 1,3 p_on)."""
    r = analyser(chemin_feuille)
    f = [j["f_jeu_Hz"] for j in r["jeux"] if math.isfinite(r["p_on_Pa"]) and r["p_on_Pa"] <= j["p_Pa"] <= 1.3 * r["p_on_Pa"]]
    return dict(p_on_Pa=r["p_on_Pa"], n_cycles=r["n_cycles"], f_jeu_Hz=f[0] if f else float("nan"),
                p_off_Pa=r["p_off_Pa"])


def main(argv=None):
    import argparse
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description="Seuils et fréquence de jeu à la soufflerie (feuille de paliers).")
    ap.add_argument("feuille")
    a = ap.parse_args(argv)
    r = analyser(a.feuille)
    print(f"zéro (pression de la pièce) : {r['zero_Pa']:.1f} Pa ; marche médiane : {r['marche_Pa']:.1f} Pa")
    for c in r["cycles"]:
        print(f"  cycle {c['cycle']} : p_on = {c['p_on']:.1f} ± {c['u_on']:.1f} Pa ; "
              f"p_off = {c['p_off']:.1f} ± {c['u_off']:.1f} Pa")
    print(f"médianes : p_on = {r['p_on_Pa']:.1f} Pa, p_off = {r['p_off_Pa']:.1f} Pa, "
          f"rapport p_on / p_off = {r['rapport_on_off']:.2f} ({r['n_cycles']} cycle(s))")
    for j in r["jeux"]:
        print(f"  {j['fichier']} : {j['p_Pa']:.1f} Pa -> {j['f_jeu_Hz']:.3f} Hz, {j['niveau_dB']:.1f} dB  {j['remarque']}")
    for al in r["alertes"]:
        print("attention :", al)


if __name__ == "__main__":
    main()

"""Bilan d'énergie d'une languette forcée (sortie Elmer `force.dat`).

La languette (coupe 2D, demi-modèle) est imposée à y = A·sin(ω(t − t0)).
Sur les derniers cycles, la force verticale de l'air F(t) (par mètre de
profondeur) se décompose en :

    F = F̄ + F_s·sin + F_c·cos

- travail de l'air par cycle  W = ∮ F·ẏ dt = π·A·F_c   (> 0 : l'air donne) ;
- amortissement de l'air      c_a = −F_c / (A·ω)       (< 0 : anti-amortissement) ;
- raideur apparente de l'air  k_a = −F_s / A           (> 0 : note plus haute ;
  elle contient aussi la masse d'air entraînée, −m_a·ω², indiscernable à une
  seule fréquence).

On compare à la languette d'acier (même coupe, même demi-largeur) :
amortissement de structure c_s = 2ζω·m', raideur k' = m'·ω².

Usage : python3 bilan.py dossier [A f t0 dt]
"""
import math
import sys

import numpy as np

d = sys.argv[1]
A = float(sys.argv[2]) if len(sys.argv) > 2 else 5e-6
f = float(sys.argv[3]) if len(sys.argv) > 3 else 440.0
t0 = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5e-3
dt = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0 / f / 30.0
w = 2 * math.pi * f

names = open(f"{d}/resultats/force.dat.names").read().splitlines()
col = next(i for i, l in enumerate(l for l in names if ':' in l and l.strip()[0].isdigit())
           if 'fluid force 2' in l)
data = np.loadtxt(f"{d}/resultats/force.dat", ndmin=2)
F = data[:, col]
t = dt * np.arange(1, len(F) + 1)
T = 1.0 / f
n_cyc = int((t[-1] - t0) / T)
if n_cyc < 2:
    sys.exit(f"{d} : seulement {n_cyc} cycle(s) calculé(s) — attendre")
m = (t > t[-1] - 2 * T + 1e-12)            # deux derniers cycles
ph = w * (t[m] - t0)
Fm = F[m]
# moindres carrés : F = a + b sin + c cos
M = np.column_stack([np.ones_like(ph), np.sin(ph), np.cos(ph)])
(a, Fs, Fc), *_ = np.linalg.lstsq(M, Fm, rcond=None)
W = math.pi * A * Fc
c_a = -Fc / (A * w)
k_a = -Fs / A

rho_s, larg, ep, zeta = 7800.0, 1.75e-3, 0.3e-3, 0.004      # demi-languette d'acier
m_l = rho_s * larg * ep
c_s = 2 * zeta * w * m_l
k_l = m_l * w * w
print(f"{d:10s} cycles {n_cyc}  F̄ {a:+.4f} N/m  F_sin {Fs:+.3e}  F_cos {Fc:+.3e}")
sens = "l'air DONNE" if W > 0 else "l'air prend"
print(f"           travail de l'air par cycle W = {W:+.3e} J/m  ({sens})")
print(f"           amortissement de l'air c_a = {c_a:+.3e} N·s/m²  |  acier c_s = {c_s:.3e}  → rapport c_a/c_s = {c_a / c_s:+.2f}")
print(f"           raideur apparente k_a = {k_a:+.3e} N/m²  |  acier k' = {k_l:.3e}  → décalage ≈ {600 / math.log(2) * math.log(1 + k_a / k_l):+.1f} ¢")

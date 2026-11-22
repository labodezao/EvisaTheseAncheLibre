# Sensibilité du seuil de démarrage et du plaquage aux réglages (22/11/2026).
# Lame uniforme de 175 Hz en repère, sous 336 cm3 ; K0 = 4,5 puis 1,5. Lancer depuis research/.
import sys, dataclasses
sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), ".."))
from banc_recherche.upstream_reed import UpstreamReed, Blade, CENTRAL_LIFT_M, CENTRAL_PLATE_M, CENTRAL_CLEARANCE_M
from banc_recherche.coupled_reeds import ReedSetting
b0 = Blade.for_note(174.6)
print("lame", round(b0.f0_hz,1), "Hz, ep", b0.thickness_m)
def seuil(blade=b0, lift=CENTRAL_LIFT_M, plate=CENTRAL_PLATE_M, cl=CENTRAL_CLEARANCE_M, V=336e-6, k0=4.5):
    s = ReedSetting(lift_m=lift, plate_m=plate, tongue_m=blade.thickness_m, clearance_m=cl)
    m = UpstreamReed(blade, s, upstream_volume_m3=V, gap_inertia="ricot", k0=k0)
    c = m.instability_band(20, 6000, n_scan=50, n_bisect=25)
    d=[x.p0_pa for x in c if x.kind=='demarrage']; f=[x.p0_pa for x in c if x.kind=='fin']
    return (round(d[0]) if d else None, round(f[0]) if f else None)
cases = [("référence",{})]
cases += [(f"jeu {c*1e6:.0f} µm",{"cl":c}) for c in (15e-6,60e-6)]
cases += [(f"levée {l*1e3:.1f} mm",{"lift":l}) for l in (0.2e-3,0.6e-3,0.8e-3)]
cases += [(f"plaque {p*1e3:.1f} mm",{"plate":p}) for p in (0.6e-3,1.5e-3)]
cases += [(f"amortissement x{r}",{"blade":dataclasses.replace(b0, zeta=b0.zeta*r)}) for r in (0.5,2)]
cases += [(f"volume {v*1e6:.0f} cm3",{"V":v}) for v in (121e-6,30e-6)]
for k0 in (4.5, 1.5):
    print("K0 =", k0)
    for n,kw in cases:
        try: r=seuil(k0=k0, **kw); print(f'  {n:22s} demarre {r[0]} Pa, plaque {r[1]} Pa', flush=True)
        except Exception as e: print(f"  {n:22s} erreur {e}")

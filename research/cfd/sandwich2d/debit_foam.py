"""Débit sortant (patch aval) dans chaque répertoire de temps d'OpenFOAM."""
import os, re, sys
os.chdir(sys.argv[1])
dz = 1e-4
for d in sorted((x for x in os.listdir('.') if re.fullmatch(r'\d+', x)), key=int):
    if not os.path.exists(os.path.join(d, 'phi')): continue
    s = open(os.path.join(d, 'phi')).read()
    blk = s[s.index('aval'):]
    blk = blk[:blk.index('}')]
    m = re.search(r'nonuniform List<scalar>\s*(\d+)\s*\(([^)]*)\)', blk, re.S)
    q = sum(float(v) for v in m.group(2).split()) if m else float(re.search(r'uniform\s+([-\d.e+]+)', blk).group(1))
    print(f"itération {d:>5s}  débit par m de profondeur {-q / dz:.4e} m²/s")

"""Géométrie 2D (coupe à travers la largeur de la languette) d'une anche
dans sa pile de supports, pour Elmer et OpenFOAM. Demi-modèle : symétrie
en x = 0 (languette centrée en largeur).

Cotes (m) — celles du modèle 1D (slot_stack), à remplacer par les tiennes :
languette 3,5 mm × 0,3 mm, jeu 30 µm, supports h_amont / h_aval.
L'air va de haut (y > 0) en bas ; la pile occupe −D ≤ y ≤ 0.

Usage : python3 geometrie.py h_amont_mm h_aval_mm [dx_jeu_µm] > anche.geo
"""
import sys

# python3 geometrie.py sandwich h_amont_mm h_aval_mm
# python3 geometrie.py accordeon plaque_mm levee_mm      (languette au-dessus, côté amont)
a, t, c = 1.75e-3, 0.3e-3, 30e-6          # demi-largeur, épaisseur, jeu
dxg = 6e-6
if len(sys.argv) > 1 and sys.argv[1] == 'accordeon':
    D = float(sys.argv[2]) * 1e-3
    lift = float(sys.argv[3]) * 1e-3
    yb, yt = lift, lift + t                # languette au-dessus de la plaque
    h_up, h_dn = 0.0, D
else:
    args = sys.argv[2:] if len(sys.argv) > 1 and sys.argv[1] == 'sandwich' else sys.argv[1:]
    h_up = float(args[0]) * 1e-3 if len(args) > 0 else 0.9e-3
    h_dn = float(args[1]) * 1e-3 if len(args) > 1 else 0.9e-3
    D = h_up + t + h_dn
    yt, yb = -h_up, -h_up - t              # faces de la languette
s = a + c                                  # demi-largeur de la fente
X, H = 6e-3, 5e-3                          # réservoirs amont et aval
big = 0.25e-3

print(f"""// anche : pile D={D*1e3:.3f} mm, languette y ∈ [{yb*1e3:.3f}, {yt*1e3:.3f}] mm
SetFactory("OpenCASCADE");
Rectangle(1) = {{0, 0, 0, {X}, {H}}};              // réservoir amont
Rectangle(2) = {{0, {-D}, 0, {s}, {D}}};           // fente
Rectangle(3) = {{0, {-D - H}, 0, {X}, {H}}};       // réservoir aval
Rectangle(4) = {{0, {yb}, 0, {a}, {t}}};           // languette
f() = BooleanUnion{{ Surface{{1}}; Delete; }}{{ Surface{{2}}; Surface{{3}}; Delete; }};
g() = BooleanDifference{{ Surface{{f()}}; Delete; }}{{ Surface{{4}}; Delete; }};

// finesse : 6 µm dans le jeu, grossier au loin
Field[1] = Box; Field[1].VIn = {dxg}; Field[1].VOut = {big};
Field[1].XMin = {a - 2*c}; Field[1].XMax = {s + 2*c}; Field[1].YMin = {min(-D, yb) - 2*c}; Field[1].YMax = {max(0, yt) + 2*c};
Field[1].Thickness = {0.6e-3};
Field[2] = Box; Field[2].VIn = {4*dxg}; Field[2].VOut = {big};
Field[2].XMin = 0; Field[2].XMax = {s + 0.4e-3}; Field[2].YMin = {min(-D, yb) - 0.6e-3}; Field[2].YMax = {max(0, yt) + 0.6e-3};
Field[2].Thickness = {1.5e-3};
Field[3] = Min; Field[3].FieldsList = {{1, 2}};
Background Field = 3;
Mesh.MeshSizeExtendFromBoundary = 0; Mesh.MeshSizeFromPoints = 0; Mesh.MeshSizeFromCurvature = 0;

// frontières repérées par leur position
eps = 1e-7;
Physical Surface("air") = {{g()}};
Physical Curve("amont") = Curve In BoundingBox{{-eps, {H}-eps, -eps, {X}+eps, {H}+eps, eps}};
Physical Curve("aval") = Curve In BoundingBox{{-eps, {-D-H}-eps, -eps, {X}+eps, {-D-H}+eps, eps}};
Physical Curve("symetrie") = Curve In BoundingBox{{-eps, {-D-H}-eps, -eps, eps, {H}+eps, eps}};
Physical Curve("languette") = Curve In BoundingBox{{-eps, {yb}-eps, -eps, {a}+eps, {yt}+eps, eps}};
paroi() = Curve In BoundingBox{{-eps, {-D-H}-eps, -eps, {X}+eps, {H}+eps, eps}};
paroi() -= Curve In BoundingBox{{-eps, {H}-eps, -eps, {X}+eps, {H}+eps, eps}};
paroi() -= Curve In BoundingBox{{-eps, {-D-H}-eps, -eps, {X}+eps, {-D-H}+eps, eps}};
paroi() -= Curve In BoundingBox{{-eps, {-D-H}-eps, -eps, eps, {H}+eps, eps}};
paroi() -= Curve In BoundingBox{{-eps, {yb}-eps, -eps, {a}+eps, {yt}+eps, eps}};
Physical Curve("paroi") = {{paroi()}};
""")

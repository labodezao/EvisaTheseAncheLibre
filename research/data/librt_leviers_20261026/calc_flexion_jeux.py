# -*- coding: utf-8 -*-
"""LibRT idee 1 : flexion des tiges, jeux, frottement, contraintes (calcul seul)."""
import math
E = 72000.0           # MPa (N/mm2)
RP02 = 275.0          # MPa, 2017A-T4 mini (ordre de grandeur)
T, W = 2.0, 7.0
I_PLAT = W*T**3/12.0; V_PLAT = T/2
I_CHANT = T*W**3/12.0
AXE = {'A': 128.24, 'B': 126.24}
TIGES = {  # nom: (pied X, plis [(h, x)])
 'A1': (41.3, [(9.6,49.1),(-9.6,93.4)]),
 'A2': (28.3, [(28.4,35.7),(-20.3,40.3),(-8.1,93.4)]),
 'A3': (15.4, [(28.4,30.5),(-20.4,39.7),(-8.0,93.4)]),
 'B1': (80.3, []),
 'B2': (67.3, [(35.5,76.5),(-35.5,80.0)]),
 'B3': (54.6, [(35.5,73.0),(-35.5,80.0)]),
}
L_ATT = math.hypot(13.5, 32.0)   # axe -> attache biellette (valeur B, supposee pour A aussi)
COURSE = 5.0
LP = 2.0                          # longueur de portee du palier (mm), = epaisseur tole
FORCES = [1.0, 1.5, 2.5]
def fle(F, L, I): return F*L**3/(3*E*I)

print("Hypotheses: porte-a-faux encastre au pivot, charge au pied (bouton = pied, decalage 0);")
print("plis = marches verticales: L_dev = L_x + somme|h| (borne haute, tige droite developpee);")
print("L_x seul = borne basse. attache a %.1f mm de l'axe (A et B). I plat=%.3f mm4, chant=%.3f mm4." % (L_ATT, I_PLAT, I_CHANT))
print("\n== 1. Bras et fleches (mm) ==")
print("tige  Lx    Ldev  | f1,5N plat Lx/Ldev | f chant(Ldev) | f1N  f2,5N (Ldev) | %course perdue 1,5N Lx/Ldev | rapport Lb/Latt")
res = {}
for n,(pied,plis) in TIGES.items():
    lx = AXE[n[0]]-pied; ld = lx+sum(abs(h) for h,_ in plis)
    r = {}
    r['lx']=lx; r['ld']=ld
    f15x=fle(1.5,lx,I_PLAT); f15d=fle(1.5,ld,I_PLAT)
    r.update(f15x=f15x,f15d=f15d)
    print("%-4s %5.1f %5.1f | %6.2f / %6.2f | %7.3f | %5.2f %6.2f | %5.1f%% / %5.1f%% | %.2f" % (
      n,lx,ld,f15x,f15d,fle(1.5,ld,I_CHANT),fle(1,ld,I_PLAT),fle(2.5,ld,I_PLAT),
      100*f15x/COURSE,100*f15d/COURSE,lx/L_ATT))
    res[n]=r

print("\n== 2. Jeux ==  (tilt = 2*c/Lp, Lp=%.0f mm ; en bout = tilt x bras)" % LP)
print("tige | bascule pied (mm) pour c=0,02/0,05/0,1 | bascule attache c=0,05 | goupille jeu 0,05/0,1 -> perte course bouton (mm)")
for n,r in res.items():
    lx=r['lx']
    b=[2*c/LP*lx for c in (0.02,0.05,0.1)]
    att=2*0.05/LP*L_ATT
    g=[j*lx/L_ATT for j in (0.05,0.1)]
    print("%-4s | %5.2f %5.2f %5.2f | %5.2f | %5.3f %5.3f" % (n,*b,att,*g))
print("(goupille D2,2 dans trou 2,2 a 2,3 : jeu diam. 0 a 0,1 ; perte = jeu x Lb/Latt)")

print("\n== 3. Frottement ==  T = mu*N*r ; g au bouton = T/Lb/9,81*1000")
print("tige | D3 (r1,5) mu0,15 N2 -> mu0,2 N4 (g) | si glisse sur D6 (r3) mu0,2 N4 (g)")
for n,r in res.items():
    lx=r['lx']
    lo=0.15*2*1.5/lx/9.81*1000; hi=0.2*4*1.5/lx/9.81*1000; hi6=0.2*4*3.0/lx/9.81*1000
    r['g']=(lo,hi)
    print("%-4s | %4.1f -> %4.1f g | %4.1f g" % (n,lo,hi,hi6))

print("\n== 4. Contraintes (section nette, flexion plat, v = 1 mm) ==")
for d in (6.0,3.0,2.2):
    net=W-d
    print("trou D%.1f : ligament %.2f mm de chaque cote, I_net=%.3f mm4" % (d,net/2,net*T**3/12))
print("tige | sigma pivot D6 (2,5N) | D3 | Kt~3 sur D6 | ratio Rp0,2 (D6)")
for n,r in res.items():
    M=2.5*r['lx']
    s6=M*V_PLAT/((W-6)*T**3/12); s3=M*V_PLAT/((W-3)*T**3/12)
    print("%-4s | %6.0f MPa | %5.0f MPa | %6.0f MPa | %.2f" % (n,s6,s3,3*s6,s6/RP02))
print("attache (effort biellette F*Lb/Latt, section a mi-trou, bras d/2) + matage:")
for n,r in res.items():
    Fa=2.5*r['lx']/L_ATT
    out=[]
    for d in (3.0,2.2):
        s=Fa*(d/2)*V_PLAT/((W-d)*T**3/12); mat=Fa/(d*T)
        out.append("D%.1f: F=%.1f N flex %.0f MPa matage %.0f MPa"%(d,Fa,s,mat))
    print("%-4s %s" % (n," | ".join(out)))

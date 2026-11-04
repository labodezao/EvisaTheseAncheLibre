import numpy as np
B = r"D:\GoogleDrive\python\Mesure anches"
np.set_printoptions(precision=3, suppress=True, linewidth=220)
names=["d_Mesures_Press","d_MesuresTemperature","d_Mesures_Debit"]
arrs=[np.load(B+rf"\data_d1_L\{n}.npy", mmap_mode="r") for n in names]
def seg(row):
    d=np.diff(row); tl=np.isclose(d,0.01,atol=0.0025)
    # runs
    out=[];start=0
    for i in range(1,len(row)):
        if (tl[i-1] if i-1<len(tl) else False)!=(tl[i-2] if i>=2 else tl[0]): pass
    idx=np.where(np.diff(tl.astype(int))!=0)[0]+1
    return tl.mean(), idx[:6]
for name,a in zip(names,arrs):
    for cell in [(0,3,4,4),(0,0,0,0),(1,7,7,7)]:
        x=np.asarray(a[cell])
        print(name, cell, [ (round(seg(x[r])[0],2), seg(x[r])[1].tolist()) for r in range(2)], "row0 ends", x[0,-3:], "row1 head", x[1,:2])

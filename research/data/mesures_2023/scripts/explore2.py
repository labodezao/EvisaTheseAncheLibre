import numpy as np, glob, os, re, h5py
B = r"D:\GoogleDrive\python\Mesure anches"
np.set_printoptions(precision=3, suppress=True, linewidth=220)
for d in ["data","data_D#0_1_L_2v"]:
    fs = glob.glob(os.path.join(B,d,"*.wav"))
    M = np.zeros((2,8,8,8),int)
    for f in fs:
        k=list(map(int,re.findall(r"\d+",os.path.basename(f)))); M[tuple(k)]=1
    print(d); 
    for p in range(2): print(" PPos",p,"count per Sec x PPlus:\n", M[p].sum(-1))
P = np.load(B+r"\data_d1_L\d_Mesures_Press.npy", mmap_mode="r")
x=np.asarray(P[0,3,4,4]); print("d1L P cell rows:\n", x[:, :12], "\n", x[:, 140:160], "\n", x[:, -12:])
Q = np.load(B+r"\data_d1_L\d_Mesures_Debit.npy", mmap_mode="r"); print("Q", np.asarray(Q[0,3,4,4])[:, :8], np.asarray(Q[0,3,4,4])[:, 145:152])
E = np.load(B+r"\data - e1\d_Mesures_Press_Acoustique.npy", mmap_mode="r")
EA = np.load(B+r"\data - e1\d_Mesures_Accelerations.npy", mmap_mode="r")
print("e1 corr acou/acc", np.corrcoef(E[0,2,2,2,1], EA[0,2,2,2,1])[0,1], np.abs(E[0,2,2,2,1]-EA[0,2,2,2,1]).max())
EP = np.load(B+r"\data - e1\d_Mesures_Press.npy", mmap_mode="r")
print("e1 press unique values over whole array", np.unique(np.asarray(EP[:,:,:,:,1,:])).size, np.unique(np.asarray(EP[:,:,:,:,1,:]))[:10])
EQ = np.load(B+r"\data - e1\d_Mesures_Debit.npy", mmap_mode="r"); print("e1 debit uniq", np.unique(np.asarray(EQ[:,:,:,:,1,:])).size, np.asarray(EQ[0,2,2,2,1,:6]))
ET = np.load(B+r"\data - e1\d_MesuresTemperature.npy", mmap_mode="r"); print("e1 T", np.asarray(ET[0,2,2,2,1,:6]))
# d1L vs pressure step: mean pressure per PPlus
with h5py.File(B+r"\data\Measure_datasetnSec8nPress8nClap8.hdf5","r") as f:
    p=f["Mesures_Press"]
    x=p[0,3,6,4]; print("Sep23 cell rows", x[:, :6], x[:, 290:310])
    for pp in range(8):
        y=p[1,3,pp,4]; n=(y[0]>0).sum(); print(" PPos1 pplus",pp,"n",n,"P mean last1s %.1f"%y[1,n-100:n].mean(), " PPos0 %.1f"%p[0,3,pp,4,1,n-100:n].mean(), "min/max", y[1,:n].min(), y[1,:n].max())

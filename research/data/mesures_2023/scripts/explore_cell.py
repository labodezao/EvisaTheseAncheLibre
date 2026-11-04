import numpy as np, h5py, os
from scipy.io import wavfile
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
B = r"D:\GoogleDrive\python\Mesure anches"
OUT = r"J:\claude\business-os\journal\recherche\figures"
np.set_printoptions(precision=3, suppress=True, linewidth=200)
# campaign d1_L npy pneumatics
P = np.load(B+r"\data_d1_L\d_Mesures_Press.npy", mmap_mode="r")
Q = np.load(B+r"\data_d1_L\d_Mesures_Debit.npy", mmap_mode="r")
T = np.load(B+r"\data_d1_L\d_MesuresTemperature.npy", mmap_mode="r")
S = np.load(B+r"\data_d1_L\d_Calculs_Surf.npy", mmap_mode="r")
print("d1L surf", S[0,:,0,0,:,0])
print("d1L press PPos0 sec3 pplus4 clap4", P[0,3,4,4,0,:5], P[0,3,4,4,1,:5], P[0,3,4,4,1,-5:])
print("d1L press PPos1 sec3 pplus4 clap4", P[1,3,4,4,1,:5])
A = np.load(B+r"\data\d_Mesures_Press_Acoustique.npy", mmap_mode="r")
sr, w = wavfile.read(B+r"\data_d1_L\PPos0Sec3PPlus4iClap4.wav")
a = np.asarray(A[0,3,4,4,1,:]); t=np.asarray(A[0,3,4,4,0,:5])
print("npy acou vs d1L wav: equal?", np.allclose(a[:len(w)], w[:len(a)]), "corr", np.corrcoef(a[:len(w)], w[:len(a)])[0,1], "time row", t)
sr2, w2 = wavfile.read(B+r"\data\PPos0Sec3PPlus4iClap4.wav")
print("npy acou vs data wav corr", np.corrcoef(a[:len(w2)], w2[:len(a)])[0,1])
sr3, w3 = wavfile.read(B+r"\data_D#0_1_L_2v\PPos0Sec3PPlus4iClap4.wav")
print("npy acou vs D#0 wav corr", np.corrcoef(a[:len(w3)], w3[:len(a)])[0,1])
# e1
E = np.load(B+r"\data - e1\d_Mesures_Press_Acoustique.npy", mmap_mode="r")
EA = np.load(B+r"\data - e1\d_Mesures_Accelerations.npy", mmap_mode="r")
EP = np.load(B+r"\data - e1\d_Mesures_Press.npy", mmap_mode="r")
print("e1 acou row0", E[0,2,2,2,0,:4], E[0,2,2,2,0,-2:], "row1 std", E[0,2,2,2,1].std(), "acc std", EA[0,2,2,2,1].std(), "acc row0", EA[0,2,2,2,0,:3])
print("e1 press", EP[0,2,2,2,0,:4], EP[0,2,2,2,1,:6], EP[0,2,2,2,1,-3:])
filled = [(p,s,pp,c) for p in range(2) for s in range(5) for pp in range(5) for c in range(5) if np.any(E[p,s,pp,c,1,:1000]!=0)]
print("e1 acoustic filled", len(filled))
with h5py.File(B+r"\data - e1\PPos0Sec2PPlus2.hdf5","r") as f:
    ts=f["med1/timeSignal"][:]; print("e1 h5 ts std", ts.std(0), "corr with npy clap4", [np.corrcoef(ts[:,0], E[0,2,2,c,1])[0,1] for c in range(5)])
    print(dict(f["med1"].attrs) if hasattr(f["med1"],"attrs") else "")
    def v(n,o): print("   ", n, dict(o.attrs))
    f.visititems(v)
# plot one cell per campaign: pressure, flow, envelope
fig, ax = plt.subplots(4,1, figsize=(9,10), sharex=True)
with h5py.File(B+r"\data\Measure_datasetnSec8nPress8nClap8.hdf5","r") as f:
    for c in [0,4,7]:
        p=f["Mesures_Press"][0,3,6,c]; q=f["Mesures_Debit"][0,3,6,c]
        n=(p[0]>0).sum()+1
        ax[0].plot(p[0,:n],p[1,:n],label=f"clapet {c}"); ax[1].plot(q[0,:n],q[1,:n])
        sr,w=wavfile.read(B+rf"\data\PPos0Sec3PPlus6iClap{c}.wav"); tt=np.arange(len(w))/sr
        ax[2].plot(tt, w/2**31, lw=0.3)
    ax[0].legend(); ax[0].set_ylabel("Mesures_Press (BMP280)"); ax[1].set_ylabel("Débit SFM3000"); ax[2].set_ylabel("micro (pleine échelle)")
    T=f["MesuresTemperature"][0,3,6,4]; n=(T[0]>0).sum()+1; ax[3].plot(T[0,:n],T[1,:n]); ax[3].set_ylabel("T (°C)")
ax[3].set_xlabel("temps (s)")
fig.tight_layout(); fig.savefig(OUT+r"\explore_cellule_sep2023.png", dpi=110)

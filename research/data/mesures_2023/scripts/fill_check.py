import h5py, numpy as np
B = r"D:\GoogleDrive\python\Mesure anches"
np.set_printoptions(precision=3, suppress=True, linewidth=200)
for fn in [B+r"\data\Measure_datasetnSec8nPress8nClap8.hdf5", B+r"\data_D#0_1_L_2v\Measure_datasetnSec8nPress8nClap8.hdf5"]:
    print("#####", fn)
    with h5py.File(fn, "r") as f:
        for k in ["Mesures_Press","MesuresTemperature","Mesures_Debit","Mesures_Accelerations","Mesures_Press_Acoustique","Tresp","Freq","Calculs_Surf","Mesures_Press_Pos","Pitches","Intensities","Results"]:
            d = f[k]
            if d.ndim>=4:
                a = np.asarray(d[...,:50]) if d.ndim>5 else np.asarray(d)
                filled = np.array([[np.any(a[p,s]!=0) for s in range(8)] for p in range(2)])
                # count per PPos of filled (S,P,C) cells
                cnt=[int(sum(np.any(a[p,s,pp,c]!=0) for s in range(8) for pp in range(8) for c in range(8))) for p in range(2)]
                print(k, "cells filled per PPos:", cnt)
            else:
                a=np.asarray(d); print(k, a.shape, "nonzero rows", int((np.abs(a).sum(1)>0).sum()))
        # sample values
        mp = f["Mesures_Press"]
        print("Press sample [0,0,0,0,:,:5]\n", mp[0,0,0,0,:,:5], "\n row1 last", mp[0,0,0,0,1,-5:])
        for pp in range(8):
            x = mp[0,3,pp,4,1,:]; print(" P_plus",pp,"press row1 mean/std", x.mean(), x.std(), " row0", mp[0,3,pp,4,0,:3])
        print("Debit sample", f["Mesures_Debit"][0,3,4,4,:,:5])
        print("Temp sample", f["MesuresTemperature"][0,3,4,4,:,:5])
        print("Accel sample", f["Mesures_Accelerations"][0,3,4,4,:,:5])
        print("Freq [0,3,4,:]", f["Freq"][0,3,4,:])
        print("Tresp [0,3,4,:]", f["Tresp"][0,3,4,:])
        print("Surf", np.asarray(f["Calculs_Surf"])[0,:,0,0].ravel()[:20])
        ac = f["Mesures_Press_Acoustique"][0,3,4,4]
        print("acou t", ac[0,:3], ac[0,-2:], " sig stats", ac[1].min(), ac[1].max(), ac[1].std())
        r = f["Results"][:]; print("Results first cols", r[:, :6])

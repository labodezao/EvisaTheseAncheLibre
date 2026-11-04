import numpy as np, glob, os
from scipy.io import wavfile
B = r"D:\GoogleDrive\python\Mesure anches"
for d in ["data","data_D#0_1_L_2v","data_d1_L"]:
    fs = sorted(glob.glob(os.path.join(B,d,"*.wav")))
    print("==", d, len(fs))
    for fn in [fs[0], fs[len(fs)//2], fs[-1]]:
        sr, x = wavfile.read(fn)
        x = x.astype(np.float64)
        print(os.path.basename(fn), sr, x.shape, x.dtype, "min %.3g max %.3g std %.3g"%(x.min(), x.max(), x.std()), "frac|x|<1e8: %.2f"%np.mean(np.abs(x)<1e8))
        h,_ = np.histogram(x, bins=12); print("  hist", h)
for fn in glob.glob(B+r"\*.wav"):
    sr,x=wavfile.read(fn); print(os.path.basename(fn), sr, x.shape, x.dtype)
# combos present in data_d1_L and D#0
import re
for d in ["data","data_D#0_1_L_2v","data_d1_L"]:
    fs = glob.glob(os.path.join(B,d,"*.wav"))
    keys=[tuple(map(int,re.findall(r"\d+",os.path.basename(f)))) for f in fs]
    k=np.array(keys); print(d, "PPos values", np.unique(k[:,0]), "Sec", np.unique(k[:,1]), "PPlus", np.unique(k[:,2]), "Clap", np.unique(k[:,3]))
    for p in np.unique(k[:,0]): print("  PPos",p,"n",(k[:,0]==p).sum())

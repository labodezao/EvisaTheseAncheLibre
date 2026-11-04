import numpy as np
from scipy.io import wavfile
from scipy.signal import find_peaks
B = r"D:\GoogleDrive\python\Mesure anches"
E = np.load(B+r"\data - e1\d_Mesures_Press_Acoustique.npy", mmap_mode="r")
def peaks(x, sr, lab):
    x = x - x.mean(); n=len(x)
    X = np.abs(np.fft.rfft(x*np.hanning(n), 8*n)); f=np.fft.rfftfreq(8*n,1/sr)
    m = f<3000; X=X[m]; f=f[m]
    pk,_ = find_peaks(X, height=X.max()*0.05, distance=int(10/(f[1]-f[0])))
    top = pk[np.argsort(X[pk])[::-1][:8]]
    print(lab, "rms %.4f"%x.std(), "peaks Hz:", np.round(np.sort(f[top]),1))
for d,cells in [("data_d1_L",["PPos0Sec3PPlus4iClap4","PPos0Sec7PPlus7iClap7","PPos0Sec0PPlus0iClap4"]),("data_D#0_1_L_2v",["PPos0Sec3PPlus4iClap4","PPos0Sec7PPlus7iClap7"]),("data",["PPos0Sec3PPlus4iClap4","PPos1Sec7PPlus7iClap7","PPos0Sec0PPlus0iClap4"])]:
    for c in cells:
        sr,w = wavfile.read(rf"{B}\{d}\{c}.wav"); w=w/2**31
        peaks(w[int(1.8*sr):], sr, d+" "+c+" tail")
        peaks(w[:int(0.4*sr)], sr, d+" "+c+" head")
for cell in [(0,2,2,2),(0,4,4,4),(1,0,0,0)]:
    x=np.asarray(E[cell+(1,)]); peaks(x[48000:],48000,"e1 "+str(cell)); peaks(x[:15000],48000,"e1 head")

import h5py, numpy as np, glob, os, sys
B = r"D:\GoogleDrive\python\Mesure anches"
def show(fn):
    print("#####", fn, os.path.getsize(fn))
    with h5py.File(fn, "r") as f:
        def v(name, obj):
            if isinstance(obj, h5py.Dataset):
                print(" ", name, obj.shape, obj.dtype, dict(obj.attrs))
        f.visititems(v)
        for k in ("Measure_params", "Shut_params"):
            if k in f: print(" ", k, f[k][:])
for fn in [B+r"\data\Measure_datasetnSec8nPress8nClap8.hdf5", B+r"\data_D#0_1_L_2v\Measure_datasetnSec8nPress8nClap8.hdf5", B+r"\data - e1\PPos0Sec0PPlus0.hdf5"]:
    show(fn)
for fn in glob.glob(B+r"\*\*.npy"):
    try:
        a = np.load(fn, mmap_mode="r", allow_pickle=False)
        print(os.path.relpath(fn,B), a.shape, a.dtype)
    except Exception as e:
        a = np.load(fn, allow_pickle=True); print(os.path.relpath(fn,B), "pickle", a)

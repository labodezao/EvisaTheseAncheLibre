import parselmouth
from parselmouth.praat import call
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.pylab as plt
import numpy as np
import os,h5py
import sys,glob
import scipy.signal as signal
import statistics



path = 'data_D#0_1_L_2v/'
dir = os.path.dirname(path)
print(os.path.isdir(path))

hd5_files=glob.glob(path+'*.hdf5')
wav_files=glob.glob(path+'*.wav')


sns.set() # Use seaborn's default style to make attractive graphs

# Plot nice figures using Python's "standard" matplotlib library


#%% This function measures formants using Formant Position formula

sound =  parselmouth.Sound(str(wav_files[1])) # read the sound
f0min= 40
f0max= 500
pitch = call(sound, "To Pitch (cc)", 0, f0min, 15, 'no', 0.03, 0.45, 0.01, 0.35, 0.14, f0max)
pointProcess = call(sound, "To PointProcess (periodic, cc)", f0min, f0max)

formants = call(sound, "To Formant (burg)", 0.0025, 5, 5000, 0.025, 50)
numPoints = call(pointProcess, "Get number of points")

f1_list = []
f2_list = []
f3_list = []
f4_list = []
t_list = []

# Measure formants only at glottal pulses
for point in range(0, numPoints):
	point += 1
	t = call(pointProcess, "Get time from index", point)
	f1 = call(formants, "Get value at time", 1, t, 'Hertz', 'Linear')
	f2 = call(formants, "Get value at time", 2, t, 'Hertz', 'Linear')
	f3 = call(formants, "Get value at time", 3, t, 'Hertz', 'Linear')
	f4 = call(formants, "Get value at time", 4, t, 'Hertz', 'Linear')
	t_list.append(t)
	f1_list.append(f1)
	f2_list.append(f2)
	f3_list.append(f3)
	f4_list.append(f4)


# f1_list = [f1 for f1 in f1_list if str(f1) != 'nan']
# f2_list = [f2 for f2 in f2_list if str(f2) != 'nan']
# f3_list = [f3 for f3 in f3_list if str(f3) != 'nan']
# f4_list = [f4 for f4 in f4_list if str(f4) != 'nan']

# calculate mean formants across pulses
f1_mean = statistics.mean(f1_list)
f2_mean = statistics.mean(f2_list)
f3_mean = statistics.mean(f3_list)
f4_mean = statistics.mean(f4_list)

# calculate median formants across pulses, this is what is used in all subsequent calcualtions
# you can use mean if you want, just edit the code in the boxes below to replace median with mean
f1_median = statistics.median(f1_list)
f2_median = statistics.median(f2_list)
f3_median = statistics.median(f3_list)
f4_median = statistics.median(f4_list)


print( f1_mean, f2_mean, f3_mean, f4_mean, f1_median, f2_median, f3_median, f4_median)
plt.plot(t_list,f1_list)
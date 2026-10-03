import parselmouth
from parselmouth.praat import call
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import host_subplot
from mpl_toolkits import axisartist
import seaborn as sns
import numpy as np
import os,h5py
import sys,glob
from scipy import signal, ndimage
from scipy.signal import butter,filtfilt
import statistics
import emd


plt.close("all")
path = 'data_d1_L/'
dir = os.path.dirname(path)
print(os.path.isdir(path))

hd5_files=glob.glob(path+'*.hdf5')
wav_files=glob.glob(path+'*.wav')




makeGraphs=True


sns.set() # Use seaborn's default style to make attractive graphs

# Plot nice figures using Python's "standard" matplotlib library
sound = parselmouth.Sound(str(wav_files[10]))

soundTime , soundData= sound.xs(),sound.values.T.flatten()


duration    = call(sound, "Get total duration") # Duration
samplerate  = call(sound, "Get sampling frequency") #Sampling freq
intensity   = sound.to_intensity(time_step=1/samplerate)
IntensTiler = call(intensity, "Down to IntensityTier") # Duration
Amplitude   = call(IntensTiler, "To AmplitudeTier") # DurationTo AmplitudeTier
TabReal     = call(Amplitude, "Down to TableOfReal") # DurationTo AmplitudeTier
Mat         = call(TabReal, "To Matrix") # To Matrix
TMatrix     = call(Mat, "Transpose") # To Matrix
datas       = call(TMatrix, "To Sound (slice)", 2) # To MatrixTo Sound (slice): 2
scaled      = call(datas, "Scale times to", 0,duration) # To MatrixTo Sound (slice): 2
raw_env     = call(datas, "Resample",samplerate, 5)

Env         = call(raw_env, "Filter (pass Hann band)", 0, 60, 5)
#>> To express the classical envelope in dB instead of voltage:
Env_data=Env.values.T.flatten()
Env_time=Env.xs()
IntData = intensity.values.T.flatten()
IntTime = intensity.xs()

#%% formants

f0min= 40
f0max= 2000
pitch = call(sound, "To Pitch", 1/20000, f0min, f0max)
pitch_values = pitch.selected_array['frequency']
diff_pich = np.diff(pitch_values)
pitch_values[pitch_values==0] = np.nan
pointProcess = call(sound, "To PointProcess (periodic, cc)", 20, 20000)
PitchTime = pitch.xs()
formants = call(sound, "To Formant (burg)", 0.0001, 5, f0max, 0.03, 12)
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


meanF0 = call(pitch, "Get mean", 0, 0, "Hertz") # get mean pitch
stdevF0 = call(pitch, "Get standard deviation", 0 ,0, "Hertz") # get standard deviation
harmonicity = call(sound, "To Harmonicity (cc)", 0.01, f0min, 0.1, 1.0)
hnr = call(harmonicity, "Get mean", 0, 0)


#%% Compute peaks and Tresp
peaks_index, _ = signal.find_peaks(Env_data, height=0.90*max(abs(Env_data[-int(len(Env_data[:])/10):])))
t_zero_idx=peaks_index[0]
t_zero = Env_time[t_zero_idx]


partTime= Env_time[t_zero_idx:] - Env_time[t_zero_idx]*np.ones(len(Env_time[t_zero_idx:]))
IntPartTime = IntTime[t_zero_idx:] - IntTime[t_zero_idx]*np.ones(len(IntTime[t_zero_idx:]))

tpartlist = t_list - IntTime[t_zero_idx]*np.ones(len(t_list))

Tresp=Env_time[peaks_index[1]]-t_zero

meanFund = pitch_values[np.argwhere(PitchTime >Tresp)].mean()
f1_mean = statistics.mean(f1_list)
f2_mean = statistics.mean(f2_list)
f3_mean = statistics.mean(f3_list)
f4_mean = statistics.mean(f4_list)

if makeGraphs :
	#%% Plots enveloppes
	plt.figure(figsize=(8, 10))
	host= host_subplot(211,axes_class=axisartist.Axes)

	plt.subplots_adjust(right=0.75)
	par11 = host.twinx()

	#par11.axis["right"] = host.new_fixed_axis(loc="right", offset=(60, 0))
	host.set_xlabel("Temps [s]")
	host.set_ylabel("Amplitude [Pa]")  # Le signal sonore et son enveloppe
	par11.set_ylabel("Intensity []", color ="g") # Intensité du signal


	#peaks
	host.plot(Env_time[peaks_index[0:2]] - t_zero*np.ones(len(Env_time[peaks_index[0:2]])), Env_data[peaks_index[0:2]]/max(abs(Env_data)), ".",color = "r",markersize=2)


	#plot a line with text
	host.axvline(x = Env_time[0], color = 'r', label = 'axvline - full height')
	host.axvline(x = Env_time[peaks_index[1]]-t_zero, color = 'r', label = 'axvline - full height')
	if len(peaks_index) >1:
		host.text(Env_time[peaks_index[1]-t_zero_idx], 0.95, "tresp = "+ str(format(Tresp*1000,".2f")+" ms, Intensity = "+str(format(IntData[peaks_index[1]],".2f"))+" dB"), rotation=0, verticalalignment='center',horizontalalignment ='center' )
	#enveloppe
	host.plot(partTime, Env_data[t_zero_idx:]/max(abs(sound.values.T)), linewidth=0.5, color ="r")

	#sound
	host.plot(partTime, soundData[t_zero_idx:]/max(abs(soundData)), linewidth=0.1, color ="b")

	#intensity
	par11.plot(IntPartTime, IntData[t_zero_idx:]/max(abs(IntData)), linewidth=0.8, color ="g")

	#%% Plots formants
	host2= host_subplot(212,axes_class=axisartist.Axes)

	spectrogram = sound.to_spectrogram(maximum_frequency=f0max)
	X, Y = spectrogram.x_grid(), spectrogram.y_grid()
	sg_db = 10 * np.log10(spectrogram.values)
	host2.pcolormesh(X-IntTime[t_zero_idx]*np.ones(len(X)), Y, sg_db, vmin=sg_db.max() - 60, cmap='afmhot')

	plt.ylim([spectrogram.ymin, spectrogram.ymax])
	plt.xlabel("time [s]")
	host2.set_ylabel("frequency [Hz]")
	host2.plot(IntPartTime, IntData[t_zero_idx:], linewidth=2, color ="w")
	host2.plot(IntPartTime, IntData[t_zero_idx:], linewidth=1, color ="g")
	#%% 1rst Formant
	host2.plot(tpartlist,f1_list, 'o', markersize=2, color='w')
	host2.plot(tpartlist,f1_list, 'o', markersize=1, color='b')
	#%% 2nd Formant
	host2.plot(tpartlist,f2_list, 'o', markersize=2, color='w')
	host2.plot(tpartlist,f2_list, 'o', markersize=1, color='r')
	#%% 3th Formant
	host2.plot(tpartlist,f3_list, 'o', markersize=2, color='w')
	host2.plot(tpartlist,f3_list, 'o', markersize=1, color='y')
	#%% 4th Formant
	host2.plot(tpartlist,f4_list, 'o', markersize=2, color='w')
	host2.plot(tpartlist,f4_list, 'o', markersize=1, color='g')
	#%% Pitch estimation
	host2.plot(pitch.xs(),pitch_values, 'o', markersize=1, color='w')
	host2.plot(pitch.xs(),pitch_values, 'o', markersize=0.5, color='pink')
	host2.set(xlim=(0, max(IntPartTime)))
	host.set(xlim=(0, max(IntPartTime)))
	#%% Emd HHSpectrum



	plt.suptitle(str(wav_files[10]))
	plt.show()
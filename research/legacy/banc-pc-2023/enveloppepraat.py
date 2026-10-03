import parselmouth

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.pylab as plt
import numpy as np
import os,h5py
import sys,glob
from parselmouth.praat import call



#%% This function measures pitches
def measurePitch(voiceID, f0min, f0max, unit):
	sound = parselmouth.Sound(voiceID) # read the sound
	duration = call(sound, "Get total duration") # duration
	pitch = call(sound, "To Pitch", 0.0, f0min, f0max) #create a praat pitch object
	meanF0 = call(pitch, "Get mean", 0, 0, unit) # get mean pitch
	stdevF0 = call(pitch, "Get standard deviation", 0 ,0, unit) # get standard deviation
	harmonicity = call(sound, "To Harmonicity (cc)", 0.01, f0min, 0.1, 1.0)
	hnr = call(harmonicity, "Get mean", 0, 0)
	pointProcess = call(sound, "To PointProcess (periodic, cc)", f0min, f0max)
	localJitter = call(pointProcess, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
	localabsoluteJitter = call(pointProcess, "Get jitter (local, absolute)", 0, 0, 0.0001, 0.02, 1.3)
	rapJitter = call(pointProcess, "Get jitter (rap)", 0, 0, 0.0001, 0.02, 1.3)
	ppq5Jitter = call(pointProcess, "Get jitter (ppq5)", 0, 0, 0.0001, 0.02, 1.3)
	ddpJitter = call(pointProcess, "Get jitter (ddp)", 0, 0, 0.0001, 0.02, 1.3)
	localShimmer =  call([sound, pointProcess], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
	localdbShimmer = call([sound, pointProcess], "Get shimmer (local_dB)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
	apq3Shimmer = call([sound, pointProcess], "Get shimmer (apq3)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
	aqpq5Shimmer = call([sound, pointProcess], "Get shimmer (apq5)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
	apq11Shimmer =  call([sound, pointProcess], "Get shimmer (apq11)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
	ddaShimmer = call([sound, pointProcess], "Get shimmer (dda)", 0, 0, 0.0001, 0.02, 1.3, 1.6)

	return duration, meanF0, stdevF0, hnr, localJitter, localabsoluteJitter, rapJitter, ppq5Jitter, ddpJitter, localShimmer, localdbShimmer, apq3Shimmer, aqpq5Shimmer, apq11Shimmer, ddaShimmer


#%% This function measures formants using Formant Position formula
def measureFormants(sound, wave_file, f0min,f0max):
	sound = parselmouth.Sound(sound) # read the sound
	pitch = call(sound, "To Pitch (cc)", 0, f0min, 15, 'no', 0.03, 0.45, 0.01, 0.35, 0.14, f0max)
	pointProcess = call(sound, "To PointProcess (periodic, cc)", f0min, f0max)

	formants = call(sound, "To Formant (burg)", 0.0025, 5, 5000, 0.025, 50)
	numPoints = call(pointProcess, "Get number of points")

	f1_list = []
	f2_list = []
	f3_list = []
	f4_list = []

	# Measure formants only at glottal pulses
	for point in range(0, numPoints):
		point += 1
		t = call(pointProcess, "Get time from index", point)
		f1 = call(formants, "Get value at time", 1, t, 'Hertz', 'Linear')
		f2 = call(formants, "Get value at time", 2, t, 'Hertz', 'Linear')
		f3 = call(formants, "Get value at time", 3, t, 'Hertz', 'Linear')
		f4 = call(formants, "Get value at time", 4, t, 'Hertz', 'Linear')
		f1_list.append(f1)
		f2_list.append(f2)
		f3_list.append(f3)
		f4_list.append(f4)

	f1_list = [f1 for f1 in f1_list if str(f1) != 'nan']
	f2_list = [f2 for f2 in f2_list if str(f2) != 'nan']
	f3_list = [f3 for f3 in f3_list if str(f3) != 'nan']
	f4_list = [f4 for f4 in f4_list if str(f4) != 'nan']

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

	return f1_mean, f2_mean, f3_mean, f4_mean, f1_median, f2_median, f3_median, f4_median

#%%
def measureEnveloppe(sound,):

	duration    = call(sound, "Get total duration") # Duration
	samplerate  = call(sound, "Get sampling frequency") #Sampling freq
	intensity   = sound.to_intensity()
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
	return




#%%
def draw_intensity(intensity):
    plt.plot(intensity.xs(), intensity.values.T, linewidth=3, color='w')
    plt.plot(intensity.xs(), intensity.values.T, linewidth=1)
    plt.grid(False)
    plt.ylim(0)
    plt.ylabel("intensity [dB]")

def draw_pitch(pitch):
    # Extract selected pitch contour, and
    # replace unvoiced samples by NaN to not plot
    pitch_values = pitch.selected_array['frequency']
    pitch_values[pitch_values==0] = np.nan
    plt.plot(pitch.xs(), pitch_values, 'o', markersize=5, color='w')
    plt.plot(pitch.xs(), pitch_values, 'o', markersize=2)
    plt.grid(False)
    plt.ylim(0, pitch.ceiling)
    plt.ylabel("fundamental frequency [Hz]")

def draw_enveloppe(pitch):
    # Extract selected pitch contour, and
    # replace unvoiced samples by NaN to not plot
    pitch_values = pitch.selected_array['frequency']
    pitch_values[pitch_values==0] = np.nan
    plt.plot(pitch.xs(), pitch_values, 'o', markersize=5, color='w')
    plt.plot(pitch.xs(), pitch_values, 'o', markersize=2)
    plt.grid(False)
    plt.ylim(0, pitch.ceiling)
    plt.ylabel("fundamental frequency [Hz]")

def draw_spectrogram(spectrogram, dynamic_range=70):
    X, Y = spectrogram.x_grid(), spectrogram.y_grid()
    sg_db = 10 * np.log10(spectrogram.values)
    plt.pcolormesh(X, Y, sg_db, vmin=sg_db.max() - dynamic_range, cmap='afmhot')
    plt.ylim([spectrogram.ymin, spectrogram.ymax])
    plt.xlabel("time [s]")
    plt.ylabel("frequency [Hz]")

def draw_formant(formant):
    # Extract selected pitch contour, and
    # replace unvoiced samples by NaN to not plot
    pitch_values = formant.selected_array['frequency']
    pitch_values[pitch_values==0] = np.nan
    plt.plot(pitch.xs(), pitch_values, 'o', markersize=5, color='w')
    plt.plot(pitch.xs(), pitch_values, 'o', markersize=2)
    plt.grid(False)
    plt.ylim(0, pitch.ceiling)
    plt.ylabel("fundamental frequency [Hz]")





path = 'data_D#0_1_L_2v/'
dir = os.path.dirname(path)
print(os.path.isdir(path))

hd5_files=glob.glob(path+'*.hdf5')
wav_files=glob.glob(path+'*.wav')

with h5py.File(str(hd5_files[0]), 'r') as f:
	Mesures_Press =    f['Mesures_Press']
	MesuresTemperature=f['MesuresTemperature']
	Mesures_Debit=     f['Mesures_Debit']

	#Pytta
	Mesures_Press_Acoustique=f['Mesures_Press_Acoustique']
	Mesures_Accelerations =  f['Mesures_Accelerations']

	#Calculs
	Mesures_Press_Pos=   f['Mesures_Press_Pos']
	Calculs_Surf=        f['Calculs_Surf']
	Measure_params =     f['Measure_params']
	Decoupe_Sections,Decoupe_Pressions,Decoupe_Clapet,Deplacement_mini_screw_S_mm,Deplacement_maxi_screw_S_mm,Deplacement_Clapet_deg_mini,Longeur_tige_clapet,Offset_Press,Max_pression = Measure_params



	sns.set() # Use seaborn's default style to make attractive graphs

	# Plot nice figures using Python's "standard" matplotlib library
	sound = parselmouth.Sound(str(wav_files[0]))




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


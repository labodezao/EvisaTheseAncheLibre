# EXTRAIT : fonction PraatCalcs() de Data_analysis.py (cœur scientifique).
# La boucle batch HDF5 complète reste sur le Drive (fileId 1R5-170W11_EZN0qpik_ILX93DteTyr8Q).
# Portée dans banc_recherche/analysis.py (praat_calcs) et impedance.py.
# -*- coding: utf-8 -*-
"""
Created on Sun Mar 27 17:17:09 2022

@author: labodezao
"""
import matplotlib.pylab as plt
import numpy as np
import os,h5py
import sys,glob

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
from scipy.io.wavfile import write, read
import pandas as pd




#%% This function measures formants using Formant Position formula
def PraatCalcs(sound, f0min=40,f0max =2000,SaveGraph=True,titlename="title"):
	offset_peaks=8000 # pour que la detection du Tresp commence après le son du clapet
	samplerate  = call(sound, "Get sampling frequency") #Sampling freq
	offset_T0 = int(samplerate/3)
	sound = parselmouth.Sound(sound.values.T.flatten()[offset_T0:])
	soundTime , soundData= sound.xs(),sound.values.T.flatten()

	spectrogram = sound.to_spectrogram(maximum_frequency=f0max)
	duration    = call(sound, "Get total duration") # Duration
	intensity   = call(sound, "To Intensity",50,1/samplerate)
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
	#print(intensity.values)
	IntData = intensity.values.T.flatten()
	IntTime = intensity.xs()

	#%% formants

	pitch = call(sound, "To Pitch", 0, f0min, f0max)
	pitch_values = pitch.selected_array['frequency']
	diff_pich = np.diff(pitch_values)
	PitchTime = pitch.xs()
	pitch_values[pitch_values==0] = np.nan
	pointProcess = call(sound, "To PointProcess (periodic, cc)", 20, 5000)
	formants = call(sound, "To Formant (burg)", 0.0001, 5, f0max, 0.03, 12)
	numPoints = call(pointProcess, "Get number of points")
	f1_list = []
	f2_list = []
	f3_list = []
	f4_list = []
	t_list = []


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

	f1_list= np.array(f1_list)
	f2_list= np.array(f2_list)
	f3_list= np.array(f3_list)
	f4_list= np.array(f4_list)

# 	print("Means")
	meanF0 = call(pitch, "Get mean", 0, 0, "Hertz") # get mean pitch
	stdevF0 = call(pitch, "Get standard deviation", 0 ,0, "Hertz") # get standard deviation
	harmonicity = call(sound, "To Harmonicity (cc)", 0.01, f0min, 0.1, 1.0)
	hnr = call(harmonicity, "Get mean", 0, 0)


	#%% Compute peaks and Tresp
	peaks_index, _ = signal.find_peaks(Env_data, height=0.45*max(abs(Env_data)))

	i_while=0
	while  Env_time[peaks_index[i_while]] < 0.50 or Env_time[peaks_index[i_while]]>0.85  :

		if i_while < peaks_index.shape[0] -1  :
			i_while += 1
		else:
			i_while = 0
			break
	t_zero_idx=peaks_index[i_while]
	t_zero = Env_time[t_zero_idx]
	print('T_zero value : ',t_zero,' sec')

	peaks_index_t0, _ = signal.find_peaks(Env_data[t_zero_idx+offset_peaks:], height=0.95*np.nanmean(Env_data[-int(len(Env_data[t_zero_idx:])/2):]))
	T_Up=Env_time[peaks_index_t0[0]+t_zero_idx+offset_peaks]
	Tresp=T_Up-t_zero
	print("Tresp ="+str(Tresp))

	meanFund = np.nanmean(pitch_values[np.argwhere(PitchTime >t_zero)].flatten())
	if len(f1_list ) >0 and len(np.argwhere(t_list >t_zero))>1 :
		f1_mean = np.nanmean(f1_list[np.argwhere(t_list >t_zero).flatten().astype(int)])
	else:
		f1_mean=0
	if len(f2_list) >0 and len(np.argwhere(t_list >t_zero))>1:
		f2_mean = np.nanmean(f2_list[np.argwhere(t_list >t_zero).flatten().astype(int)])
	else:
		f2_mean=0
	if len(f3_list) >0 and len(np.argwhere(t_list >t_zero))>1:
		f3_mean = np.nanmean(f3_list[np.argwhere(t_list >t_zero).flatten().astype(int)])
	else:
		f3_mean=0
	if len(f4_list) >0 and len(np.argwhere(t_list >t_zero))>1:
		f4_mean = np.nanmean(f4_list[np.argwhere(t_list >t_zero).flatten().astype(int)])
	else:
		f4_mean=0

	partTime= Env_time[t_zero_idx:] - Env_time[t_zero_idx]*np.ones(len(Env_time[t_zero_idx:]))
	IntPartTime = IntTime[t_zero_idx:] - IntTime[t_zero_idx]*np.ones(len(IntTime[t_zero_idx:]))

	tpartlist = t_list - IntTime[t_zero_idx]*np.ones(len(t_list))

	return IntPartTime, IntData[t_zero_idx:],partTime,  soundData[t_zero_idx:],t_zero,Tresp,PitchTime,pitch_values,tpartlist,f1_list,f2_list,f3_list,f4_list,meanFund,f1_mean,f2_mean,f3_mean,f4_mean

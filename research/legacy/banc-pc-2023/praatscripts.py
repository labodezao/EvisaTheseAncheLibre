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



class PraatMes:


	#%% This function measures formants using Formant Position formula
	def PraatCalcs(self,sound, f0min=40,f0max =2000,):

		self.soundTime , self.soundData= sound.xs(),sound.values.T.flatten()

		self.spectrogram = sound.to_spectrogram(maximum_frequency=f0max)
		self.duration    = call(sound, "Get total duration") # Duration
		self.samplerate  = call(sound, "Get sampling frequency") #Sampling freq
		intensity   = sound.to_intensity(time_step=1/self.samplerate)
		IntensTiler = call(intensity, "Down to IntensityTier") # Duration
		Amplitude   = call(IntensTiler, "To AmplitudeTier") # DurationTo AmplitudeTier
		TabReal     = call(Amplitude, "Down to TableOfReal") # DurationTo AmplitudeTier
		Mat         = call(TabReal, "To Matrix") # To Matrix
		TMatrix     = call(Mat, "Transpose") # To Matrix
		datas       = call(TMatrix, "To Sound (slice)", 2) # To MatrixTo Sound (slice): 2
		scaled      = call(datas, "Scale times to", 0,self.duration) # To MatrixTo Sound (slice): 2
		raw_env     = call(datas, "Resample",self.samplerate, 5)

		Env         = call(raw_env, "Filter (pass Hann band)", 0, 60, 5)
		#>> To express the classical envelope in dB instead of voltage:
		self.Env_data=Env.values.T.flatten()
		self.Env_time=Env.xs()
		self.IntData = intensity.values.T.flatten()
		self.IntTime = intensity.xs()

		#%% formants

		pitch = call(sound, "To Pitch", 1/20000, f0min, f0max)
		self.pitch_values = pitch.selected_array['frequency']
		diff_pich = np.diff(self.pitch_values)
		self.pitchTime = pitch.xs()
		self.pitch_values[self.pitch_values==0] = np.nan
		pointProcess = call(sound, "To PointProcess (periodic, cc)", 20, 20000)
		PitchTime = pitch.xs()
		formants = call(sound, "To Formant (burg)", 0.0001, 5, f0max, 0.03, 12)
		numPoints = call(pointProcess, "Get number of points")

		self.f1_list = []
		self.f2_list = []
		self.f3_list = []
		self.f4_list = []
		self.t_list = []


		for point in range(0, numPoints):
			point += 1
			t = call(pointProcess, "Get time from index", point)
			f1 = call(formants, "Get value at time", 1, t, 'Hertz', 'Linear')
			f2 = call(formants, "Get value at time", 2, t, 'Hertz', 'Linear')
			f3 = call(formants, "Get value at time", 3, t, 'Hertz', 'Linear')
			f4 = call(formants, "Get value at time", 4, t, 'Hertz', 'Linear')
			self.t_list.append(t)
			self.f1_list.append(f1)
			self.f2_list.append(f2)
			self.f3_list.append(f3)
			self.f4_list.append(f4)


		meanF0 = call(pitch, "Get mean", 0, 0, "Hertz") # get mean pitch
		stdevF0 = call(pitch, "Get standard deviation", 0 ,0, "Hertz") # get standard deviation
		harmonicity = call(sound, "To Harmonicity (cc)", 0.01, f0min, 0.1, 1.0)
		hnr = call(harmonicity, "Get mean", 0, 0)


		#%% Compute peaks and Tresp
		self.peaks_index, _ = signal.find_peaks(self.Env_data, height=0.90*max(abs(self.Env_data[-int(len(self.Env_data[:])/10):])))
		self.t_zero_idx=self.peaks_index[0]
		self.t_zero = self.Env_time[self.t_zero_idx]




		self.Tresp=self.Env_time[self.peaks_index[1]]-self.t_zero
		print("Tresp ="+str(self.Tresp))
		print(np.shape(self.pitch_values[np.argwhere(PitchTime >self.Tresp)].flatten().astype(int)))
		self.meanFund = statistics.mean(self.pitch_values[np.argwhere(PitchTime >self.Tresp)].flatten().astype(int))
		if len(self.f1_list) >0 :
			self.f1_mean = statistics.mean(self.f1_list[np.argwhere(self.t_list >self.Tresp).flatten().astype(int)])
		if len(self.f2_list) >0 :
			self.f2_mean = statistics.mean(self.f2_list[np.argwhere(self.t_list >self.Tresp).flatten().astype(int)])
		if len(self.f3_list) >0 :
			self.f3_mean = statistics.mean(self.f3_list[np.argwhere(self.t_list >self.Tresp).flatten().astype(int)])
		if len(self.f4_list) >0 :
			self.f4_mean = statistics.mean(self.f4_list[np.argwhere(self.t_list >self.Tresp).flatten().astype(int)])

		return




	#%%
	def draw_curve(self, titlename="",save=True):

		partTime= self.Env_time[self.t_zero_idx:] - self.Env_time[self.t_zero_idx]*np.ones(len(self.Env_time[self.t_zero_idx:]))
		IntPartTime = self.IntTime[self.t_zero_idx:] - self.IntTime[self.t_zero_idx]*np.ones(len(self.IntTime[self.t_zero_idx:]))

		tpartlist = self.t_list - self.IntTime[self.t_zero_idx]*np.ones(len(self.t_list))
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
		host.plot(self.Env_time[self.peaks_index[0:2]] - self.t_zero*np.ones(len(self.Env_time[self.peaks_index[0:2]])), self.Env_data[self.peaks_index[0:2]]/max(abs(self.Env_data)), ".",color = "r",markersize=2)


		#plot a line with text
		host.axvline(x = self.Env_time[0], color = 'r', label = 'axvline - full height')
		host.axvline(x = self.Env_time[self.peaks_index[1]]-self.t_zero, color = 'r', label = 'axvline - full height')
		if len(self.peaks_index) >1:
			host.text(self.Env_time[self.peaks_index[1]-self.t_zero_idx], 0.95, "tresp = "+ str(format(self.Tresp*1000,".2f")+" ms, Intensity = "+str(format(self.IntData[self.peaks_index[1]],".2f"))+" dB"), rotation=0, verticalalignment='center',horizontalalignment ='center' )
		#enveloppe
		host.plot(partTime, self.Env_data[self.t_zero_idx:]/max(abs(self.soundData)), linewidth=0.5, color ="r")

		#sound
		host.plot(partTime, self.soundData[self.t_zero_idx:]/max(abs(self.soundData)), linewidth=0.1, color ="b")

		#intensity
		par11.plot(IntPartTime, self.IntData[self.t_zero_idx:]/max(abs(self.IntData)), linewidth=0.8, color ="g")

		#%% Plots formants
		host2= host_subplot(212,axes_class=axisartist.Axes)


		X, Y = self.spectrogram.x_grid(), self.spectrogram.y_grid()
		sg_db = 10 * np.log10(self.spectrogram.values)
		host2.pcolormesh(X-self.IntTime[self.t_zero_idx]*np.ones(len(X)), Y, sg_db, vmin=sg_db.max() - 60, cmap='afmhot')

		plt.ylim([self.spectrogram.ymin, self.spectrogram.ymax])
		plt.xlabel("time [s]")
		host2.set_ylabel("frequency [Hz]")
		host2.plot(IntPartTime, self.IntData[self.t_zero_idx:], linewidth=2, color ="w")
		host2.plot(IntPartTime, self.IntData[self.t_zero_idx:], linewidth=1, color ="g")
		#%% 1rst Formant
		host2.plot(tpartlist,self.f1_list, 'o', markersize=2, color='w')
		host2.plot(tpartlist,self.f1_list, 'o', markersize=1, color='b')
		#%% 2nd Formant
		host2.plot(tpartlist,self.f2_list, 'o', markersize=2, color='w')
		host2.plot(tpartlist,self.f2_list, 'o', markersize=1, color='r')
		#%% 3th Formant
		host2.plot(tpartlist,self.f3_list, 'o', markersize=2, color='w')
		host2.plot(tpartlist,self.f3_list, 'o', markersize=1, color='y')
		#%% 4th Formant
		host2.plot(tpartlist,self.f4_list, 'o', markersize=2, color='w')
		host2.plot(tpartlist,self.f4_list, 'o', markersize=1, color='g')
		#%% Pitch estimation
		host2.plot(self.pitchTime,self.pitch_values, 'o', markersize=1, color='w')
		host2.plot(self.pitchTime,self.pitch_values, 'o', markersize=0.5, color='pink')
		host2.set(xlim=(0, max(IntPartTime)))
		host.set(xlim=(0, max(IntPartTime)))
		#%% Emd HHSpectrum



		plt.suptitle(str(titlename))
		plt.show()
		if save:
			figname = "%s.png" %(str(titlename))
			plt.savefig(os.path.join(figname),dpi=400)


	def Get_Tresp(self, titlename=""):
		return self.Tresp

	def Get_Intensities(self, titlename=""):
		return self.IntTime , self.IntData

	def Get_Freqs(self, titlename=""):
		return self.t_list, self.f1_list , self.f2_list, self.f3_list ,self.f4_list,self.pitch_values,self.pitchTime

	def Get_Mean_Freqs(self, titlename=""):
		return  self.meanFund , self.f1_mean, self.f2_mean ,self.f3_mean,self.f4_mean

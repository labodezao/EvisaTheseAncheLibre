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


	#%% Plots enveloppes
	plt.figure(figsize=(8, 10))
	host= host_subplot(211,axes_class=axisartist.Axes)

	Int_Up = np.nanmean(IntData[np.argwhere((IntTime >t_zero) | (IntTime <T_Up) ).flatten().astype(int)])
	plt.subplots_adjust(right=0.75)
	par11 = host.twinx()

	#par11.axis["right"] = host.new_fixed_axis(loc="right", offset=(60, 0))
	host.set_xlabel("Temps [s]")
	host.set_ylabel("Amplitude [Pa]")  # Le signal sonore et son enveloppe
	par11.set_ylabel("Intensity []", color ="g") # Intensité du signal


	#peaks
	host.plot(Env_time[peaks_index[0]] - t_zero, Env_data[peaks_index[0]]/max(abs(Env_data)), "x",color = "r",markersize=6)
	host.plot(Env_time[peaks_index_t0[0:2]+offset_peaks +t_zero_idx] - t_zero, Env_data[peaks_index_t0[0:2]+offset_peaks +t_zero_idx]/max(abs(Env_data)), "x",color = "r",markersize=6)
	#plot a line with text
	host.axvline(x = 0, color = 'r', label = 'axvline - full height')
	if len(peaks_index_t0) >0:
		host.axvline(x = Env_time[peaks_index_t0[0]+offset_peaks +t_zero_idx]-t_zero, color = 'r', )
		host.text(Env_time[peaks_index_t0[0]+offset_peaks +t_zero_idx]-t_zero, 0.95, "tresp = "+ str(format(Tresp*1000,".2f")+" ms, Intensity = "+str(format(Int_Up ,".2f"))+" dB"), rotation=0, verticalalignment='center',horizontalalignment ='center' )
	#enveloppe
	host.plot(partTime, Env_data[t_zero_idx:]/max(abs(Env_data)), linewidth=0.5, color ="r")

	#sound
	host.plot(partTime, soundData[t_zero_idx:]/max(abs(soundData)), linewidth=0.1, color ="b")

	#intensity
	par11.plot(IntPartTime, IntData[t_zero_idx:]/max(abs(IntData)), linewidth=0.8, color ="g")

	#%% Plots formants
	host2= host_subplot(212,axes_class=axisartist.Axes)


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
	host2.plot(PitchTime,pitch_values, 'o', markersize=1, color='w')
	host2.plot(PitchTime,pitch_values, 'o', markersize=0.5, color='pink')
	host2.set(xlim=(0, max(IntPartTime)))
	host.set(xlim=(0, max(IntPartTime)))
	#%% Emd HHSpectrum



	plt.suptitle(str(titlename))
	plt.show()
	if SaveGraph:
		#print('savegraphed !')
		figname = "%s.png" %(str(titlename))
		plt.savefig(os.path.join(local_dir,figname),dpi=400)
		plt.close('all')



	return IntPartTime, IntData[t_zero_idx:],partTime,  soundData[t_zero_idx:],t_zero,Tresp,PitchTime,pitch_values,tpartlist,f1_list,f2_list,f3_list,f4_list,meanFund,f1_mean,f2_mean,f3_mean,f4_mean





plt.close("all")
path = 'data/'
local_dir = os.path.dirname(path)


hd5_files=glob.glob(path+'*.hdf5')
makeGraphs=True

shutdown_restore = 0
sns.set() # Use seaborn's default style to make attractive graphs

# Plot nice figures using Python's "standard" matplotlib library


with h5py.File(str(hd5_files[0]), 'a') as f:
	Mesures_Press =    f['Mesures_Press']
	MesuresTemperature=f['MesuresTemperature']
	Mesures_Debit=     f['Mesures_Debit']

	#pytta
	Mesures_Press_Acoustique=f['Mesures_Press_Acoustique']
	Mesures_Accelerations =  f['Mesures_Accelerations']

	#calculs
	Mesures_Press_Pos=   f['Mesures_Press_Pos']
	Calculs_Surf=        f['Calculs_Surf']
	Measure_params =     f['Measure_params']
	Decoupe_Sections,Decoupe_Pressions,Decoupe_Clapet,Deplacement_mini_screw_S_mm,Deplacement_maxi_screw_S_mm,Deplacement_Clapet_deg_mini,Longeur_tige_clapet,Offset_Press,Max_pression = Measure_params

	Tresp=f.require_dataset('Tresp', (2,Decoupe_Sections, Decoupe_Pressions,Decoupe_Clapet,2),maxshape=(2,None,None, None,2),dtype='f4',chunks=True)
	Freq=f.require_dataset('Freq', (2,Decoupe_Sections, Decoupe_Pressions,Decoupe_Clapet,5),maxshape=(2,None,None, None,5),dtype='f4',chunks=True)

	Shut_params = f.require_dataset('Shut_params', (4, ) ,dtype='i4')

	try:
		Pitches =f.require_dataset('Pitches', (2,Decoupe_Sections, Decoupe_Pressions,Decoupe_Clapet,2,7),maxshape=(2,None,None, None,2,None),dtype='f4',chunks=True)
	except:
		Pitches=f['Pitches']
	try:
		Formant =f.require_dataset('Formant', (2,Decoupe_Sections, Decoupe_Pressions,Decoupe_Clapet,5,7),maxshape=(2,None,None, None,5,None),dtype='f4',chunks=True)
	except:
		Formant=f['Formant']




	try:
		Part_Press_Acoustique=f.require_dataset('Part_Press_Acoustique', (2,Decoupe_Sections, Decoupe_Pressions,Decoupe_Clapet,2,1),maxshape=(2,None,None, None,2,None),dtype='f4',chunks=True)
	except:
		Part_Press_Acoustique = f['Part_Press_Acoustique']

	try:
		Intensities=f.require_dataset('Intensities', np.shape(Mesures_Press_Acoustique),maxshape=(2,None,None, None,2,None),dtype='f4',chunks=True)
	except:
		Intensities = f['Intensities']



	try:
		Results=f.require_dataset('Results', (16,Decoupe_Sections* Decoupe_Pressions*Decoupe_Clapet*2),maxshape=(16,None),dtype='f4',chunks=True)
	except:
		Results = f['Results']


	if shutdown_restore == 0:
		Ppos_shut=0
		Pplus_shut=0
		Splus_shut =0
		Clap_shut =0
		Shut_params[:]=[Ppos_shut,Splus_shut,Pplus_shut,Clap_shut]
	else :

		if Shut_params[3] > 0 :
			 Shut_params[3] -=1
		else :
			Shut_params[3] =0
			Shut_params[2] -= 1

# 	print(np.transpose(Results))
# Boucle des pression positives
#	try:

	for P_pos in range(0,2):


		#reinitialize shudown params
		if ( P_pos < Shut_params[0] and shutdown_restore):
			continue

		print("Pressions Positive 1-Oui, 0-non : ", P_pos)

	# Boucle des sections
		for S_plus in range(0,Decoupe_Sections):


			if ( S_plus < Shut_params[1] and shutdown_restore):
				continue

			print("Section courante", S_plus)

	# Boucle des incréments de pression

			for P_plus in range(0,Decoupe_Pressions):


				if P_plus < Shut_params[2] and shutdown_restore :
					continue

				print("Pression courante", P_plus)


				for i_Clap in range(0,Decoupe_Clapet):

					if (i_Clap < Shut_params[3] and shutdown_restore ):
						continue

					print("Clapet courant", i_Clap)
					name = f'PPos{P_pos}Sec{S_plus}PPlus{P_plus}iClap{i_Clap}'
					#rate,soundWave=read(path+name+ ".wav", )
					SoundTemp= np.array(Mesures_Press_Acoustique[P_pos] [S_plus] [ P_plus] [i_Clap] [1])

					sound = parselmouth.Sound(SoundTemp/2**31)
					#print(sound.get_intensity())


					#GradP	Surface	Pression	hClap	SurfCalc	PressMes	Débit	Impédence	PHydro	Tresp	Intensité	Freq0	Formant1	Formant2	Formant3	Formant4




					TempRes  = PraatCalcs(sound,titlename=name)
					#print(TempRes)

					Tresp [P_pos, S_plus, P_plus,i_Clap,0]=TempRes[4]
					Tresp [P_pos, S_plus, P_plus,i_Clap,1]=TempRes[5]


					if TempRes[0].shape[0] > Intensities.shape[5]:
						Intensities.resize((2,Decoupe_Sections, Decoupe_Pressions,Decoupe_Clapet,2,TempRes[0].shape[0]))
						#print("Int_Time reshaped")


					if TempRes[2].shape[0] > Part_Press_Acoustique.shape[5]:
						Part_Press_Acoustique.resize((2,Decoupe_Sections, Decoupe_Pressions,Decoupe_Clapet,2,TempRes[2].shape[0]))
						#print("PressAc_Time reshaped")

					if TempRes[6].shape[0] > Pitches.shape[5]:
						Pitches.resize((2,Decoupe_Sections, Decoupe_Pressions,Decoupe_Clapet,2,TempRes[6].shape[0]))
						#print("Piches_Time reshaped")

					if TempRes[8].shape[0] > Formant.shape[5]:
						Formant.resize((2,Decoupe_Sections, Decoupe_Pressions,Decoupe_Clapet,5,TempRes[8].shape[0]))
					Formant.resize((2,Decoupe_Sections, Decoupe_Pressions,Decoupe_Clapet,5,TempRes[8].shape[0]))
					print("Formant reshaped")



					Intensities[P_pos, S_plus, P_plus,i_Clap,0][:TempRes[0].shape[0]] = TempRes[0]
					Intensities[P_pos, S_plus, P_plus,i_Clap,1][:TempRes[1].shape[0]] =TempRes[1]
					Intensities[P_pos, S_plus, P_plus,i_Clap,0][Intensities[P_pos, S_plus, P_plus,i_Clap,1]==0] = np.nan
					Intensities[P_pos, S_plus, P_plus,i_Clap,1][Intensities[P_pos, S_plus, P_plus,i_Clap,1]==0] = np.nan
					Part_Press_Acoustique[P_pos, S_plus, P_plus,i_Clap,0][:TempRes[2].shape[0]]=TempRes[2]
					Part_Press_Acoustique[P_pos, S_plus, P_plus,i_Clap,1][:TempRes[3].shape[0]] =TempRes[3]
					Pitches[P_pos, S_plus, P_plus,i_Clap,0][:TempRes[6].shape[0]] = TempRes[6]
					Pitches[P_pos, S_plus, P_plus,i_Clap,1][:TempRes[7].shape[0]] = TempRes[7]
					Formant[P_pos, S_plus, P_plus,i_Clap,0][:TempRes[8].shape[0]] = TempRes[8]
					Formant[P_pos, S_plus, P_plus,i_Clap,1][:TempRes[9].shape[0]] = TempRes[9]
					Formant[P_pos, S_plus, P_plus,i_Clap,2][:TempRes[10].shape[0]] = TempRes[10]
					Formant[P_pos, S_plus, P_plus,i_Clap,3][:TempRes[11].shape[0]] = TempRes[11]
					Formant[P_pos, S_plus, P_plus,i_Clap,4][:TempRes[12].shape[0]] = TempRes[12]
					Freq[P_pos, S_plus, P_plus,i_Clap,0] = TempRes[13]
					Freq[P_pos, S_plus, P_plus,i_Clap,1] = TempRes[14]
					Freq[P_pos, S_plus, P_plus,i_Clap,2] = TempRes[15]
					Freq[P_pos, S_plus, P_plus,i_Clap,3] = TempRes[16]
					Freq[P_pos, S_plus, P_plus,i_Clap,4] = TempRes[17]


					try:
						Press_to_idx=np.argwhere(Mesures_Press[P_pos][ S_plus][ P_plus][i_Clap][0] >Tresp [P_pos][ S_plus][ P_plus][i_Clap][0]).flatten().astype(int)[0]
					except:
						Press_to_idx = 0

					try:
						Debit_t0_idx =np.argwhere(Mesures_Debit[P_pos][ S_plus][ P_plus][i_Clap][0] >Tresp [P_pos][ S_plus][ P_plus][i_Clap][0]).flatten().astype(int)[0]
					except:
						Debit_t0_idx = 0


					Press_In_t0 = Mesures_Press[P_pos, S_plus, P_plus,i_Clap,1][Press_to_idx:]
					Débit_In_t0 = Mesures_Debit[P_pos, S_plus, P_plus,i_Clap,1][Debit_t0_idx:]
					Press_In_t0[Press_In_t0==0] = np.nan
					Débit_In_t0[Débit_In_t0==0] = np.nan
					Press_In_Mean =np.nanmean(Press_In_t0)
					Débit_In_Mean =np.nanmean(Débit_In_t0)

					Impedence = Press_In_Mean/Débit_In_Mean
					PuiHydro = Press_In_Mean*Débit_In_Mean

					name = f'PPos{P_pos}Sec{S_plus}PPlus{P_plus}iClap{i_Clap}'
					Tresp [P_pos][ S_plus][ P_plus][i_Clap] =0
					Intensities[P_pos][ S_plus][ P_plus][i_Clap] =0

					Results[:,i_Clap] = (P_pos,S_plus,P_plus,i_Clap,
										 Calculs_Surf[P_pos][ S_plus][ P_plus][ i_Clap],
										 Press_In_Mean,
										 Débit_In_Mean,
										 Impedence,
										 PuiHydro,
										 Tresp[P_pos][ S_plus][ P_plus][i_Clap][1],
										 np.nanmean(Intensities[P_pos][ S_plus][ P_plus][i_Clap]),

										 Freq[P_pos][ S_plus][ P_plus][i_Clap][0],
										 Freq[P_pos][ S_plus][ P_plus][i_Clap][1],
										 Freq[P_pos][ S_plus][ P_plus][i_Clap][2],
										 Freq[P_pos][ S_plus][ P_plus][i_Clap][3],
										 Freq[P_pos][ S_plus][ P_plus][i_Clap][4])

	df = pd.DataFrame(np.transpose(Results), columns = ['P_pos','S_plus','P_plus','i_Clap','Calculs_Surf','Press_In_Mean','Débit_In_Mean','Impedence','PuiHydro','Tresp','Intensitiy','Freq0','Form1','Form2','Form3','Form4'])
	df.to_csv(path+'plan_exp.csv')
	print(df)
	print(type(df))
# 	except Exception as e:
# 		exc_type, exc_obj, exc_tb = sys.exc_info()
# 		shutdown_restore =1
# 		np.save(path +'analysis_shutdownrestore.npy', [P_pos, P_plus, S_plus, i_Clap])

# 		fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
# 		print("Error :",fname, exc_tb.tb_lineno,e)
# 		pass
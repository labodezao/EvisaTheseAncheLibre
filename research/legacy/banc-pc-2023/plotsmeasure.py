# -*- coding: utf-8 -*-
"""
Created on Sun Mar 27 17:17:09 2022

@author: labodezao
"""
import matplotlib.pylab as plt
import numpy as np
import os,h5py
import sys,glob
from ipywidgets import interactive
from IPython.display import display

path = 'data_D#0_1_L_2v/'
dir = os.path.dirname(path)
print(os.path.isdir(path))

hd5_files=glob.glob(path+'*.hdf5')

print(hd5_files[0])
with h5py.File(str(hd5_files[0]), 'r') as f:
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







	# Boucle des pression positives

	for P_pos in range(0,2):
		print("Pressions Positive 1-Oui, 0-non : ", P_pos)

	# Boucle des sections
		for S_plus in range(0,Decoupe_Sections):
			print("Section courante", S_plus)

	# Boucle des incréments de pression

			for P_plus in range(0,Decoupe_Pressions):

				print("Pression courante", P_plus)

				print('pouet')



	plt.plot(Mesures_Press_Acoustique[0][0][0][0][0],Mesures_Press_Acoustique[0][0][0][0][1]) # du type mat[pression_pos][Pos_section][Val_Pression][i_Clap ][data,temps]

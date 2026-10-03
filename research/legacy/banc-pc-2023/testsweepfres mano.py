# -*- coding: utf-8 -*-
"""
Created on Fri Dec 11 00:56:26 2020

@author: labodezao
"""
import sys
import time
from rshell import pyboard

import numpy as np
import matplotlib.pyplot as plt
import os
from scipy.io.wavfile import write
import pyaudio
import sounddevice as sd

from scipy import signal


path = 'data\\'
dir = os.path.dirname(path)
print(os.path.isdir(path))
if not os.path.isdir(path):
	os.mkdir(path)       

Offset_Press = 300 # Offset de pression 
Max_pression = 3000 # value entre 0 et 4095 qui fixe le max de pression a étudier
pente =2
Freq=3
try:
	pyb_mes = pyboard.Pyboard('COM11')
	pyb_mes.enter_raw_repl()
	pyb_control = pyboard.Pyboard('COM10')
	pyb_control.enter_raw_repl()
	pyb_mes.exec_raw("from MesAnche import *")
	pyb_mes.exec("mes = MesAnches()")
	pyb_control.exec("from valvecontrol import *")
	pyb_control.exec("control = ValControl()")
	Decoupe_Pressions=Max_pression - Offset_Press
	Mes_Press = np.zeros((2,int(Decoupe_Pressions/pente)))
	t = time.time()
	
	for P_plus in range(0,int(Decoupe_Pressions/pente),1):
		tn=(time.time() - t)
		Mes_Press[0,P_plus] = tn
		#dac_press = pente*(Max_pression-Offset_Press)*(P_plus/(Decoupe_Pressions-1))+Offset_Press #linear
		dac_press = 800*np.sin(2*np.pi*Freq*tn)+1000
		dac_press = 800*signal.sawtooth(2 * np.pi * Freq * tn)+1000
		comm_p=f"control.Set_Press({int(dac_press)})"
		pyb_control.exec(comm_p)
		#On sauvegarde les mesures
		Mes_Press[1,P_plus] = float(pyb_mes.exec("print(mes.Mes_Press())"))
		print(P_plus,dac_press )
		time.sleep(0.00001)
		P_plus +=1

	plt.figure(figsize=(16,9))
	plt.plot(Mes_Press[0,0:-1].T,Mes_Press[1,0:-1].T) # du type mat[pression_pos][Pos_section][Val_Pression][i_Clap ][data,temps]
	plt.xlabel('Temps (s)')
	plt.ylabel('Pression acoustique')
	plt.show()

except Exception as e:
	exc_type, exc_obj, exc_tb = sys.exc_info()
	fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
	print("Error :",fname, exc_tb.tb_lineno,e)
	pass


pyb_mes.exit_raw_repl()
pyb_mes.close()

pyb_control.exec("control.Set_Press(00)")
pyb_control.exit_raw_repl()
pyb_control.close()


# -*- coding: utf-8 -*-
"""
Created on Tue Feb 15 14:33:35 2022

@author: labodezao
"""
import sys
import time
from rshell import pyboard
import pytta
import numpy as np
import matplotlib.pylab as plt
import os
import numpy as np
from scipy import interpolate, signal


Fs=250 #frequence echantillonage interpol
pyb_mes = pyboard.Pyboard('COM11')
pyb_mes.enter_raw_repl()
pyb_mes.exec_raw("from MesAnche import *")
pyb_mes.exec("mes = MesAnches()")
comm_mesure ="mes.Mes_Full_Mes(sampling=120, acquisition_time=3)"
pyb_mes.exec_raw_no_follow(comm_mesure)
time.sleep(1)


pyb_mes.follow(timeout=5)
comm_grab ="print(mes.Grab_Full_Mes())"
Mes_bytes_unformatted = pyb_mes.exec(comm_grab)
Mes_bytes = eval(str(Mes_bytes_unformatted, "ascii"))

Mes_Press =np.frombuffer(Mes_bytes, dtype=np.float32)
Mes_Press=Mes_Press.reshape(6,int(Mes_Press.size/6))
print(Mes_Press)



m_press = Mes_Press[0:2,:].shape[1]
m_temp = Mes_Press[2:4,:].shape[1]


f_interpol = interpolate.interp1d(Mes_Press[0,:], Mes_Press[1,:])
xx = np.linspace(Mes_Press[0,0], Mes_Press[0,-1], int(Mes_Press[0,-1]*Fs))



yy = f_interpol(xx)
W0 =2*2/Fs
W1       = 2*80/Fs #filter parameter Cut frequency over the sample frequency
#(b, a)   = signal.butter(4, [W0, W1], btype='band')
(b, a)   = signal.butter(4, W1, btype='lowpass')

filt_yy = signal.filtfilt(b, a, yy)

#plt.plot(Mes_Press[0,:],Mes_Press[1,:])
plt.plot(xx,filt_yy, 'g',linewidth='0.5')
plt.ylabel('Amplitude ')
plt.xlim(0,max(Mes_Press[0,:])+0.001)
plt.ylim(-5500,5500)
plt.show()


pyb_mes.exit_raw_repl()
pyb_mes.close()

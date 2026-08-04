# -*- coding: utf-8 -*-
"""
Created on Fri Dec 11 00:56:26 2020

@author: labodezao
"""
import sys
import time
from rshell import pyboard

import numpy as np
import matplotlib.pylab as plt
import os
from scipy.io.wavfile import write
import pyaudio
import sounddevice as sd
import h5py



p = pyaudio.PyAudio()
print (sd.query_devices())
device_index=1


RATE=48000
SAMPLING=200
RECORD_SECONDS = 3
CHUNKSIZE = 1024
nbchannels=1
device_idx=device_index
stream = p.open(format=pyaudio.paFloat32, channels=nbchannels, rate=RATE, input=True, frames_per_buffer=CHUNKSIZE, input_device_index =device_idx)
shutdown_restore=1




def record( stream = stream,filename=None,nbchannels=nbchannels):


    # initialize portaudio

   frames = np.zeros((1 , nbchannels)) # A python-list of chunks(numpy.ndarray)
   for _ in range(0, int(RATE / CHUNKSIZE * RECORD_SECONDS)):
       data = stream.read(CHUNKSIZE)
       frames = np.append(frames,np.reshape(np.frombuffer(data, dtype=np.int32),(CHUNKSIZE , nbchannels) ),0)

   #Convert the list of numpy-arrays into a 1D array (column-wise)
   # plot data
   #frames[:,0]   = frames[:,0] / max(abs(frames[:,0] ))
   #if nbchannels ==2 :
      #frames[:,1]  = frames[:,1] / max(abs(frames[:,1] ))

   times = np.linspace(0, frames[:,0].shape[0]/RATE, num=frames[:,0].shape[0])
   #plt.plot(times,frames[:,0],linewidth=0.3)
   #plt.show()

   if filename is not None:
       write(filename+ ".wav", RATE, frames.astype(np.float32))
   return frames,times

path = 'data\\'
dir = os.path.dirname(path)
print(os.path.isdir(path))
if not os.path.isdir(path):
	os.mkdir(path)




try:
	pyb_mes = pyboard.Pyboard('COM11')
	pyb_mes.enter_raw_repl()
	pyb_control = pyboard.Pyboard('COM10')
	pyb_control.enter_raw_repl()
	pyb_mes.exec_raw("from MesAnche import *")
	pyb_mes.exec("mes = MesAnches()")
	pyb_control.exec("from valvecontrol import *")
	pyb_control.exec("control = ValControl()")

	Decoupe_Sections = 8       # int
	Decoupe_Pressions = 8      # int
	Decoupe_Clapet = 8         # int

	Deplacement_mini_screw_S_mm =4   # mm 0 mm is min
	Deplacement_maxi_screw_S_mm =12   # mm 14 mm is max
	Deplacement_Clapet_deg_mini =2   # deg
	Deplacement_Clapet_deg_maxi =22   # deg
	LargeurTrouSection = 15 #mm
	Longeur_tige_clapet = 20     # mm
	Offset_Press = 300 # Offset de pression
	Max_pression = 3500 # value entre 0 et 4095 qui fixe le max de pression a étudier


	with h5py.File(path+'Measure_dataset'+ f'nSec{Decoupe_Sections}nPress{Decoupe_Pressions}nClap{Decoupe_Clapet}' +'.hdf5', 'a') as f:
		Mesures_Press = f.require_dataset('Mesures_Press', (2,Decoupe_Sections, Decoupe_Pressions,Decoupe_Clapet,2,SAMPLING*RECORD_SECONDS),maxshape=(2,None,None, None,2,None),dtype='f4',chunks=True)
		MesuresTemperature=f.require_dataset('MesuresTemperature', (2,Decoupe_Sections, Decoupe_Pressions,Decoupe_Clapet,2,SAMPLING*RECORD_SECONDS),maxshape=(2,None,None, None,2,None),dtype='f4',chunks=True)
		Mesures_Debit=f.require_dataset('Mesures_Debit', (2,Decoupe_Sections, Decoupe_Pressions,Decoupe_Clapet,2,SAMPLING*RECORD_SECONDS),maxshape=(2,None,None, None,2,None) ,dtype='f4',chunks=True)

		#pytta
		Mesures_Press_Acoustique=f.require_dataset('Mesures_Press_Acoustique', (2,Decoupe_Sections, Decoupe_Pressions,Decoupe_Clapet,2,RATE*RECORD_SECONDS),maxshape=(2,None,None, None,2,None),dtype='f4',chunks=True)
		Mesures_Accelerations = f.require_dataset('Mesures_Accelerations', (2,Decoupe_Sections, Decoupe_Pressions,Decoupe_Clapet,2,SAMPLING*RECORD_SECONDS),dtype='f4',chunks=True)

		#calculs
		Mesures_Press_Pos=f.require_dataset('Mesures_Press_Pos', (2,Decoupe_Sections, Decoupe_Pressions,Decoupe_Clapet,2),maxshape=(2,None,None, None,2),dtype='f4',chunks=True)
		Calculs_Surf=f.require_dataset('Calculs_Surf', (2,Decoupe_Sections, Decoupe_Pressions,Decoupe_Clapet),maxshape=(2,None,None, None) ,dtype='f4',chunks=True)
		Measure_params = f.require_dataset('Measure_params', (9, ) ,dtype='i4')
		Shut_params = f.require_dataset('Shut_params', (4, ) ,dtype='i4')
		Measure_params[:] = [Decoupe_Sections,Decoupe_Pressions,Decoupe_Clapet,Deplacement_mini_screw_S_mm,Deplacement_maxi_screw_S_mm,Deplacement_Clapet_deg_mini,Longeur_tige_clapet,Offset_Press,Max_pression]

		if shutdown_restore == 0:
			Ppos_shut=0
			Pplus_shut=0
			Splus_shut =0
			Clap_shut =0
			Shut_params[:]=[Ppos_shut,Splus_shut,Pplus_shut,Clap_shut]
			#I2c : Pression débit température et surface

		else :
			i_P_pos = True
			i_S_Plus = True
			i_P_Plus = True
			i_Clap_Modif = True
			if Clap_shut > 0 :
				 Shut_params[3] -=1
			else :
				Shut_params[3] =0
				Splus_shut -= 1

		Electro_vanne=0 #Si Electro_vanne=1 : on as un clapet fixe et on commande l'arrivée de la pression par electrovanne temporisée.

		#init script
		Mes_bytes =0

		# Boucle des pression positives

		for P_pos in range(0,2):
			print("Pressions Positive 1-Oui, 0-non : ", P_pos)
			#reinitialize shudown params
			if (Shut_params[0]!= 0 and P_pos == 0 and i_P_pos):
				P_pos = Shut_params[0]
			else:
				Shut_params[0]=P_pos
				i_P_pos =False
		# Boucle des sections
			for S_plus in range(0,Decoupe_Sections):
				print("Section courante", S_plus)
				if (Shut_params[1]!= 0 and S_plus == 0 and i_S_Plus):
					S_plus = Shut_params[1]
				else:
					Shut_params[1]=S_plus
					i_S_Plus=False
				pos_mm=(S_plus)/(Decoupe_Sections-1)*(Deplacement_maxi_screw_S_mm-Deplacement_mini_screw_S_mm) +Deplacement_mini_screw_S_mm
				Surf=pos_mm*LargeurTrouSection
				comm_s = f"mes.Move_to_Pos({pos_mm},500)"
				#pyb_mes.exec("mes.Move_to_Pos(0,500)")
				pyb_mes.exec(comm_s)
				print('Srew_mm : ',(S_plus/(Decoupe_Sections-1))*(Deplacement_maxi_screw_S_mm-Deplacement_mini_screw_S_mm))

		# Boucle des incréments de pression

				for P_plus in range(0,Decoupe_Pressions):

					print("Pression courante", P_plus)
					if (Shut_params[2]!= 0 and P_plus == 0 and i_P_Plus):
						P_plus = Shut_params[2]
					else:
						Shut_params[2]=P_plus
						i_P_Plus=False
					# On as fixé une surface et on règle on pression :
					#on règle le ventilo
					comm_p=f"control.Set_Press({int((Max_pression-Offset_Press)*(P_plus/(Decoupe_Pressions-1))+Offset_Press)})"
					pyb_control.exec(comm_p)
					for i_Clap in range(0,Decoupe_Clapet):
						if (Shut_params[3]!= 0 and i_Clap == 0 and i_Clap_Modif):
							i_Clap = Shut_params[3]
						else:
							Shut_params[3]=i_Clap
							i_Clap_Modif=False
						#On sauvegarde les mesures
						name = f'PPos{P_pos}Sec{S_plus}PPlus{P_plus}iClap{i_Clap}'
						filename = f'{path}{name}'
						print('****************iclap',i_Clap)
						pyb_control.exec_raw_no_follow("control.Posi_Valve_init()")
						time.sleep(1)
						if Electro_vanne ==1:
							comm_clap=f"control.Move_to_angle( {int((Deplacement_Clapet_deg_maxi-Deplacement_Clapet_deg_mini)*(i_Clap/(Decoupe_Clapet-1))+Deplacement_Clapet_deg_mini)}, 2000)"
							pyb_control.exec_raw_no_follow(comm_clap)
							pyb_control.exec("control.Vanne_Close()") # la temporisation est sur le relay réglée sur 500 ms environ
							pyb_control.exec("control.Vanne_Open()") # la temporisation est sur le relay réglée sur 500 ms environ
						else :
							pyb_control.exec("control.Vanne_Open()")
							print('************angle clap',int((Deplacement_Clapet_deg_maxi-Deplacement_Clapet_deg_mini)*(i_Clap/(Decoupe_Clapet-1))+Deplacement_Clapet_deg_mini))
							comm_clap=f"control.Move_to_angle( {int((Deplacement_Clapet_deg_maxi-Deplacement_Clapet_deg_mini)*(i_Clap/(Decoupe_Clapet-1))+Deplacement_Clapet_deg_mini)}, 1500,800)"
							pyb_control.exec_raw_no_follow(comm_clap)
						time.sleep(0.2)


						comm_mesure ="mes.Mes_Full_Mes(sampling=100, acquisition_time=3)"
						pyb_mes.exec_raw_no_follow(comm_mesure)
						#On démarre l'acquision de X sec
						#on ferme la vanne et on enclanche une tempo de 500 msec pui on l'ouvre et on fait les mesure dans la fonction Mesures_Full

						sig,Vect_time = record(filename=filename)


						time.sleep(2)
						pyb_mes.follow(timeout=5)
						comm_grab ="print(mes.Grab_Full_Mes())"
						Mes_bytes_unformatted = pyb_mes.exec(comm_grab)
						Mes_bytes = eval(str(Mes_bytes_unformatted, "ascii"))

						Mes_Press =np.frombuffer(Mes_bytes, dtype=np.float32)
						Mes_Press=Mes_Press.reshape(6,int(Mes_Press.size/6))

						m_press = Mes_Press[0:2,:].shape[1]
						m_temp = Mes_Press[2:4,:].shape[1]
						m_debit = Mes_Press[4:6,:].shape[1]


						Acous = np.array([Vect_time,sig[:,0]])
						m_acou  =  Acous[4:6,:].shape[1]

						#on rentres les valeurs dans le dataset
						if m_press > Mesures_Press.shape[5] :
 							Mesures_Press.resize((2,Decoupe_Clapet,Decoupe_Sections, Decoupe_Pressions,Decoupe_Clapet,2,m_press))
 							print("Mesures_Press reshaped")

						if m_temp > MesuresTemperature.shape[5]:
							MesuresTemperature.resize((2,Decoupe_Clapet,Decoupe_Sections, Decoupe_Pressions,Decoupe_Clapet,2,m_temp))
							print("MesuresTemperature reshaped")
						if m_debit > Mesures_Debit.shape[5]:
							Mesures_Debit.resize((2,Decoupe_Clapet,Decoupe_Sections, Decoupe_Pressions,Decoupe_Clapet,2,m_debit))
							print("Mesures_Debit reshaped")
						if nbchannels ==2 :
							Accel=np.array([Vect_time,sig[:,1]])
							m_accel = Accel[:,:].shape[1]
							Mesures_Accelerations[P_pos, S_plus, P_plus,i_Clap , 0:2, 0:m_accel]= Accel #L est l'accéléromètre
							if m_accel > Mesures_Accelerations.shape[5] :
								Mesures_Accelerations.resize((2,Decoupe_Clapet,Decoupe_Sections, Decoupe_Pressions,Decoupe_Clapet,2,m_accel))
								print("Mesures_Accelerations reshaped")
						if m_acou > Mesures_Press_Acoustique.shape[5] :
							Mesures_Press_Acoustique.resize((2,Decoupe_Clapet,Decoupe_Sections, Decoupe_Pressions,Decoupe_Clapet,2,m_acou))
							print("Mesures_Press_Acoustique reshaped")


						# Create a temporary variable with zeros values
						# size (2, 6, 6, 2, #numsamples)
						# Assign the values.
						Mesures_Press[P_pos, S_plus, P_plus,i_Clap, 0:2, 0:m_press] = Mes_Press[0:2,:]  # here there is a pbl when the loop id_CrossSection goes +1, the previous datas are replaced by news ones
						#print(shape(temp[id_Pressure_Positive, id_CrossSection, id_Pressure,i_Clap 0:2, 0:m]))
						# Now append to the main array
						MesuresTemperature[P_pos, S_plus, P_plus ,i_Clap, 0:2, 0:m_temp]=Mes_Press[2:4,:]
						Mesures_Debit[P_pos, S_plus, P_plus,i_Clap, 0:2, 0:m_debit]=Mes_Press[4:6,:]
						Mesures_Press_Pos[P_pos, S_plus, P_plus,i_Clap ]=float(LargeurTrouSection*(S_plus/(Decoupe_Sections-1))*(Deplacement_maxi_screw_S_mm-Deplacement_mini_screw_S_mm)) #screw pos * largeur section
						Calculs_Surf[P_pos, S_plus, P_plus, i_Clap ] = Surf               #5 in mm²
						Mesures_Press_Acoustique[P_pos, S_plus, P_plus,i_Clap , 0:2, 0:m_acou]= Acous  #R est le microphone



		plt.plot(Mesures_Press_Acoustique[0][0][0][0][0],Mesures_Press_Acoustique[0][0][0][0][1]) # du type mat[pression_pos][Pos_section][Val_Pression][i_Clap ][data,temps]


except Exception as e:
	exc_type, exc_obj, exc_tb = sys.exc_info()
	shutdown_restore =1
	np.save(path +'val_shutdownrestore.npy', [P_pos, P_plus, S_plus, i_Clap])

	fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
	print("Error :",fname, exc_tb.tb_lineno,e)
	pass

pyb_control.exec("control.Set_Press(00)")
pyb_mes.exit_raw_repl()
pyb_mes.close()
pyb_control.exit_raw_repl()
pyb_control.close()

# close stream
stream.stop_stream()
stream.close()
p.terminate()


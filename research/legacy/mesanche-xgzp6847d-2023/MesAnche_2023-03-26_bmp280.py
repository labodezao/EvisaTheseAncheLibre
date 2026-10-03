from pyb import DAC
from step import Stepper
import utime
from bmp280 import *
from sfm3000 import SFM3000
import machine
import sys
import json
import math , time , array , gc
from ulab import numpy as np

class MesAnches():
    
    def __init__(self):
        #Acuators
        self.PRESS_STEP = machine.Pin('X1', machine.Pin.OUT)
        self.PRESS_DIR = machine.Pin('X2', machine.Pin.OUT)
        self.SCREW_STEP = machine.Pin('X3', machine.Pin.OUT)
        self.SCREW_DIR = machine.Pin('X4', machine.Pin.OUT)
        self.SLEEP_STEP=machine.Pin('X21', machine.Pin.OUT)
        self.DAC_BLOW = DAC(1, bits=12)   # use 12 bit resolution # limit switch on, X5
        self.BLOW_EN = machine.Pin('X7', machine.Pin.OUT) # limit switch
        self.VANNE_EN = machine.Pin('X19', machine.Pin.OUT) # limit switch
        self.CLAMP = machine.Pin('X20', machine.Pin.OUT) # limit switch
        self.BLOW_EN.high()
        self.PressPositive = True
        self.VANNE_EN.high() #Vanne ouverte
        self.SW1 = machine.Pin('X12', machine.Pin.IN) # limit switch
        self.SW2 = machine.Pin('X11', machine.Pin.IN, pull=machine.Pin.PULL_UP) # limit switch
        self.bus=machine.SoftI2C(scl=machine.Pin('Y9'), sda=machine.Pin('Y10'),freq=400000,timeout=450)
        
        
        #steppers and positions init
        self.step_press = Stepper(self.PRESS_STEP, self.PRESS_DIR, self.SLEEP_STEP )
        self.step_screw = Stepper(self.SCREW_STEP, self.SCREW_DIR,self.SLEEP_STEP)

        self.Posi_Press_init()
        self.Posi_Screw_init()
        
        #I2c init
        self.n_act_meas = 0
        self.n_exp_meas = 0
        self.acquisition_time =0
        #sensors
        #try:
        self.bmp280 = BMP280(self.bus)
        self.sfm3000 = SFM3000(self.bus)
            
        #except (RuntimeError, TypeError, NameError, OSError):
        #    pass
        self.InitP0()

    # Fonctions
    def InitP0(self):
        self.VANNE_EN.high()#Vanne fermée
        self.BLOW_EN.low()
        utime.sleep_ms(1000)
        self.p0= self.bmp280.pressure
        self.BLOW_EN.high()
        self.VANNE_EN.low()#Vanne ouverte
        
    def Get_PressPositive(self) -> None:
        """On initialise le stepper pour une pression positive """
        return self.PressPositive
    
    def Tempo_Vanne(self,time) -> None:
        """On initialise le stepper pour une pression positive """
        self.VANNE_EN.high()#Vanne fermée
        utime.sleep_ms(time*1000)
        self.VANNE_EN.low()#Vanne ouverte 
    
    def Posi_Press_init(self) -> None:
        """On initialise le stepper pour une pression positive """
        self.step_press.steps(-300,1000)

        while self.SW1.value() :
            self.step_press.steps(20,1000)
            
        self.PressPositive = 1
         
    def Posi_Screw_init(self) -> None:
        """On initialise le stepper pour une pression positive """
        self.step_screw.steps(-300,1000)

        while self.SW2.value() :
            self.step_screw.steps(20,1000)
            
        self.xpos = 0

    def Mes_Full_Mes(self,sampling=100, acquisition_time=3) -> None:
        """Mesure de la pression température et remplissage d'un array de valeurs"""
        #sampling max 150 Hz
        # set up
        self.acquisition_time = acquisition_time
        self.n_exp_meas = math.floor(acquisition_time * math.ceil(sampling)) 
        self.results=np.zeros(( 6 , self.n_exp_meas+1), dtype=np.float)
        np.ndinfo(self.results)
        n_act_meas = 0
        
        # read bytes as fast as possible
        start = time.ticks_us()
        while time.ticks_diff(time.ticks_us(), start) < acquisition_time * 1000000:
          curr_time = time.ticks_us()
          if time.ticks_diff(curr_time, start) < (n_act_meas * 1000000. / sampling):
            continue
          # read sensor 1
          self.results[0,n_act_meas] = time.ticks_diff(curr_time, start)/1000000
          # grab the time of the measure 1
          self.results[1,n_act_meas] = self.bmp280.pressure
          # read sensor 2
          self.results[2,n_act_meas] = time.ticks_diff(curr_time, start)/1000000
          # grab the time of the measure 2
          self.results[3,n_act_meas] = self.bmp280.temperature
          # read sensor 3
          self.results[4,n_act_meas] = time.ticks_diff(curr_time, start)/1000000
          # grab the time of the measure 3
          self.results[5,n_act_meas] = self.sfm3000.Mes_flow()
          
          n_act_meas += 1
        
        #print (self.results)
        self.n_act_meas =n_act_meas
        # bytes --> lists of integers
        # remove exceeding zeros
        #results = results[:,:n_act_meas]
        #file = open('mes_all.csv','wb')
        #file.write(self.results.tobytes())
        #file.close()

    
    def Grab_Full_Mes(self) -> None:
        """Mesure de la pression température et remplissage d'un array de valeurs"""
        #print("measured samples: ", self.n_act_meas)
        #print("expected samples: ", self.n_exp_meas)
        #print("actual sampling rate: ", self.n_act_meas / self.acquisition_time)
        #return self.results.tobytes()
        return self.results.tobytes()
    

    def Mes_Press(self) -> None:
        """Mesure de la pression a l'aide du BMP380"""
        
        return self.bmp280.pressure
    
    def Mes_Temp(self) -> None:
        """Mesure de la pression a l'aide du BMP380"""
        
        return self.bmp280.temperature

    def Mes_Debit(self) -> float:
        """Mesure du débit du SFM3000"""
         
        return self.sfm3000.Mes_flow()
       
       
    def Calc_Surf(self) -> float:
        """Calcule la Surface en mm² en fonction de la position x"""
        S = float(abs(self.xpos)*15)
        return S
    
    
    def Move_mm(self, xmove: int, speed=500) -> None:
         """bouge la vis de X mm"""
         self.step_screw.Move_mm(-xmove , speed )
         self.xpos = self.xpos + xmove
        
    def Move_to_Pos(self, moveto: int, speed=500) -> None:
         """bouge la vis de X mm"""        
         self.Move_mm(int((moveto-self.xpos)),speed)

    def InvPress(self, Surpess: bool) -> None:
        """bouge la vis de X mm"""
        if self.SW2.value():
                if self.PressPos == 1:
                    self.stepper.steps(-1600,2600)
                    self.PressPos = not self.PressPos
                else :
                    self.stepper.steps(+1600,2600)
                    self.PressPos = not self.PressPos
     

    def Set_Press(self, Press: int) -> None:
       """Envoie % de pression d'air 0 -4095"""
       self.DAC_BLOW.write(Press)
        
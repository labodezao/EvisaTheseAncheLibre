from pyb import DAC,ADC
from step import Stepper
import utime
import machine
import sys
import math
from ulab import numpy as np
import uasyncio as asyncio

class ValControl():
    
    def __init__(self):
        #Acuators
        self.DAC_BLOW = DAC(1, bits=12)   # X5 use 12 bit resolution # limit switch on
        self.ADC_BLOW = ADC(machine.Pin('X6', machine.Pin.OUT))
        self.VALVE_STEP = machine.Pin('X7', machine.Pin.OUT)
        self.VALVE_DIR = machine.Pin('X8', machine.Pin.OUT)
        self.VALVE_SLEEP = machine.Pin('X9', machine.Pin.OUT)
        self.VANNE_EN = machine.Pin('X19', machine.Pin.OUT) # limit switch
        self.VANNE_EN.high() # Vanne ouverte
        self.SW1 = machine.Pin('X12', machine.Pin.IN) # limit switch for valve
        self.step_per_rev = 1600
        #steppers and positions init
        self.step_valve = Stepper(self.VALVE_STEP, self.VALVE_DIR, self.VALVE_SLEEP,  self.step_per_rev  )
        self.Posi_Valve_init()
        
    # Fonctions
        
    def Vanne_Open(self) -> None:
        """On initialise le stepper pour une pression positive """
        self.VANNE_EN.low()#Vanne ouverte
    
    
    def Posi_Valve_init(self) -> None:
        """On initialise le stepper pour une pression positive """
        self.step_valve.steps(300,1000)

        while self.SW1.value() :
            self.step_valve.steps(-20,1000)
        self.xpos = 0
         
    def Move_to_angle(self, moveto: int, speed=500,tempo_ms=100) -> None:
         """bouge la vis de X mm"""
         utime.sleep_ms(tempo_ms)
         self.step_valve.rel_angle(int((moveto-self.xpos)),speed)
         self.xpos += int((moveto-self.xpos))
         
    def Move_Trills(self, nb_ar: int, angle: int , speed=500) -> None:
         """bouge la vis de X mm"""
         for i in range(abs(nb_ar)):
            self.Move_to_angle(angle,speed)
            self.Move_to_angle(-angle,speed)
         self.current_position += step_count   

         self.step_valve.rel_angle(int((moveto-self.xpos)),speed)
        
    def Set_Press(self, Press: int) -> None:
       """Envoie % de pression d'air 0 -4095"""
       self.DAC_BLOW.write(Press)

from pyb import DAC
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
        self.uart = machine.UART(4, 9600) # X1, X2
        self.VALVE_STEP = machine.Pin('X3', machine.Pin.OUT)
        self.VALVE_DIR = machine.Pin('X4', machine.Pin.OUT)
        self.VALVE_SLEEP = machine.Pin('X5', machine.Pin.OUT)
        self.VANNE_EN = machine.Pin('X19', machine.Pin.OUT) # limit switch
        self.VANNE_EN.high() # Vanne ouverte
        self.SW1 = machine.Pin('X12', machine.Pin.IN) # limit switch for valve
        self.step_per_rev = 1600
        #steppers and positions init
        self.step_valve = Stepper(self.VALVE_STEP, self.VALVE_DIR, self.VALVE_SLEEP,  self.step_per_rev  )
        self.Posi_Valve_init()
        
    # Fonctions
    async def Tempo_Vanne(self,time=500) -> None:
        """On initialise le stepper pour une pression positive """
        if VANNE_EN == 0 :
            self.VANNE_EN.high()#Vanne fermée
        await asyncio.sleep_ms(time)
        self.VANNE_EN.low()#Vanne ouverte
    
    def Vanne_Close(self) -> None:
        """On ferme la vanne"""
        self.VANNE_EN.high()#Vanne fermée
    
    def Vanne_Open(self) -> None:
        """On ouvre la vanne """
        self.VANNE_EN.low()#Vanne fermée
    
    def Posi_Valve_init(self) -> None:
        """On initialise le stepper pour une pression positive """
        self.step_valve.steps(-300,1000)

        while self.SW1.value() :
            self.step_valve.steps(20,1000)
            
        self.xpos = 0
         
    async def Move_to_angle(self, moveto: int, speed=500,tempo=500) -> None:
         """bouge la vis de X mm"""
         sleep_ms(tempo)
         self.step_valve.rel_angle(int((moveto-self.xpos)),speed)
         self.xpos += int((moveto-self.xpos))
         
    def Move_Trills(self, nb_ar: int, angle: int , speed=500) -> None:
         """bouge la vis de X mm"""
        for i in range(abs(nb_ar)):
            self.Move_to_angle(angle,speed)
            self.Move_to_angle(-angle,speed)
        self.current_position += step_count   

         self.step_valve.rel_angle(int((moveto-self.xpos)),speed)
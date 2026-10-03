import machine
import utime
import ustruct



class SDP810500():
    def __init__(self,bus):
        self.bus=bus
        self.scale_press = 60 # Scale factor for pressure in Air
        self.scale_temp = 200 # Scale factor for temps in Air
        self.buf = bytearray([0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00])
        self.EN_Mes()
        
        
        
    def EN_Mes(self):
        # send 0x0006 to soft reset sensor and wait 1 sec
        re = bytearray([0x3F,0xF9])
        self.bus.writeto(0x26,re)
        utime.sleep(0.2)

        #Initialize Sensor send 0x1000 to sensor to start continuous measurement
        ##Command code (Hex)        Temperature compensation            Averaging
        ##0x3603                    Mass flow                           Average  till read
        ##0x3608                    Mass flow None                      Update rate 0.5ms
        ##0x3615                    Differential pressure               Average till read
        ##0x361E                    Differential pressure None          Update rate 0.5ms
        
        start = bytearray([0x36,0x15])
        self.bus.writeto(0x26,start)
        utime.sleep(0.9) 
        self.buf=self.bus.readfrom(0x26,9)
        self.scale_press= ustruct.unpack(">h",bytearray([self.buf[6],self.buf[7]]) )[0]
        print(self.scale_press)
        
        
    def Mes_DPress(self) :
               
        #start measurements
        self.buf=self.bus.readfrom(0x26,9)
        #take the first 2 bytes of measurements
        pressure_value=ustruct.unpack(">h",self.buf[0:2] )[0]
        #calculate flow
        d_pres= pressure_value /self.scale_press
        utime.sleep(0.1)
        return d_pres


    def Mes_Temp(self) :
        
        #start measurements
        self.buf=self.bus.readfrom(0x26,9)
        #take the first 2 bytes of measurements
        t_value=ustruct.unpack(">h",self.buf[3:5] )[0]
        #calculate flow
        temp= t_value /self.scale_temp
        utime.sleep(0.1)
        return temp
    

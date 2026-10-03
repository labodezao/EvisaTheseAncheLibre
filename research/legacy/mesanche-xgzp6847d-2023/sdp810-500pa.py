import machine
import utime


class sdp810500():
    def __init__(self,bus):
        self.bus=bus
        self.scale_press = 60 # Scale factor for pressure in Air
        self.scale_temp = 200 # Scale factor for temps in Air
        self.EN_Mes()
        
        
    def EN_Mes(self):
        # send 0x0006 to soft reset sensor and wait 1 sec
        re = bytearray([0x00,0x06])
        self.bus.writeto(0x26,re)
        utime.sleep(1)

        #Initialize Sensor send 0x1000 to sensor to start continuous measurement
        ##Command code (Hex)        Temperature compensation            Averaging
        ##0x3603                    Mass flow                           Average  till read
        ##0x3608                    Mass flow None                      Update rate 0.5ms
        ##0x3615                    Differential pressure               Average till read
        ##0x361E                    Differential pressure None          Update rate 0.5ms
        
        start = bytearray([0x36,0x03])
        self.bus.writeto(0x26,start)
        utime.sleep(0.2)
        scales_buf = self.bus.readfrom(0x26,9)
        self.scale_press=int.from_bytes(buf[7:8], 'big')
        
        
    def Mes_DPress(self) :
               
        #start measurements
        buf = self.bus.readfrom(0x26,9)
        #take the first 2 bytes of measurements
        pressure_value=int.from_bytes(buf[0:1], 'big')
        #calculate flow
        d_pres= pressure_value /self.scale_press  
        return d_pres


    def Mes_Temp(self) :
        
        #start measurements
        buf = self.bus.readfrom(0x26,9)
        #take the first 2 bytes of measurements
        pressure_value=int.from_bytes(buf[3:4], 'big')
        #calculate flow
        temp= pressure_value /self.scale_press  
        return temp
    

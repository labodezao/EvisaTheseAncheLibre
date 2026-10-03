import machine
import utime
import ustruct

class XGZP6847D():
    def __init__(self,bus):
        self.bus=bus
        self.buf = bytearray([0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00])
        self.scale_press = 64 # Scale factor -1...10 bars datasheet p9
        self.temp = 0;
        
        self.EN_Mes()
        
        
    def EN_Mes(self):
        # send 0x0A to 0x30 adress to  enable measurement
        utime.sleep(0.3)
        self.bus.writeto(0x30, 0x0A)
        utime.sleep(0.1)
        
    def Mes_Read(self) :
        
        #start measurements
        buf = self.bus.readfrom_mem(0x30, 0x06, 5)
        #take the first 2 bytes of measurements
    
        pressure_value=ustruct.unpack(">h",self.buf[0:3] )[0]
        self.d_pres= pressure_value /self.scale_press
        t_value=ustruct.unpack(">h",self.buf[3:5] )[0]
        temp= t_value /self.scale_temp        
        utime.sleep(0.1)
        
        return self.d_pres
    
    def Get_DPress(self) :
        
        Mes_Read()
        return self.d_pres
    
    def Get_Temp(self) :
        
        Mes_Read()
        return self.d_pres


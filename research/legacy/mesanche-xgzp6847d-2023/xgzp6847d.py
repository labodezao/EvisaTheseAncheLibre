import machine
import utime
import ustruct
import statistics

class XGZP6847D():
    def __init__(self,bus):
        self.bus=bus
        self.buf_press = bytearray([0x00,0x00,0x00])
        self.buf_temp = bytearray([0x00,0x00])
        self.scale_press = 1024 # Scale factor -1...10 bars datasheet p9
        self.temp = 0;
        self.d_press =0;
        self.press_offset =0;
        self.EN_Mes()
        self.Calc_off()
        
    def EN_Mes(self):
        # send 0x0A to 0x30 adress to  enable measurement
        self.bus.start()
        utime.sleep(0.2)
        print('0x30 initial params' ,hex(self.bus.readfrom_mem(0x6d,0x30, 1)[0]))
        print('0xA5 initial params' ,hex(self.bus.readfrom_mem(0x6d,0xA5, 1)[0]))
        print('0xA6 initial params' ,hex(self.bus.readfrom_mem(0x6d,0xA6, 1)[0]))
        self.bus.writeto_mem(0x6d,0x30, bytearray([0x0A]))
        #self.bus.writeto_mem(0x6d,0xA5, bytearray([0x10]))
        self.bus.writeto_mem(0x6d,0xA6, bytearray([0x2B]))
        #print('0x30 new params' ,hex(self.bus.readfrom_mem(0x6d,0x30, 1)[0]))
        #print('0xA5 new params' ,hex(self.bus.readfrom_mem(0x6d,0xA5, 1)[0]))
        #print('0xA6 new params' ,hex(self.bus.readfrom_mem(0x6d,0xA6, 1)[0]))
    
            
    def Calc_off(self) :
        Tab_zeros=[0]*80
        for x in range(80):
            utime.sleep(0.01)
            Tab_zeros[x]=self.Get_DPress()
            
        self.press_offset= statistics.mean(Tab_zeros)
        print("mean",self.press_offset)    
    
        
    def Mes_Read(self) :
        number =0
        #start measurements
        self.bus.writeto_mem(0x6d,0x30, bytearray([0x0A]))
        #utime.sleep(0.001)
        while (( self.bus.readfrom_mem(0x6d,0x30, 1)[0] & 0x08)> 0) :
            utime.sleep(0.1)
        self.buf_press = self.bus.readfrom_mem(0x6d, 0x06, 3)
        self.buf_temp = self.bus.readfrom_mem(0x6d, 0x09, 2)
        #take the first 2 bytes of measurements
        pressure_adc = int(self.buf_press[0]) * 65536 + int(self.buf_press[1]) * 256 + int(self.buf_press[2]);
        #Compute the value of pressure converted by ADC
        if (pressure_adc > 8388607):
            pressure = (pressure_adc - 16777216) / self.scale_press
        else:
            pressure = pressure_adc / self.scale_press
            
        self.d_press= pressure
        t_value=(int(self.buf_temp[0])*256+self.buf_temp[1])/256
        self.temp= t_value      
                
        
    
    def Get_DPress(self) :
        
        self.Mes_Read()
        return self.d_press
    
    def Get_Temp(self) :
        
        self.Mes_Read()
        return self.temp
    
    def Get_system_config(self) :
        
    
        return self.bus.readfrom_mem(0x6d, 0xA5, 1)


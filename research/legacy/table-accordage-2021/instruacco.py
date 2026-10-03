import utime
import machine
import ssd1306
from nanogui import Label, Meter, refresh
import uasyncio
from xgzp6847d import XGZP6847D

bus=machine.SoftI2C(scl=machine.Pin('X9'), sda=machine.Pin('X10'),freq=400000)

# Fonts
import courier20 as fixed
import font6 as small
import arial10 
ssd = setup(False, True)  # Create a display instance
import sys


class TableAccordage():
    
    def __init__(self):
        #Acuators
        self.IN1 = machine.Pin('X1', machine.Pin.OUT)
        self.IN2 = machine.Pin('X2', machine.Pin.OUT)
        self.IN3 = machine.Pin('X3', machine.Pin.OUT)
        self.IN4 = machine.Pin('X4', machine.Pin.OUT)
        self.IN5 = machine.Pin('X5', machine.Pin.OUT)
        self.IN6 = machine.Pin('X6', machine.Pin.OUT)
        self.BLOW = machine.Pin('X4', machine.Pin.OUT) # limit switch
        self.VANNE = machine.Pin('X19', machine.Pin.OUT) # limit switch
        self.CLAMP = machine.Pin('X20', machine.Pin.OUT) # limit switch
        self.BLOW.high()
        self.PressPos = True
        self.VANNE.high() #Vanne ouverte
        self.SW1 = machine.Pin('X11', machine.Pin.IN) # limit switch
        self.SW2 = machine.Pin('X12', machine.Pin.IN, pull=machine.Pin.PULL_UP) # limit switch

        #print(self.SW2.value())
        self.stepper = Stepper(self.IN1, self.IN2, self.IN3)

        self.stepper.steps(-300,1000)

        while self.SW1.value() :
            self.stepper.steps(20,1000)

        self.PressPos = 1
        

        self.bus=machine.I2C(scl=machine.Pin('Y9'), sda=machine.Pin('Y10'))
        #sensors
        self.bmp = BMP280(self.bus)
        #tca.switch_channel(1)
        self.sfm3000 = SFM3000(self.bus)
        self.p0 = self.bmp.pressure
        uasyncio.run(self.main())
        self.InitP0()
        #print(self.sfm3000.Mes_flow())

        
        
     
        
    async def screen(self):
        
        Writer.set_textpos(ssd, 0, 0)  # In case previous tests have altered it
        wri = Writer(ssd, small, verbose=False)
        wri.set_clip(False, False, False)

        nfields = []
        dy = small.height() + 6
        y = 2
        col = 50
        width = wri.stringlen('990.99')
        for txt in ('Press:', 'Y:', 'Z:'):
            nfields.append(Label(wri, y, col, width, bdcolor=None))  # Draw border
            y += dy
        await uasyncio.sleep_ms(100)      
    
        while True :
            Label(wri, 2, 2, ' Press ', True)
            Label(wri, 22, 2, ' Flow   ', True)
            Label(wri, 42, 2, ' Temp ', True)
            i=0    
            for field in nfields:
                value = (self.bmp.pressure-self.p0,self.sfm3000.Mes_flow(),self.bmp.temperature)
                #print(value[i]) # print sensors values
                field.value('{:5.2f}'.format(value[i]))
                i=i+1
            refresh(ssd)
            await uasyncio.sleep_ms(100)
     
    async def InitP0(self):
        self.VANNE.low()#Vanne fermÃ©e
        self.BLOW.low()
        await uasyncio.sleep_ms(2000)
        self.p0= self.bmp.pressure
        self.BLOW.high()
        self.VANNE.high()#Vanne fermÃ©e
     
    async def InvPress(self):
        await uasyncio.sleep_ms(1000)
        #print('Sw2',self.SW2.value())
        while True:
            #print(self.SW2.value())
            if self.SW2.value():
                if self.PressPos == 1:
                    self.stepper.steps(-1600,2600)
                    self.PressPos = not self.PressPos
                else :
                    self.stepper.steps(+1600,2600)
                    self.PressPos = not self.PressPos
            await uasyncio.sleep_ms(120)

    def _handle_exception(self,loop, context):
        print('Global handler')
        sys.print_exception(context["exception"])
        #loop.stop()
        sys.exit()  # Drastic - loop.stop() does not work when used this way
    
    
    async def main(self):
        #self.loop = uasyncio.get_event_loop()
        #self.loop.set_exception_handler(self._handle_exception)
        uasyncio.create_task(self.InvPress())
        uasyncio.create_task(self.screen())       
        while True:
            await uasyncio.sleep(1000)
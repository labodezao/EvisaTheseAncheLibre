from machine import Pin, SoftI2C 
import utime
from xgzp6847d import XGZP6847D


bus=SoftI2C(scl=Pin('Y9'), sda=Pin('Y10'),freq=400000)

xgzp6847d = XGZP6847D(bus)


while True :
    print(round(xgzp6847d.Get_DPress(),2) )
    #utime.sleep(0.01)
    #https://courspython.com/derivee-fonction.html
    
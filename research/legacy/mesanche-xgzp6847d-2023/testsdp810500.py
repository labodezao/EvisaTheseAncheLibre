import machine
from sdp810500 import SDP810500

bus=machine.SoftI2C(scl=machine.Pin('Y9'), sda=machine.Pin('Y10'),freq=400000)
sdp810 = SDP810500(bus)
while True :
    print(sdp810.Mes_DPress())
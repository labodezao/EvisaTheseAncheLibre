from valvecontrol import *

val = ValControl()

val.Move_to_angle(32,500)
utime.sleep_ms(1000)
val.Move_to_angle(2,500)
utime.sleep_ms(1000)
val.Move_to_angle(20,500)
utime.sleep_ms(1000)
val.Move_to_angle(5,500)
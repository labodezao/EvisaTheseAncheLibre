from MesAnche import *

mes = MesAnches()
#mes.Move_mm(1,500)


mes.Mes_Full_Mes(sampling=200, acquisition_time=3)
print(mes.Grab_Full_Mes())

#mes.Posi_Press_init()

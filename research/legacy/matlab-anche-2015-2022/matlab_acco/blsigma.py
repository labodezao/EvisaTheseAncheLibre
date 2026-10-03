from sympy import *

def bl_sigma(n):
        BL={            
                1:1.87510407 ,
                2:4.69409113 ,
                3:7.85475744  ,
                4:10.99554073,
                5:14.13716839 
             }
        Sigma={
                1:0.7341 ,
                2:1.0185 ,
                3:0.9992 ,
                4:1
             }
        return BL.get(n,(2*n-1)*pi/2), Sigma.get(n,1)
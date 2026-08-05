from sympy.abc import *
from sympy import *
from numpy import dot
import numpy as np
from scipy import linalg

def BL_Sigma(n): 
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
    
def km()   : 
    
    
 # du type Longeur, densité, largeur,epaisseur, Young modulus
 Properties_mat = Matrix(np.loadtxt('matrix.txt', delimiter=','))
 
 
 print(Properties_mat)
 
 NDDL=2
 L=sum(Properties_mat.col(0))

 M=zeros(NDDL)
 K=zeros(NDDL)

 nsection,nparam=Properties_mat.shape
 #print (nsection,nparam)
 #print(L)


 for i in range(1, NDDL+1):
        Bi,Si=BL_Sigma(i)
        for j in range(1, NDDL+1):
            Bj,Sj=BL_Sigma(j)
            M_ij=0
            K_ij=0
            xn=0
            xnp1=Properties_mat[0,0]
            for k in range(1,nsection+1):
                if k > 1:
                    xn=xnp1
                    xnp1=xnp1 + Properties_mat[k-1,0]
                ## Calcul des coefficients de matrices
                print(i,j,k)
                kij=integrate( diff(cosh(Bi/L*x)-cos(Bi/L*x)-Si*(sinh(Bi/L*x)-sin(Bi/L*x)),x,2)*diff(cosh(Bj/L*x)-cos(Bj/L*x)-Sj*(sinh(Bj/L*x)-sin(Bj/L*x)),x,2)   , (x,xn , xnp1))
                mij=integrate( (cosh(Bi/L*x)-cos(Bi/L*x)-Si*(sinh(Bi/L*x)-sin(Bi/L*x)))*(cosh(Bj/L*x)-cos(Bj/L*x)-Sj*(sinh(Bj/L*x)-sin(Bj/L*x)))   , (x,xn , xnp1))
                K_ij=K_ij + dot(dot(dot(kij,Properties_mat[k-1,4]),Properties_mat[k-1,2]),Properties_mat[k-1,3] ** 3) / 12
                M_ij=M_ij + dot(dot(dot(mij,Properties_mat[k-1,1]),Properties_mat[k-1,2]),Properties_mat[k-1,3])
            M[i-1,j-1]=M_ij
            K[i-1,j-1]=K_ij
          
 Mp=np.array(M).astype(np.float64)
 Kp=np.array(K).astype(np.float64)
        
 w,vr=linalg.eig(Kp,Mp)
 Freq= np.real(np.sqrt(w)/(2*3.141592653589793238462643383279))
 print (Freq)


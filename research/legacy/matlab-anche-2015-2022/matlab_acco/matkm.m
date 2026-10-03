function [Mp,Kp] = matkm( Properties_mat: Matrix)

syms x ;

Properties_mat =  [ 4.550*10^-3 , 7800 , 4.259*10^-3 , 0.35*10^-3 , 2.1*10^11 ;
					14.850*10^-3 , 7800 , 4.008*10^-3 , 0.2*10^-3 , 2.1*10^11 ;
					9*10^-3 , 7800 , 3.699*10^-3 , 0.275*10^-3 , 2.1*10^11 ;
					9*10^-3 , 7800 , 3.466*10^-3 , 1.5*10^-3 , 2.1*10^11 ] ; 
Properties_mat =  [ 5*10^-3 , 7800 , 4*10^-3 , 0.5*10^-3 , 2.1*10^11 ;
				    5*10^-3 , 7800 , 4*10^-3 , 0.5*10^-3 , 2.1*10^11 ;
					5*10^-3 , 7800 , 4*10^-3 , 0.5*10^-3 , 2.1*10^11 ] ; 

% du type [x0 (longeur tron�on ),rho0 (densit� moyenne du troncon) ,b0 (largeur -constante- de l'anche) ,h0 (Epaisseur) ,E0 (Module Young)  ;  xi,rhoi,bi,hi,Ei  ;  xn,rhon,bn,hn,En] 
% Note :
% Rem  :

NDDL=1;
L  =  sum(Properties_mat(:,1));


M=zeros(NDDL);
K=zeros(NDDL);
[nsection,nparam] = size(Properties_mat) ;
for i= [1: NDDL];
   [Bi,Si] = BL_Sigma(i) ; 
   
   for j= [1 : NDDL] ;
 [Bj,Sj] = BL_Sigma(j) ; 
  M_ij=0;
  K_ij=0;
  xn = 0;
  xnp1=  Properties_mat(1,1);
  
  for k=1:nsection  
if k>1
 xn = xnp1;
xnp1= xnp1 + Properties_mat(k,1);
end


%% Calcul des coefficients de matrices

kij = int( diff(cosh(Bi/L*x)-cos(Bi/L*x)-Si*(sinh(Bi/L*x)-sin(Bi/L*x)),2)*diff(cosh(Bj/L*x)-cos(Bj/L*x)-Sj*(sinh(Bj/L*x)-sin(Bj/L*x)),2)   , xn , xnp1)  ;
mij = int((cosh(Bi/L*x)-cos(Bi/L*x)-Si*(sinh(Bi/L*x)-sin(Bi/L*x)))*(cosh(Bj/L*x)-cos(Bj/L*x)-Sj*(sinh(Bj/L*x)-sin(Bj/L*x))) , xn , xnp1 );
K_ij = K_ij + kij*Properties_mat(k,5)*Properties_mat(k,3)*Properties_mat(k,4)^3/12;
M_ij = M_ij + mij*Properties_mat(k,2)*Properties_mat(k,3)*Properties_mat(k,4);
%Mtest=double(int( (cosh(Bi/L*x)-cos(Bi/L*x)-Si*(sinh(Bi/L*x)-sin(Bi/L*x)))*(cosh(Bj/L*x)-cos(Bj/L*x)-Sj*(sinh(Bj/L*x)-sin(Bj/L*x))) , 0 , L) )*Properties_mat(k,2)*Properties_mat(k,3)*Properties_mat(k,4) 
%Ktest=double(int( diff(cosh(Bi/L*x)-cos(Bi/L*x)-Si*(sinh(Bi/L*x)-sin(Bi/L*x)),x,2)*diff(cosh(Bj/L*x)-cos(Bj/L*x)-Sj*(sinh(Bj/L*x)-sin(Bj/L*x)),x,2)  , 0 , L) )*Properties_mat(k,5)*Properties_mat(k,3)*Properties_mat(k,4)^3/12
  end

M(i,j) = M_ij;
K(i,j)= K_ij;
 end


end


Val = eig(K,M) 

Freq= sqrt(Val)./(2*pi)
end








function [Bl,sigma] = BL_Sigma(n)
%/ n            : numero du mode ;
%// x      		: [Parametre de la fonction : position longitudinale ou on recheche la déformée modale]
%// Offset 		: [valeur de l'offset du à la déformée statique en x]
%// Bl     		: [Longeur de l'anche : Variable Externe]
%// sigma 	 	: [Longeur de l'anche : Variable Externe]
%// Long_Anche 	: [Longeur de l'anche : Variable Externe]
%// f 			: [variable de sortie de la fonction : donne la valeur de la déformée modale en un point x]
%//----------------------------------------------------------------------------------------------------------

if n < 6

switch n
    case 1
Bl              = 1.87510407                                     			;%// Coefficient Bl pour calculer les deformée modales
sigma			 = 0.7341                                         			;%// Coefficient sigma pour calculer les deformée modales

case 2 
 
 Bl              = 4.69409113                                     			;%// Coefficient Bl pour calculer les deformée modales
sigma			 = 1.0185                                         			;%// Coefficient sigma pour calculer les deformée modales

case 3 
Bl               = 7.85475744                                     			;%// Coefficient Bl pour calculer les deformée modales
sigma			 = 0.9992                                         			;%// Coefficient sigma pour calculer les deformée modales

 
case 4 
 Bl               = 10.99554073                                     			;%// Coefficient Bl pour calculer les deformée modales
sigma			 = 1                                         			;%// Coefficient sigma pour calculer les deformée modales

case 5 
Bl               = 14.13716839                                     			;%// Coefficient Bl pour calculer les deformée modales
sigma			 = 1                                         			;%// Coefficient sigma pour calculer les deformée modales


end
else
Bl               =   (2*n-1)*pi/2                                  			;%// Coefficient Bl pour calculer les deformée modales
sigma			=    1                                             			;%// Coefficient sigma pour calculer les deformée modales



end

      
end




function  [Omega_n ]= Pulsa_nat(n) 

[Bl,~]=BL_Sigma(n);
E=B*h^3/12;
Omega_n =(Bl)^2*(E*I/(Roh*A*L^4))^0.5 ;


end

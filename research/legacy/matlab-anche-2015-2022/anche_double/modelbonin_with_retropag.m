function modelbonin_with_retropag
clear all
close all
clc

global Pbouchen x0 x_seuil Kp Roh_Air Lar_Anche gammacv P_Anchen Beta Surf_Anche Section_Cuivret Vn Debit_entree tnm1 P0 Fn TimeVP

%% Variables
x0                      = 1*10^-3 ;%demi espace entre les plaquettes de l'anche
x_seuil                 = x0/2       ; %
Roh_Anche               = 770        ; %
Distance_Bout_Fil       = 11*10^-3   ; %
rLt_Lvib                  = 0.4        ; %rapport longeur vibrante / longueur totale
Epaisseur_Roseau        = 0.5*10^-3  ; %
Lar_Anche               = 11*10^-3   ; %
E                       = 10^10      ; %
Beta                    = 1.6        ; %
gammacv                 = 1.4        ; %
Roh_Air                 = 1.2        ; %
Diam_Cuivret_cot_anche  = 4*10^-3    ; %

%% Init
P0= 10^5; % pression atomspherique
Q0       =[0,0] ; %Vit0,Pos0 
P_Anchen = 10^5    ; %Pression anche a l'instant n
 
Vn = pi*40*10^-9*(80)^2/4; % volume cavité bucale
Debit_entree = 10^-5;% débit d'air à l'entrée
tnm1 =0;
%% Calculs
M          =  2*Roh_Anche*Lar_Anche*Distance_Bout_Fil*Epaisseur_Roseau ;% masse des deux plaquettes
K          =  rLt_Lvib*Distance_Bout_Fil*E*(Epaisseur_Roseau/Lar_Anche)^3 ; % raideur de l'anche
Surf_Anche =   Lar_Anche*Distance_Bout_Fil    ;    %
Section_Cuivret = (pi*Diam_Cuivret_cot_anche^2)/4; %

T0					 = 2*pi/sqrt(K/M)   	; % Periode propre estimée de l'osilation de l'anche
Decoupe_Temps        = 600;
DeltaTemps 			 = T0/(Decoupe_Temps) ; % increment de temps
Temps			     = 0:DeltaTemps:50*T0  ; % Vecteur temps que l'on discrÃ©tise en N dÃ©coupes ;


%% Solveur

Pbouchen = P0;
Mp = [ M 0;  0 -1 ]  ;
Kp = [ 0 K;  1 0  ]  ;

options = odeset('Mass',Mp,'MassSingular','no','MStateDependence','no') ;
[T,Q] = ode45(@Eq_Lame, Temps, Q0, options );

save('Resanche.mat','T','Q')
 figure
 plot(T,Q(:,1))
title('Vitesse anche')
 
 figure
 plot(T,Q(:,2))
title('Position anche')
 
 figure
 plot(Q(:,2),Q(:,1))
title('phase plane')
end

function dQ = Eq_Lame(t,Q)
global  x0 x_seuil Lar_Anche Vn gammacv Pbouchen P_Anchen Kp Section_Cuivret tnm1 itertime Debit_entree Roh_Air Beta Surf_Anche P0 Fn TimeVP;
if tnm1==0
dQ=Q;

else
    

DeltaP =  ( Pbouchen - P_Anchen );
%% Calcul Pertes charges
if (Q(2)>x0)
Q(2)=x0;
end
Posn = Q(2);
% if (Posn<x0)
% Posn=xo;
% end
%Vn
Vitn=Q(1);
Vit_Air_Anche = sign(DeltaP)*exp(-Beta*x_seuil/(x0-Posn))*(2*abs(DeltaP)/Roh_Air)^0.5 + Surf_Anche/(Lar_Anche*(x0-Posn))*Vitn; % Pertes de charges
Section_anche  =  Lar_Anche*(x0-Posn);
Debit_Sortie = Vit_Air_Anche*Section_anche
Debit_entree
%% Pression dans la bouche a t=n+1
deltat=(t-tnm1);
dV   = deltat*( -Debit_entree + Debit_Sortie ) ;  
Volume_Cavitenp1 = Vn  + dV    ;
%Pn
Pbouchenp1 = Pbouchen*(Vn/Volume_Cavitenp1)^gammacv  ;

   
%%    
   Vit_Air_Cuivret=  Vit_Air_Anche*Lar_Anche*(x0-Posn)/Section_Cuivret;
   
%% Pression à l'interieur de l'anche
  P_Acoust=0;
%P_Acoust= P_Anchen - P0 - 1/2*Roh_Air*Vit_Air_Cuivret^2 +1/2*Roh_Air*Vit_Air_Anche^2  ;
   P_Anchen = P0+ P_Acoust + 1/2*Roh_Air*Vit_Air_Cuivret^2 -1/2*Roh_Air*Vit_Air_Anche^2; % summer
%% Forces de pression agissant sur l'anche
   
F = Surf_Anche*(Pbouchenp1-P_Anchen); 
Pbouchen=Pbouchenp1;
Fp = [F 0]';
Vn= Volume_Cavitenp1;
%% Calcul du RK
dQ = (Fp-Kp*Q); 

TimeVP(itertime)            = t                                 ;
Fn(itertime) = F;                                               ;



end

tnm1 =t                     ;
itertime = itertime +1      ;
end
%% parametres phys :

c= 340;% celerité son

%% parametres goulot :
L_goulot = 5 *10^-3;
D_goulot = 120 *10^-3;
L_corr= 0.8*D_goulot/2+L_goulot;

%%calc
S_goulot = pi*(D_goulot^2)/4;


%% parametres volume

H_reso =  75 *10^-3;
D_reso =  240 *10^-3;


%% Calc

V_reso = H_reso*pi*(D_reso^2)/4
V_reso = 47.1*10^-3

f_reso = c/2/pi*sqrt(S_goulot /V_reso/L_corr)


%%plot


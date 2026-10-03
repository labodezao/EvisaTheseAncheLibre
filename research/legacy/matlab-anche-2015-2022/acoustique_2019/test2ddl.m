clear 
C=342;               % célérité du son
Vo=0.14   % volume reso
Rho_air=1.4;             % masse volumique
Mu=Rho_air*C^2/Vo
Freq=10:0.1:400;
Omega=2*pi.*Freq;
K=Omega./C;  %nombre d'onde


Res_t=250 % résonance mécanique de la plaque couplée à la cavité fermée
M_t=0.2;                % masse tabl
Su_t=0.3
M_t=0.2                % masse e
K_t=M_t*4*pi^2*Res_t^2 -Mu*Su_t^2        % raideur premier mode de table


Res_h=195; % résonance mécanique de la plaque couplée à la cavité fermée
M_h=0.00025;                % masse tabl
Su_h=sqrt(M_h*4*pi^2*Res_h^2/Mu   )      % raideur premier mode de table



Gamma_h= 0;
Gamma_t=0;
Om_t2= (K_t+Mu*Su_t^2)/M_t;
Om_h2= Mu*Su_h^2/M_h;
Om_a2= Mu*Su_t^2/M_t;
Om_th4=Om_a2*Om_h2;
Dc=(Om_t2-Omega.^2+j.*Omega*Gamma_t).*(Om_h2-Omega.^2+j.*Omega*Gamma_h)-Om_th4 ;


%%calc

Ht=(Om_h2-Omega.^2+j.*Omega*Gamma_h)./Dc/M_t; 
Hh=Su_t/Su_h*Om_h2/M_t./Dc;

QtsF=Su_t*1i.*Omega.*Ht;
QhsF=Su_h*1i.*Omega.*Hh;

ft=1/2/pi*sqrt((K_t+Mu*Su_t^2)/(M_t))    %fréquence résonance plaque + charge externe dans cavité fermée
fh=1/2/pi*sqrt(Mu*Su_h^2/(M_h))         % fréquence de helmholtz de la cavité rigide

%-------------------------------------------
figure(1);clf;

title ('fonction de transfert abs')
plot(Freq,20*log10(abs(Ht)),'r',Freq,20*log10(abs(Hh)),'k')
legend('xtable/F','xevent/F')



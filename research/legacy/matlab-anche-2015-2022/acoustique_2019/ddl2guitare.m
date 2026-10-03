clear all
% Modèle interaction plaque élastique/cavité
% modèle à deux degrés de liberté d'un résonateur de Helmholtz à parois élastiques
% 
%%


%% Propiétées physiques de l'air
C=342;               % célérité du son
Rho_air=1.4;             % masse volumique
Vo=pi*0.3^2*1/6 ;  % volume reso
Vo=0.01 ;  % volume reso
Mu=Rho_air*C^2/Vo
Theta=0.5; % compressibilité adiab

%% données calculs
Freq=10:0.3:600;
Omega=2*pi.*Freq;
K=Omega./C;  %nombre d'onde
Xsi=0.8;   % coefficient correction longueur

%---------------------------------------------
% paramètres table
%---------------------------------------------
Res_t=380; % résonance mécanique de la plaque couplée à la cavité fermée

D_t=0.6; % rayon plaque effective
Rho_t=500; % masse volumique table
Su_t=pi/4*D_t^2; %surface table
Su_t=0.09 %surface table
Ep_t=3*10^-3; % épaisseur table
Zrayt=Rho_air*C*(Theta*K.^2*D_t^2+1i*Xsi*K.*D_t/2); %impédance de rayonnement table

M_t = Rho_t*Su_t*Ep_t;                % masse table                % masse tabl
K_t= M_t*4*pi^2*Res_t^2 -Mu*Su_t^2        % raideur premier mode de table
Am_t=0;                         % amortissement modal table
Am_h=0;                         % amortissement modal helmotz

%---------------------------------------------
% paramètres helmotz
%---------------------------------------------
D_h=150*10^-3; % rayon ouverture
Ep_h=35*10^-3;  % épaisseur event

Su_h=pi*D_h^2/4; %surface event       
M_h=Rho_air*Su_h*(Ep_h+Xsi*D_h/2)    % masse event avec correction longeur

ZD_h=Rho_air*C*(Theta*K.^2*D_h^2+1i*Xsi*K.*D_h); %impédance de rayonnement table

%%calculs resonnaces


Gamma_h= Am_h/M_h;
Gamma_t=Am_t/M_t;
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

% %-------------------------------------------
% figure(1);clf;
% subplot(211);grid; hold on;
% title ('fonction de transfert abs')
% plot(Freq,20*log10(abs(Ht)),'r',Freq,20*log10(abs(Hh)),'k')
% legend('xtable/F','xevent/F')
% subplot(212);grid; hold on;
% title ('fonction de transfert angle')
% plot(Freq,angle(Ht),'r')
% plot(Freq,angle(Hh),'k')
% 
% figure(2);clf;
% subplot(211);grid; hold on;
% title ('fonction de transfert abs')
% plot(Freq,20*log10(abs(Ht)+abs(Hh)))
% legend('xtable/F')
% subplot(212);grid; hold on;
% title ('fonction de transfert angle')
% plot(Freq,angle(Ht),'r')
% plot(Freq,angle(Hh),'k')
% 
% %
% figure(3);clf;
% subplot(211);grid; hold on;
% title ('fonction de transfert abs')
% PtsF=1i*Omega.*Zrayt.*Ht;
% PhsF=1i*Omega.*ZD_h.*Hh;
% 
% plot(Freq,20*log10(abs(PtsF)),'r',Freq,20*log10(abs(PhsF)),'k')
% legend('Ptable/F','Pevent/F')
% 
% subplot(212);grid; hold on;
% title ('fonction de transfert angle')
% plot(Freq,unwrap(angle(PtsF)),'r',...
%    Freq,unwrap(angle(PhsF)),'k',...
%    Freq,unwrap(angle(PtsF))-unwrap(angle(PhsF)),'g')
% legend('Ptable/F','Pevent/F','phase(Ptable/F-Pevent/F)')
% 
% 
% 

figure(1);clf;

title ('fonction de transfert abs')
plot(Freq,20*log10(abs(Ht)),'r',Freq,20*log10(abs(Hh)),'k')
legend('xtable/F','xevent/F')


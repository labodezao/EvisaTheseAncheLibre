function  RK4ode45cavity_reed_socket()
%[Timemat, FFTMat, TotDSP, Ofrequency, Freq, Pos, Vit] =
clc %Clears the screen
%clear all
close all

global  Mat_Modale pente_stat ForceMod Properties_mat Properties_tab_harmo Properties_Cav Properties_air NDDL L Vittemp Postemp bmoy DLS Qtemp hmoy DeltaTemps Voln Kp Pn tnm1 DeltaP Debit_sortie Debit_entree itertime TimeVP Pntemp Vntemp  ;
DLS = 10^-4;
NDDL = 2;
Pref= 2*10^-5;

Properties_mat = [ 29.22*10^-3 , 7800 , 4.8*10^-3 , 0.40*10^-3 , 2.1*10^11 ; 15.12*10^-3 , 7800 , 4.80*10^-3 , 0.045*10^-3 , 2.1*10^11 ; 10.35*10^-3 , 7800 , 4.8*10^-3 , 0.7*10^-3 , 2.1*10^11 ] ; 
% du type [x0,rho0,b0,h0,E0  ;  xi,rhoi,bi,hi,Ei  ;  xn,rhon,bn,hn,En]

Properties_Cav = [35*10^-3 ,15*10^-3 ,15*10^-3 , 9 *10^-3]; 
% Longueur cavit�, Largeur cavit�, Hauteur cavit�, distance lame/cavit�
%------------------------------------------------------------------------
% 1.2-Parametres g�ometrique de la table d'harmonie
%------------------------------------------------------------------------
Properties_tab_harmo = [290*10^-3,150*10^-3] ;

%------------------------------------------------------------------------
% 1.3-Constantes et variables physiques (E,Roha)
%-------------------------------------------------------------------------
Properties_air = [15.6*10^-6, 1.2  , 1.4 , 10^5]; 
%Viscosité cin�matique de l'air, densit� air, gamma=cp/cv po

 L= sum(Properties_mat(:,1));

bmoy = sum(Properties_mat(:,3))/length(Properties_mat(1,:));
Emoy=sum(Properties_mat(:,5))/length(Properties_mat(1,:));
%-------------------------------------------------------------------------
%-Parametres du systeme a 1ddl  
%-------------------------------------------------------------------------7
hmoy = sum(Properties_mat(:,4))/length(Properties_mat(1,:));
Imoy = bmoy*hmoy^3/12;
romoy = sum(Properties_mat(:,2))/length(Properties_mat(1,:));
Masse = bmoy*hmoy*L*romoy ;
Raideur_Equival		 = 3*Emoy*Imoy/(L^3)   ; % raideur equivalente de la poutre pour le systeme a 1 ddl
wo				     = sqrt(Raideur_Equival/Masse)  ; % Puslation propre estimée de la lame
T0					 = 2*pi/wo   	; % Periode propre estimée de l'osilation de l'anche
Decoupe_Temps        = 900;
DeltaTemps 			 = T0/(Decoupe_Temps) ; % increment de temps
Temps			     = 0:DeltaTemps:50*T0  ; % Vecteur temps que l'on discrétise en N découpes ;
Fs  = 1/DeltaTemps; % Sample time
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
Nombre_calcul_Volume = 3 ;
V0 = Properties_Cav(1)*Properties_Cav(2)*Properties_Cav(3);
if(Nombre_calcul_Volume == 1 )
Volumemin = V0;   
Delta_Calcul_Volume  = 0;
else
Volumemin			 = 0.3*V0 ;
Volumemax			 = 1.9*V0      ;
Delta_Calcul_Volume  = (Volumemax-Volumemin)/(Nombre_calcul_Volume -1)	;
end
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
Nombre_calcul_Press = 3 ;
Debit_max = 2*290*150*10^-9 ;
%%
Delta_Deb=0;
if (Nombre_calcul_Press ~= 1 ) 
Delta_Deb = 2*Debit_max/(Nombre_calcul_Press-1);
end
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
Nombre_calcul_Static   = 1 ;
Flechemax            = 8*10^-4;
Delta_Fleche =0;
if (Nombre_calcul_Static   ~= 1)
Delta_Fleche = 2*Flechemax /L*(Nombre_calcul_Static-1);
end
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

Mat_Modale = Matrice_Modes_Poutre(L);

[Mp,Kp] = matkm();
Val = eig(Kp(1:NDDL,NDDL+1:end),Mp(1:NDDL,1:NDDL)) ;
Freq= sqrt(Val)./(2*pi);


options = odeset('Mass',Mp,'MassSingular','no','MStateDependence','no');


Time_index=zeros(1,length(Temps));
TimeVolPress=zeros(1,length(Temps));

Q=TimeVolPress;
Pos=TimeVolPress;
Vit=TimeVolPress;
Acc=TimeVolPress;
EvPress =TimeVolPress;
EvVol =TimeVolPress;
ForceModale=TimeVolPress;

TotDSP     = zeros(Nombre_calcul_Volume ,Nombre_calcul_Press, Nombre_calcul_Static);
Ofrequency = TotDSP;
TResp      = TotDSP;
VolumeCav  = TotDSP;
PressCalc  = TotDSP;
DeformStatCalc = TotDSP;
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
for Iter_Calc_Static = 1: Nombre_calcul_Static

pente_stat =  - Flechemax/L    + Delta_Fleche*(Iter_Calc_Static-1)
Q0 = [Deformee_Statique(L)*(Mat_Modale\ones(NDDL,1)); zeros(NDDL ,1)]

for Iter_Calc_Press = 1: Nombre_calcul_Press

Debit_entree =  - Debit_max + Delta_Deb*(Iter_Calc_Press-1)
 if (Debit_entree ~= 0)

for Iter_Calc_Vol = 1: Nombre_calcul_Volume  
Pn = Properties_air(4);
tnm1         = 0;
DeltaP       = 0;
Debit_sortie = 0;
itertime     = 0;



Voln = Volumemin + Delta_Calcul_Volume*(Iter_Calc_Vol-1)

eval(['VolumeCav',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),'=  Voln;']); % normalement c'est pareil pour tous les deform�s stats et press
eval(['PressCalc',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),'= Debit_entree;']);
eval(['DeformStatCalc',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),'= Deformee_Statique(L);']);

[~,~] = ode45(@Eq_Lame, Temps, Q0, options );

ntimevp=2;
ntime=2;
Time_index(1) = 1;
while(ntime < length(Temps)+1)
 if(TimeVP(ntimevp) < Temps(ntime) )   
  ntimevp = ntimevp +1;
 else 
Time_index(ntime) = ntimevp-1;
ntime=ntime+1;
end
end

Qtemp = Qtemp(:,Time_index);
eval(['TimeVolPress',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),'=TimeVP(Time_index);'])

for iQddotcal=1:NDDL   
eval(['Qd2(iQddotcal,1:length(TimeVolPress',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),'(2:end)))= (Qtemp(iQddotcal,2:end) - Qtemp(iQddotcal,1:end-1))./( TimeVolPress',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),'(2:end) - TimeVolPress',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),'(1:end-1)); '])  
end



eval(['Q',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),'= smoothn([Qd2 ; Qtemp(:,1:end-1) ],''robust'');'])
clear Qd2
eval(['Pos',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),'=smoothn(Postemp(Time_index),''robust'');'])
eval(['Vit',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),'=smoothn(Vittemp(Time_index),''robust'');'])
eval(['Acc',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),'=smoothn((Vit',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),'(2:end,Iter_Calc_Vol,Iter_Calc_Static,Iter_Calc_Press) - Vit',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),'(1:end-1,Iter_Calc_Vol,Iter_Calc_Static,Iter_Calc_Press))./( TimeVolPress',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),'(2:end,Iter_Calc_Vol,Iter_Calc_Static,Iter_Calc_Press) - TimeVolPress',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),'(1:end-1,Iter_Calc_Vol,Iter_Calc_Static,Iter_Calc_Press)),''robust'');'])
eval(['EvPress',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),'=smoothn(Pntemp(Time_index),''robust'');'])
eval(['EvVol',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),'=smoothn(Vntemp(Time_index),''robust'');'])
eval(['ForceModale',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),'=smoothn(ForceMod(Time_index),''robust'') ;'])


 %%%%%%%%%%%%%%%%%%%---------TRESP--------------%%%%%%%%%%%%%%%%%%%%%
eval(['[env] = envelope(','TimeVolPress',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),''',smoothn(Pos',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),''',10^3));']);
eval(['S = lsiminfo(env,','TimeVolPress',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),'(1:length(env)));']);
eval(['irest = find( ','TimeVolPress',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),'(1:length(env)) > S.SettlingTime ,1);']);
TResp(Iter_Calc_Vol,Iter_Calc_Press,Iter_Calc_Static) = S.SettlingTime ;

if(eval(['(irest > 0.90*length(Pos',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),'))']))
eval(['irest=floor(0.90*length(Pos',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),'))'])
end
clear env
%%%%%%%%%%%%%%%%%%%%%%%%------FFT------%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%min max values
ms1=Fs/(Freq(1)*1.4);                 % maximum speech Fx at 1000Hz
ms20=Fs/(Freq(1)*0.8);                  % minimum speech Fx at 50Hz
% do fourier transform of windowed signal
eval(['Y=fft(smoothn(Pos',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),'(irest:end)'',10^6).*hamming(length(Pos',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),'(irest:end))));']);
% cepstrum is DFT of log spectrum
C=fft(log(abs(Y)+eps));
% figure
% plot(C);

if(length(C)> floor(ms20)-1)
    [~,fx]=max(abs(C(floor(ms1):floor(ms20)-1)));
%---------------------------------------------------------------------------
freqtemp=Fs/(ms1+fx-1);
Ofrequency(Iter_Calc_Vol,Iter_Calc_Press,Iter_Calc_Static)= freqtemp;
else
   freqtemp=0;
end
%%%%%%%%%%%%%%%%%%%DSP%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
clear C
eval(['TotDSP(Iter_Calc_Vol,Iter_Calc_Press,Iter_Calc_Static) = spl(EvPress',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),'(irest:end),''air'');']);


%% Plots
%Pos_Env= figure('PaperType', 'A5');

% figure(Pos_Env)
% plot(TimeVolPress(:,Iter_Calc_Vol,Iter_Calc_Press),Pos(:,Iter_Calc_Vol,Iter_Calc_Press),TimeVolPress(1:length(env),Iter_Calc_Vol,Iter_Calc_Press),env);
% set(gca,'FontSize',12);
% title ({['Time response for inlet volume flow =',num2str(Debit_entree),' m^3/s,'],['Cavity Volume =',num2str(Voln),' m^3, '],['and Static Position at reed end ', num2str(Deformee_Statique(L)),'m'],['Oscillate at ',num2str(freqtemp),' Hz and Settling Time =',num2str(S.SettlingTime) ,'s' ]},'FontSize',12) 
% xlabel('Position [m]'     )
% ylabel('Time [s]'     )
% saveName = ([num2str(NDDL),'DDL_','ivf',num2str(Debit_entree),'_Vol',num2str(Voln),'_Pos', num2str(Deformee_Statique(L)),'.eps']);
% print(Pos_Env,'-depsc2',saveName,'-r550')

%% saves

savefile = ['PVS',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),'.mat'];
save( savefile, ['TimeVolPress',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static)] ,['EvVol',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static)] ,['EvPress',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static)],['Q',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static)],['Pos',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static)],['Vit',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static)],['Acc',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static)],['VolumeCav',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static)],['PressCalc',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static)],['DeformStatCalc',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static)]); 

eval(['clear', ' TimeVolPress',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static) ,' EvVol',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static) ,' EvPress',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),' Q',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),' Pos',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),' Vit',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),' Acc',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),' VolumeCavStat',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),' PressCalc',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static),' DeformStatCalc',num2str(Iter_Calc_Press),num2str(Iter_Calc_Vol),num2str(Iter_Calc_Static)]); 


Qtemp= 0;
Postemp= 0;
Vittemp= 0;
Pntemp= 0;
Vntemp= 0;
ForceMod= 0;




end
end
end 
end

  savefile = 'MatRes.mat';
save(savefile, 'TotDSP', 'Ofrequency', 'TResp' ,'VolumeCav','PressCalc','DeformStatCalc');
% clear TotDSP Ofrequency TResp VolumeCav PressCalc DeformStatCalc


%%%%%%%%%%%%%%%%%%%%%%%%%PLOT 3d %%%%%%%%%%%%%%%%%%%%%%%%%

% figure
% 
% plot3(smoothn(Pos(1:end-1,1,1,1)),smoothn(Vit(1:end-1,1,1,1)),smoothn(Acc(:,1,1,1)))
% 
% grid on
% title ('Espace phase 3D'   ) 
% xlabel('Position -m-'     )
% ylabel('Vitesse -SI-'     )
% zlabel('Acceleration -SI-')
% 

figure

[XDSP,YDSP] = meshgrid(VolumeCav(:,1,1), PressCalc(1,1,:));
ZDSP(:,:) = smoothn(TotDSP(:,1,:));
%plot3(XOfreq,YOfreq,ZOfreq')
surf(XDSP,YDSP,ZDSP')
shading interp
grid on
title ('Dsp(Volume , Volumic inlet air flow )'  ) 
xlabel('Volume [m^3]'     )
ylabel('Debit[m^3/s]'     )
zlabel('Dsp_Spl [db]')


figure

[XOfreq,YOfreq] = meshgrid(VolumeCav(:,1,1),PressCalc(1,1,:));
ZOfreq(:,:) = smoothn(Ofrequency(:,1,:));
%plot3(XOfreq,YOfreq,ZOfreq)
surf(XOfreq,YOfreq,ZOfreq')
shading interp
grid on
title ('Freq(Volume , Volumic inlet air flow )'  ) 
xlabel('Volume [m^3]'     )
ylabel('Debit[m^3/s]'     )
zlabel('Fondamental Frequency [db]')



figure

[XResp,YResp] = meshgrid(VolumeCav(:,1,1),PressCalc(1,1,:));
ZResp(:,:) = smoothn(TResp(:,1,:));
%plot3(XOfreq,YOfreq,ZOfreq)
surf(XResp,YResp,ZResp')
shading interp
grid on
title ('seattling time (Volume , Volumic inlet air flow )'  ) 
xlabel('Volume [m^3]'     )
ylabel('Volumic inlet  air flow[m^3/s]'     )
zlabel('Response time [s]')

%%%%%%%%%%%%%%%%%%%%%%PLOT 2D %%%%%%%%%%%%%%%%%%%%
% 
% DSPfig = figure('PaperType', 'A4');
% q = figure('PaperType', 'A4');
% phasetot = figure('PaperType', 'A4');
% VolvsFReq = figure('PaperType', 'A4');
% 
% figure(DSPfig)
% 
% plot(VolumeCav,TotDSP )
% grid on
% title('DSP vs Volume') 
% xlabel('Volume [m^3]')
% ylabel('Dsp')
% 
% figure(VolvsFReq)
% 
% plot(VolumeCav(),Ofrequency() )
% grid on
% title('Oscillation freqency versus Volume') 
% xlabel('Volume [m^3]')
% ylabel('Oscilation frequency')
% 
% for k=1:NDDL
%     
% figure ( q )
% subplot(2,NDDL,NDDL+k)
% plot(T,Q(:,NDDL+k));
% title(['q',num2str(k),'versus Time']);
% xlabel('Time [s]')
% ylabel(['q',num2str(k)])
% 
% subplot(2,NDDL,k)
% plot(T,Q(:,k));
% title(['dq',num2str(k),'/dt versus Time']);
% xlabel('Time [s]')
% ylabel(['dq',num2str(k),'/dt'])
% end
% 
% figure ( phasetot);
% subplot(1,2,1)
% plot(Postemp,Vittemp);
% title('Phase portrait for the reed');
% xlabel('Position [m]')
% ylabel('Velocity [m/s]')
% subplot(1,2,2)
% plot(T,Postemp);
% title('Reed Position vs time');
% xlabel('Time [s]')
% ylabel('Position [m]')
% %On regarde en milieu de lame
% 

% 
% saveName = ([num2str(NDDL),'DDL','boutphase.jpg']);
% print(phasetot,'-djpeg',saveName,'-r550')
% 
% saveName = ([num2str(NDDL),'DDL','VolvsFreq.jpg']);
% print(VolvsFReq,'-djpeg',saveName,'-r550')
% 
% saveName = ([num2str(NDDL),'DDL','q.jpg']);
% print(q,'-djpeg',saveName,'-r550')
% 
% %Save matrices
% 

clear all


end



%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

 function [ds] = Deformee_Statique(x)
% x      		: [Param�tre de la fonction : position longitudinale ou on recheche la déformée modale]
% ds 			: [Valeur de la déformée statique en x]
%----------------------------------------------------------------------
 global pente_stat;
 ds=pente_stat*x;
 end
 
 %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

 %function [d] =Distance_boutlame_socle(x)
% x      		: [fl�che de la poutre]
% d 			: [distance lame socle]
%----------------------------------------------------------------------
% global pente_stat;
 
%d= ;
 %end

% Fonction second membre de l'equation diffencielle 

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
function dQ = Eq_Lame(t,Q) % on met ici dans d le second membre donc Delta pression entre l'extrados et l'intrados de la lame u(1) est X alors que u(2) est sa dérivée

global  Voln Pn Qtemp Kp tnm1 TimeVP Pntemp Vntemp itertime Debit_entree NDDL L Postemp Vittemp Mat_Modale ForceMod ;


if tnm1==0
dQ=Q;


else
    
Deltat = t-tnm1;

%%

Qstatic = [ Deformee_Statique(L)*(Mat_Modale\ones(NDDL,1)); zeros(NDDL ,1)];

Q = Q + Qstatic;

[Fp,Volnp1,Pnp1] = matf(Q ,Debit_entree, Voln, Pn, Deltat);
dQ = (Fp-Kp*Q); 

%(Mat_Modale(1,1:NDDL)*dQ(1:NDDL))

%%

Qtemp(1:length(Q),itertime) = Q                                 ;
TimeVP(itertime)            = t                                 ;
Pntemp(itertime)            = Pn                                ;
Vntemp(itertime)            = Voln                              ;
Postemp(itertime)           = Mat_Modale(1,:)*Q(NDDL+1 : end)   ;
Vittemp(itertime)           = Mat_Modale(1,:)*Q(1 : NDDL)       ;
ForceMod(itertime)          = Mat_Modale(1,1:NDDL)*dQ(1:NDDL)   ;

Voln = Volnp1                                                   ;
Pn = Pnp1                                                       ;

end
tnm1 =t                                                         ;
itertime = itertime +1                                          ;
end


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
function [Fp , Volume_Cavitenp1,Pnp1 ] = matf(Q, Debit_entree , Vn, Pn, DeltaTemps)
global Mat_Modale Properties_mat Properties_Cav  Properties_air NDDL L Debit_sortie  DLS Properties_tab_harmo bmoy hmoy  ;
  syms x  ;
[nsection,nparam] = size(Properties_mat) ;  
gamma_sigmo = 1*10^-3;
beta_sigmo = -2200;
gamma_sigmo2 =-Properties_Cav(4)*10^-3;

DeltaP =  ( Pn - 10^5);




Posn = Mat_Modale(1,:)*Q(NDDL+1 : end);



S_Table        = Properties_tab_harmo(2)*Properties_tab_harmo(1)  ; %// 
S_Inter        = DLS*(2*L+ bmoy +2*DLS)  ;                            
S_Trou         = (L+DLS)*(min(Properties_mat(:,3)) + 4*DLS + max(Properties_mat(:,3)))/2  ;


if(Debit_sortie ==0)
Re_open = Debit_entree*DLS/(S_Trou*Properties_air(1));
else
Re_open = Debit_sortie*DLS/(S_Trou*Properties_air(1));
end
 if( Re_open < 3000)
   Kpc_open = 64 / Re_open;
 else
   Kpc_open = 0.316*Re_open^(-0.25);
 end

 % 3) Calcul du volume entree a l'instant n :
 %-------------------------------------------------------------------
      TQ1_open = Kpc_open*hmoy*(6*DLS+2*bmoy + 2*L)/4*(S_Trou)                                     ; %termes pertes de charges regulières 
      TQ2_open = (1-S_Trou/S_Table)^2  ; %terme pertes de charges singulières elargissement
      TQ3_open = (1/0.65 - 1)^2*(Properties_Cav(1)*Properties_Cav(2)/S_Trou)^2  ; %terme pertes de charges singulières retrecissement      
      TQtot_open = TQ1_open + TQ2_open + TQ3_open ;



if(Debit_sortie == 0)
Re_close = Debit_entree*DLS/(S_Inter*Properties_air(1));
else
Re_close = Debit_sortie*DLS/(S_Inter*Properties_air(1));
end
 if( Re_close < 3000)
   Kpc_close = 64/Re_close;
 else
   Kpc_close = 0.316*Re_close^(-0.25);
 end
      TQ1_close = Kpc_close*hmoy*(6*DLS+2*bmoy + 4*L)/4*(S_Inter)                ; %termes pertes de charges regulières
      TQ2_close = (1-S_Inter/S_Table)^2                                          ; %terme pertes de charges singulières elargissement
      TQ3_close = (1/0.65 - 1)^2*(Properties_Cav(1)*Properties_Cav(2)/S_Inter)^2 ; %terme pertes de charges singulières retrecissement   
      TQtot_close = TQ1_close + TQ2_close + TQ3_close                            ;

%TQtot_close
% pertes de charges clapet 

 TQ_clap =  40.52*0.91^(abs(atand(Posn/L)));

 
pondersigmoa = exp(beta_sigmo*(Posn + gamma_sigmo))/(1+exp(beta_sigmo*(Posn + gamma_sigmo))) + (1/(1+exp(beta_sigmo*(Posn+gamma_sigmo2))))^2  ;
%pondersigmoa

 Funct_Ksi = TQtot_close/S_Inter^2 + ((TQtot_open + TQ_clap) / S_Trou^2 - TQtot_close/S_Inter^2)*pondersigmoa ;    
%Funct_Ksi
%S_Trou
%DeltaP
 Debit_sortie = sign(DeltaP)*(abs(2*DeltaP)/(Properties_air(2)*Funct_Ksi) )^0.5     ;

%  
% Debit_sortie
% Debit_entree
Qlf   =0 ;
Qltemp = 0;
 
 for j = 1 : NDDL
 [Bi,Si] = BL_Sigma(j);
  xnp1=  Properties_mat(1,1);
  xn=0;
  for k=1:nsection 
if k>1
 xn = xnp1;
xnp1= xnp1 + Properties_mat(k,1);
end
Qli= Q(j)*Properties_mat( k,3 )*L/Bi*( sinh((Bi*xnp1)/L)-sin((Bi*xnp1)/L) - (sinh((Bi*xn)/L)-sin((Bi*xn)/L)) -Si*(cosh((Bi*xnp1)/L) + cos((Bi*xnp1)/L) - cosh((Bi*xn)/L) - cos((Bi*xn)/L))  ) ;
Qltemp= Qltemp +Qli;
  end
 %Q(j) 
Qlf= Qlf + Qltemp;
  
 end
%  Qlf
 
gammacv= Properties_air(3);

dV   = DeltaTemps*( Debit_entree - Debit_sortie + Qlf) ;
   
   Volume_Cavitenp1 = Vn  + dV  ; 
 
   Pnp1 = Pn*(Vn/Volume_Cavitenp1)^gammacv  ;
%    Pn

 
   DeltaP = (   Pnp1 -Properties_air(4))                             ; %
%DeltaP
%%% matrice Fi

F=zeros(1,NDDL);

for i= 1: NDDL;
   [Bi,Si] = BL_Sigma(i) ; 
 
  F_i=0;
  xn = 0;
  xnp1=  Properties_mat(1,1);
  for k=1:nsection  
if k>1
 xn = xnp1;
xnp1= xnp1 + Properties_mat(k,1);
end
fi= DeltaP*Properties_mat(k,3)*L/Bi*( sinh((Bi*xnp1)/L)-sin((Bi*xnp1)/L) - (sinh((Bi*xn)/L)-sin((Bi*xn)/L)) -Si*(cosh((Bi*xnp1)/L) + cos((Bi*xnp1)/L) - cosh((Bi*xn)/L) - cos((Bi*xn)/L))  ) ;

F_i = F_i + fi;
  end
  
F(i)= F_i;

end

Fp = [F zeros( 1,NDDL)]';

end


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
function [Mp,Kp] = matkm()
syms x  ;
global Properties_mat  NDDL L ;

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
 end
%Mtest=double(int( (cosh(Bi/L*x)-cos(Bi/L*x)-Si*(sinh(Bi/L*x)-sin(Bi/L*x)))*(cosh(Bj/L*x)-cos(Bj/L*x)-Sj*(sinh(Bj/L*x)-sin(Bj/L*x))) , 0 , L) )*Properties_mat(k,2)*Properties_mat(k,3)*Properties_mat(k,4) +0
%Ktest=double(int( diff(cosh(Bi/L*x)-cos(Bi/L*x)-Si*(sinh(Bi/L*x)-sin(Bi/L*x)),x,2)*diff(cosh(Bj/L*x)-cos(Bj/L*x)-Sj*(sinh(Bj/L*x)-sin(Bj/L*x)),x,2)  , 0 , L) )*Properties_mat(k,5)*Properties_mat(k,3)*Properties_mat(k,4)^3/12
 
M(i,j) = (M_ij);
K(i,j) = (K_ij);
 end


end



Mp = [M zeros(NDDL);zeros(NDDL) -eye(NDDL)] 
Kp = [zeros(NDDL) K;  eye(NDDL) zeros(NDDL)] 


%Val = eig(K,M) ;

%Freq= sqrt(Val)./(2*pi);

end


function [Mat_Mod] = Matrice_Modes_Poutre (x)
global NDDL L ;


Mat_Mod=eye(NDDL);
for i_mod = 1:NDDL
    
[Bi,sig] = BL_Sigma(i_mod);
 
Mat_Mod(1,i_mod) = (cosh(Bi/L*x)-cos(Bi/L*x)-sig*(sinh(Bi/L*x)-sin(Bi/L*x)));
end
end



%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
function [Bl,sigma] = BL_Sigma(n)
%/ n            : numero du mode ;
% x      		: [Parametre de la fonction : position longitudinale ou on recheche la déformée modale]
% Offset 		: [valeur de l'offset du à la déformée statique en x]
% Bl     		: [Longeur de l'anche : Variable Externe]
% sigma 	 	: [Longeur de l'anche : Variable Externe]
% L 	: [Longeur de l'anche : Variable Externe]
% f 			: [variable de sortie de la fonction : donne la valeur de la déformée modale en un point x]
%-------------------------------------------------------------------
if n < 6
    
switch n
case 1
 Bl              = 1.87510407                           ;
sigma			 = 0.7341                               ;
case 2 
 Bl              = 4.69409113                           ;
sigma			 = 1.0185                               ;
case 3 
Bl               = 7.85475744                           ;
sigma			 = 0.9992                     	        ;
case 4 
 Bl               = 10.99554073                     	;
sigma			 = 1                                	;
case 5 
Bl               = 14.13716839                        	;
sigma			 = 1                                    ;
end

else
Bl               =   (2*n-1)*pi/2                       ;
sigma			 =    1                                 ;
end

end




function [up,down] = envelope(x,y,interpMethod)

%ENVELOPE gets the data of upper and down envelope of the known input (x,y).
%
%   Input parameters:
%    x               the abscissa of the given data
%    y               the ordinate of the given data
%    interpMethod    the interpolation method
%
%   Output parameters:
%    up      the upper envelope, which has the same length as x.
%    down    the down envelope, which has the same length as x.
%
%   See also DIFF INTERP1

%   Designed by: Lei Wang, <WangLeiBox@hotmail.com>, 11-Mar-2003.
%   Last Revision: 21-Mar-2003.
%   Dept. Mechanical & Aerospace Engineering, NC State University.
% $Revision: 1.1 $  $Date: 3/21/2003 10:33 AM $

if (length(x) == length(y) && length(x)>3 && length(find(diff(sign(diff(y)))==-2)) > 3)
    


if (nargin < 2)||(nargin > 3),
 error('Please see help for INPUT DATA.');
elseif (nargin == 2)
    interpMethod = 'linear';
end

% Find the extreme maxim values 
% and the corresponding indexes

%oRIGINAL:
% extrMaxValue = y(find( diff(sign(diff(y)) )==-2  )+1);
% extrMaxIndex =   find(diff(sign(diff(y)))==-2)+1;

%---------------------------------------------------- 

extrMaxValue = y(find( diff(sign(diff(y)) )==-2  )+1);
extrMaxIndex =   find(diff(sign(diff(y)))==-2)+1;

up = extrMaxValue;
up_x = x(extrMaxIndex);

if (length(up_x)>1 && length(x)>1 && length(up)>1 && length(find(diff(up)==0)) < floor(length(up)*0.15) )
yp0 =interp1(up_x,up,x,'linear');
yp=yp0;


 s=100;

itersmooth=1;
while(length(find(diff(sign(diff(yp)))==+2) )> 7)
itersmooth=itersmooth+1;
    yp = smoothn(yp,s*100);
s=s*100;

end
 
Cutindex =   find(  diff(sign(diff(yp)))==-2,3)+1;
if (~isempty(Cutindex))
[~,icutindexmax]= min(abs(yp0(Cutindex)-ones(length(yp0(Cutindex)),1)*mean(yp0(floor(0.90*end):floor(0.95*end))))) ;
    up = smoothn(yp0(1:Cutindex(icutindexmax)),10000);
end
else
up=y(1:floor(end/2));    
end
else
up=y(1:floor(end/2));
end
end



function [SPL] = spl(p_Pa,ref)

% Calculate root mean square value of pressure signal
p_rms = sqrt(mean(p_Pa.^2));

% Define the correct reference pressure: 
switch ref
    case {'air','Air','AIR','gas','Gas','GAS'}
        p_ref = 20*1e-6; % reference pressure in air is typically 20 uPa

    case {'water','Water','WATER','liquid','Liquid','LIQUID','SALTWATER','saltwater','Saltwater'}
        p_ref = 1*1e-6; % reference pressure in water is typically 1 uPa
        
    otherwise
        p_ref = ref; % reference pressure can be any user-defined value 'ref'
end

SPL = 20*log10(p_rms/p_ref);
end


function [z,s,exitflag,Wtot] = smoothn(varargin)

%SMOOTHN Robust spline smoothing for 1-D to N-D data.
%   SMOOTHN provides a fast, automatized and robust discretized smoothing
%   spline for data of any dimension.
%
%   Z = SMOOTHN(Y) automatically smoothes the uniformly-sampled array Y. Y
%   can be any N-D noisy array (time series, images, 3D data,...). Non
%   finite data (NaN or Inf) are treated as missing values.
%
%   Z = SMOOTHN(Y,S) smoothes the array Y using the smoothing parameter S.
%   S must be a real positive scalar. The larger S is, the smoother the
%   output will be. If the smoothing parameter S is omitted (see previous
%   option) or empty (i.e. S = []), it is automatically determined using
%   the generalized cross-validation (GCV) method.
%
%   Z = SMOOTHN(Y,W) or Z = SMOOTHN(Y,W,S) specifies a weighting array W of
%   real positive values, that must have the same size as Y. Note that a
%   nil weight corresponds to a missing value.
%
%   Robust smoothing
%   ----------------
%   Z = SMOOTHN(...,'robust') carries out a robust smoothing that minimizes
%   the influence of outlying data.
%
%   [Z,S] = SMOOTHN(...) also returns the calculated value for S so that
%   you can fine-tune the smoothing subsequently if needed.
%
%   An iteration process is used in the presence of weighted and/or missing
%   values. Z = SMOOTHN(...,OPTION_NAME,OPTION_VALUE) smoothes with the
%   termination parameters specified by OPTION_NAME and OPTION_VALUE. They
%   can contain the following criteria:
%       -----------------
%       TolZ:       Termination tolerance on Z (default = 1e-3)
%                   TolZ must be in ]0,1[
%       MaxIter:    Maximum number of iterations allowed (default = 100)
%       Initial:    Initial value for the iterative process (default =
%                   original data)
%       -----------------
%   Syntax: [Z,...] = SMOOTHN(...,'MaxIter',500,'TolZ',1e-4,'Initial',Z0);
%
%   [Z,S,EXITFLAG] = SMOOTHN(...) returns a boolean value EXITFLAG that
%   describes the exit condition of SMOOTHN:
%       1       SMOOTHN converged.
%       0       Maximum number of iterations was reached.
%
%   Class Support
%   -------------
%   Input array can be numeric or logical. The returned array is of class
%   double.
%
%   Notes
%   -----
%   The N-D (inverse) discrete cosine transform functions <a
%   href="matlab:web('http://www.biomecardio.com/matlab/dctn.html')"
%   >DCTN</a> and <a
%   href="matlab:web('http://www.biomecardio.com/matlab/idctn.html')"
%   >IDCTN</a> are required.
%
%   To be made
%   ----------
%   Estimate the confidence bands (see Wahba 1983, Nychka 1988).
%
%   Reference
%   --------- 
%   Garcia D, Robust smoothing of gridded data in one and higher dimensions
%   with missing values. Computational Statistics & Data Analysis, 2010. 
%   <a
%   href="matlab:web('http://www.biomecardio.com/pageshtm/publi/csda10.pdf')">PDF download</a>
%
%   Examples:
%   --------
%   % 1-D example
%   x = linspace(0,100,2^8);
%   y = cos(x/10)+(x/50).^2 + randn(size(x))/10;
%   y([70 75 80]) = [5.5 5 6];
%   z = smoothn(y); % Regular smoothing
%   zr = smoothn(y,'robust'); % Robust smoothing
%   subplot(121), plot(x,y,'r.',x,z,'k','LineWidth',2)
%   axis square, title('Regular smoothing')
%   subplot(122), plot(x,y,'r.',x,zr,'k','LineWidth',2)
%   axis square, title('Robust smoothing')
%
%   % 2-D example
%   xp = 0:.02:1;
%   [x,y] = meshgrid(xp);
%   f = exp(x+y) + sin((x-2*y)*3);
%   fn = f + randn(size(f))*0.5;
%   fs = smoothn(fn);
%   subplot(121), surf(xp,xp,fn), zlim([0 8]), axis square
%   subplot(122), surf(xp,xp,fs), zlim([0 8]), axis square
%
%   % 2-D example with missing data
%   n = 256;
%   y0 = peaks(n);
%   y = y0 + rand(size(y0))*2;
%   I = randperm(n^2);
%   y(I(1:n^2*0.5)) = NaN; % lose 1/2 of data
%   y(40:90,140:190) = NaN; % create a hole
%   z = smoothn(y); % smooth data
%   subplot(2,2,1:2), imagesc(y), axis equal off
%   title('Noisy corrupt data')
%   subplot(223), imagesc(z), axis equal off
%   title('Recovered data ...')
%   subplot(224), imagesc(y0), axis equal off
%   title('... compared with original data')
%
%   % 3-D example
%   [x,y,z] = meshgrid(-2:.2:2);
%   xslice = [-0.8,1]; yslice = 2; zslice = [-2,0];
%   vn = x.*exp(-x.^2-y.^2-z.^2) + randn(size(x))*0.06;
%   subplot(121), slice(x,y,z,vn,xslice,yslice,zslice,'cubic')
%   title('Noisy data')
%   v = smoothn(vn);
%   subplot(122), slice(x,y,z,v,xslice,yslice,zslice,'cubic')
%   title('Smoothed data')
%
%   % Cardioid
%   t = linspace(0,2*pi,1000);
%   x = 2*cos(t).*(1-cos(t)) + randn(size(t))*0.1;
%   y = 2*sin(t).*(1-cos(t)) + randn(size(t))*0.1;
%   z = smoothn(complex(x,y));
%   plot(x,y,'r.',real(z),imag(z),'k','linewidth',2)
%   axis equal tight
%
%   % Cellular vortical flow
%   [x,y] = meshgrid(linspace(0,1,24));
%   Vx = cos(2*pi*x+pi/2).*cos(2*pi*y);
%   Vy = sin(2*pi*x+pi/2).*sin(2*pi*y);
%   Vx = Vx + sqrt(0.05)*randn(24,24); % adding Gaussian noise
%   Vy = Vy + sqrt(0.05)*randn(24,24); % adding Gaussian noise
%   I = randperm(numel(Vx));
%   Vx(I(1:30)) = (rand(30,1)-0.5)*5; % adding outliers
%   Vy(I(1:30)) = (rand(30,1)-0.5)*5; % adding outliers
%   Vx(I(31:60)) = NaN; % missing values
%   Vy(I(31:60)) = NaN; % missing values
%   Vs = smoothn(complex(Vx,Vy),'robust'); % automatic smoothing
%   subplot(121), quiver(x,y,Vx,Vy,2.5), axis square
%   title('Noisy velocity field')
%   subplot(122), quiver(x,y,real(Vs),imag(Vs)), axis square
%   title('Smoothed velocity field')
%
%   See also SMOOTH, SMOOTH3, DCTN, IDCTN.
%
%   -- Damien Garcia -- 2009/03, revised 2010/11
%   Visit my <a
%   href="matlab:web('http://www.biomecardio.com/matlab/smoothn.html')">website</a> for more details about SMOOTHN 

% Check input arguments
error(nargchk(1,12,nargin));

%% Test & prepare the variables
%---
k = 0;
while k<nargin && ~ischar(varargin{k+1}), k = k+1; end
%---
% y = array to be smoothed
y = double(varargin{1});
sizy = size(y);
noe = prod(sizy); % number of elements
if noe<2, z = y; return, end
%---
% Smoothness parameter and weights
W = ones(sizy);
s = [];
if k==2
    if isempty(varargin{2}) || isscalar(varargin{2}) % smoothn(y,s)
        s = varargin{2}; % smoothness parameter
    else % smoothn(y,W)
        W = varargin{2}; % weight array
    end
elseif k==3 % smoothn(y,W,s)
        W = varargin{2}; % weight array
        s = varargin{3}; % smoothness parameter
end
if ~isequal(size(W),sizy)
        error('MATLAB:smoothn:SizeMismatch',...
            'Arrays for data and weights must have same size.')
elseif ~isempty(s) && (~isscalar(s) || s<0)
    error('MATLAB:smoothn:IncorrectSmoothingParameter',...
        'The smoothing parameter must be a scalar >=0')
end
%---
% "Maximal number of iterations" criterion
I = find(strcmpi(varargin,'MaxIter'),1);
if isempty(I)
    MaxIter = 100; % default value for MaxIter
else
    try
        MaxIter = varargin{I+1};
    catch ME
        error('MATLAB:smoothn:IncorrectMaxIter',...
            'MaxIter must be an integer >=1')
    end
    if ~isnumeric(MaxIter) || ~isscalar(MaxIter) ||...
            MaxIter<1 || MaxIter~=round(MaxIter)
        error('MATLAB:smoothn:IncorrectMaxIter',...
            'MaxIter must be an integer >=1')        
    end    
end
%---
% "Tolerance on smoothed output" criterion
I = find(strcmpi(varargin,'TolZ'),1);
if isempty(I)
    TolZ = 1e-3; % default value for TolZ
else
    try
        TolZ = varargin{I+1};
    catch ME
        error('MATLAB:smoothn:IncorrectTolZ',...
            'TolZ must be in ]0,1[')
    end
    if ~isnumeric(TolZ) || ~isscalar(TolZ) || TolZ<=0 || TolZ>=1 
        error('MATLAB:smoothn:IncorrectTolZ',...
            'TolZ must be in ]0,1[')
    end    
end
%---
% "Initial Guess" criterion
I = find(strcmpi(varargin,'Initial'),1);
if isempty(I)
    isinitial = false; % default value for TolZ
else
    isinitial = true;
    try
        z0 = varargin{I+1};
    catch ME
        error('MATLAB:smoothn:IncorrectInitialGuess',...
            'Z0 must be a valid initial guess for Z')
    end
    if ~isnumeric(z0) || ~isequal(size(z0),sizy) 
        error('MATLAB:smoothn:IncorrectTolZ',...
            'Z0 must be a valid initial guess for Z')
    end    
end
%---
% "Weighting function" criterion
I = find(strcmpi(varargin,'Weights'),1);
if isempty(I)
    weightstr = 'bisquare'; % default weighting function
else
    try
        weightstr = lower(varargin{I+1});
    catch ME
        error('MATLAB:smoothn:IncorrectWeights',...
            'A valid weighting function must be chosen')
    end
    if ~ischar(weightstr)
        error('MATLAB:smoothn:IncorrectWeights',...
            'A valid weighting function must be chosen')
    end    
end
%---
% Weights. Zero weights are assigned to not finite values (Inf or NaN),
% (Inf/NaN values = missing data).
IsFinite = isfinite(y);
nof = nnz(IsFinite); % number of finite elements
W = W.*IsFinite;
if any(W<0)
    error('MATLAB:smoothn:NegativeWeights',...
        'Weights must all be >=0')
else 
    W = W/max(W(:));
end
%---
% Weighted or missing data?
isweighted = any(W(:)<1);
%---
% Robust smoothing?
isrobust = any(strcmpi(varargin,'robust'));
%---
% Automatic smoothing?
isauto = isempty(s);
%---
% DCTN and IDCTN are required
test4DCTNandIDCTN

%% Creation of the Lambda tensor
%---
% Lambda contains the eingenvalues of the difference matrix used in this
% penalized least squares process.
d = ndims(y);
Lambda = zeros(sizy);
for i = 1:d
    siz0 = ones(1,d);
    siz0(i) = sizy(i);
    Lambda = bsxfun(@plus,Lambda,...
        cos(pi*(reshape(1:sizy(i),siz0)-1)/sizy(i)));
end
Lambda = -2*(d-Lambda);
if ~isauto, Gamma = 1./(1+s*Lambda.^2); end

%% Upper and lower bound for the smoothness parameter
% The average leverage (h) is by definition in [0 1]. Weak smoothing occurs
% if h is close to 1, while over-smoothing appears when h is near 0. Upper
% and lower bounds for h are given to avoid under- or over-smoothing. See
% equation relating h to the smoothness parameter (Equation #12 in the
% referenced CSDA paper).
N = sum(sizy~=1); % tensor rank of the y-array
hMin = 1e-6; hMax = 0.99;
sMinBnd = (((1+sqrt(1+8*hMax.^(2/N)))/4./hMax.^(2/N)).^2-1)/16;
sMaxBnd = (((1+sqrt(1+8*hMin.^(2/N)))/4./hMin.^(2/N)).^2-1)/16;

%% Initialize before iterating
%---
Wtot = W;
%--- Initial conditions for z
if isweighted
    %--- With weighted/missing data
    % An initial guess is provided to ensure faster convergence. For that
    % purpose, a nearest neighbor interpolation followed by a coarse
    % smoothing are performed.
    %---
    if isinitial % an initial guess (z0) has been provided
        z = z0;
    else
        z = InitialGuess(y,IsFinite);
    end
else
    z = zeros(sizy);
end
%---
z0 = z;
y(~IsFinite) = 0; % arbitrary values for missing y-data
%---
tol = 1;
RobustIterativeProcess = true;
RobustStep = 1;
nit = 0;
%--- Error on p. Smoothness parameter s = 10^p
errp = 0.1;
opt = optimset('TolX',errp);
%--- Relaxation factor RF: to speedup convergence
RF = 1 + 0.75*isweighted;

%% Main iterative process
%---
while RobustIterativeProcess
    %--- "amount" of weights (see the function GCVscore)
    aow = sum(Wtot(:))/noe; % 0 < aow <= 1
    %---
    while tol>TolZ && nit<MaxIter
        nit = nit+1;
        DCTy = dctn(Wtot.*(y-z)+z);
        if isauto && ~rem(log2(nit),1)
            %---
            % The generalized cross-validation (GCV) method is used.
            % We seek the smoothing parameter s that minimizes the GCV
            % score i.e. s = Argmin(GCVscore).
            % Because this process is time-consuming, it is performed from
            % time to time (when nit is a power of 2)
            %---
            fminbnd(@gcv,log10(sMinBnd),log10(sMaxBnd),opt);
        end
        z = RF*idctn(Gamma.*DCTy) + (1-RF)*z;
        
        % if no weighted/missing data => tol=0 (no iteration)
        tol = isweighted*norm(z0(:)-z(:))/norm(z(:));
       
        z0 = z; % re-initialization
    end
    exitflag = nit<MaxIter;

    if isrobust %-- Robust Smoothing: iteratively re-weighted process
        %--- average leverage
        h = sqrt(1+16*s); h = sqrt(1+h)/sqrt(2)/h; h = h^N;
        %--- take robust weights into account
        Wtot = W.*RobustWeights(y-z,IsFinite,h,weightstr);
        %--- re-initialize for another iterative weighted process
        isweighted = true; tol = 1; nit = 0; 
        %---
        RobustStep = RobustStep+1;
        RobustIterativeProcess = RobustStep<4; % 3 robust steps are enough.
    else
        RobustIterativeProcess = false; % stop the whole process
    end
end

%% Warning messages
%---
if isauto
    if abs(log10(s)-log10(sMinBnd))<errp
        warning('MATLAB:smoothn:SLowerBound',...
            ['s = ' num2str(s,'%.3e') ': the lower bound for s ',...
            'has been reached. Put s as an input variable if required.'])
    elseif abs(log10(s)-log10(sMaxBnd))<errp
        warning('MATLAB:smoothn:SUpperBound',...
            ['s = ' num2str(s,'%.3e') ': the upper bound for s ',...
            'has been reached. Put s as an input variable if required.'])
    end
end
if nargout<3 && ~exitflag
    warning('MATLAB:smoothn:MaxIter',...
        ['Maximum number of iterations (' int2str(MaxIter) ') has ',...
        'been exceeded. Increase MaxIter option or decrease TolZ value.'])
end


%% GCV score
%---
function GCVscore = gcv(p)
    % Search the smoothing parameter s that minimizes the GCV score
    %---
    s = 10^p;
    Gamma = 1./(1+s*Lambda.^2);
    %--- RSS = Residual sum-of-squares
    if aow>0.9 % aow = 1 means that all of the data are equally weighted
        % very much faster: does not require any inverse DCT
        RSS = norm(DCTy(:).*(Gamma(:)-1))^2;
    else
        % take account of the weights to calculate RSS:
        yhat = idctn(Gamma.*DCTy);
        RSS = norm(sqrt(Wtot(IsFinite)).*(y(IsFinite)-yhat(IsFinite)))^2;
    end
    %---
    TrH = sum(Gamma(:));
    GCVscore = RSS/nof/(1-TrH/noe)^2;
end

end

%% Robust weights
function W = RobustWeights(r,I,h,wstr)
    % weights for robust smoothing.
    MAD = median(abs(r(I)-median(r(I)))); % median absolute deviation
    u = abs(r/(1.4826*MAD)/sqrt(1-h)); % studentized residuals
    if strcmp(wstr,'cauchy')
        c = 2.385; W = 1./(1+(u/c).^2); % Cauchy weights
    elseif strcmp(wstr,'talworth')
        c = 2.795; W = u<c; % Talworth weights
    else
        c = 4.685; W = (1-(u/c).^2).^2.*((u/c)<1); % bisquare weights
    end
    W(isnan(W)) = 0;
end

%% Test for DCTN and IDCTN
function test4DCTNandIDCTN
    if ~exist('dctn','file')
        error('MATLAB:smoothn:MissingFunction',...
            ['DCTN and IDCTN are required. Download DCTN <a href="matlab:web(''',...
            'http://www.biomecardio.com/matlab/dctn.html'')">here</a>.'])
    elseif ~exist('idctn','file')
        error('MATLAB:smoothn:MissingFunction',...
            ['DCTN and IDCTN are required. Download IDCTN <a href="matlab:web(''',...
            'http://www.biomecardio.com/matlab/idctn.html'')">here</a>.'])
    end
end

%% Initial Guess with weighted/missing data
function z = InitialGuess(y,I)
    %-- nearest neighbor interpolation (in case of missing values)
    if any(~I(:))
        if license('test','image_toolbox')
            [z,L] = bwdist(I);
            z = y;
            z(~I) = y(L(~I));
        else
        % If BWDIST does not exist, NaN values are all replaced with the
        % same scalar. The initial guess is not optimal and a warning
        % message thus appears.
            z = y;
            z(~I) = mean(y(I));
            warning('MATLAB:smoothn:InitialGuess',...
                ['BWDIST (Image Processing Toolbox) does not exist. ',...
                'The initial guess may not be optimal; additional',...
                ' iterations can thus be required to ensure complete',...
                ' convergence. Increase ''MaxIter'' criterion if necessary.'])    
        end
    else
        z = y;
    end
    %-- coarse fast smoothing using one-tenth of the DCT coefficients
    siz = size(z);
    z = dctn(z);
    for k = 1:ndims(z)
        z(ceil(siz(k)/10)+1:end,:) = 0;
        z = reshape(z,circshift(siz,[0 1-k]));
        z = shiftdim(z,1);
    end
    z = idctn(z);
end


function [y,w] = idctn(y,DIM,w)

%IDCTN N-D inverse discrete cosine transform.
%   X = IDCTN(Y) inverts the N-D DCT transform, returning the original
%   array if Y was obtained using Y = DCTN(X).
%
%   IDCTN(X,DIM) applies the IDCTN operation across the dimension DIM.
%
%   Class Support
%   -------------
%   Input array can be numeric or logical. The returned array is of class
%   double.
%
%   Reference
%   ---------
%   Narasimha M. et al, On the computation of the discrete cosine
%   transform, IEEE Trans Comm, 26, 6, 1978, pp 934-936.
%
%   Example
%   -------
%       RGB = imread('autumn.tif');
%       I = rgb2gray(RGB);
%       J = dctn(I);
%       imshow(log(abs(J)),[]), colormap(jet), colorbar
%
%   The commands below set values less than magnitude 10 in the DCT matrix
%   to zero, then reconstruct the image using the inverse DCT.
%
%       J(abs(J)<10) = 0;
%       K = idctn(J);
%       figure, imshow(I)
%       figure, imshow(K,[0 255])
%
%   See also DCTN, IDSTN, IDCT, IDCT2.
%
%   -- Damien Garcia -- 2009/04, revised 2009/11
%   website: <a
%   href="matlab:web('http://www.biomecardio.com')">www.BiomeCardio.com</a>

% ----------
%   [Y,W] = IDCTN(X,DIM,W) uses and returns the weights which are used by
%   the program. If IDCTN is required for several large arrays of same
%   size, the weights can be reused to make the algorithm faster. A typical
%   syntax is the following:
%      w = [];
%      for k = 1:10
%          [y{k},w] = idctn(x{k},[],w);
%      end
%   The weights (w) are calculated during the first call of IDCTN then
%   reused in the next calls.
% ----------

error(nargchk(1,3,nargin))

y = double(y);
sizy = size(y);

% Test DIM argument
if ~exist('DIM','var'), DIM = []; end
assert(~isempty(DIM) || ~isscalar(DIM),...
    'DIM must be a scalar or an empty array')
assert(isempty(DIM) || DIM==round(DIM) && DIM>0,...
    'Dimension argument must be a positive integer scalar within indexing range.')

% If DIM is empty, a DCT is performed across each dimension

if isempty(DIM), y = squeeze(y); end % Working across singleton dimensions is useless
dimy = ndims(y);

% Some modifications are required if Y is a vector
if isvector(y)
    dimy = 1;
    if size(y,1)==1
        if DIM==1, w = []; return
        elseif DIM==2, DIM=1;
        end
        y = y.';
    elseif DIM==2, w = []; return
    end
end

% Weighing vectors
if ~exist('w','var') || isempty(w)
    w = cell(1,dimy);
    for dim = 1:dimy
        if ~isempty(DIM) && dim~=DIM, continue, end
        n = (dimy==1)*numel(y) + (dimy>1)*sizy(dim);
        w{dim} = exp(1i*(0:n-1)'*pi/2/n);
    end
end

% --- IDCT algorithm ---
if ~isreal(y)
    y = complex(idctn(real(y),DIM,w),idctn(imag(y),DIM,w));
else
    for dim = 1:dimy
        if ~isempty(DIM) && dim~=DIM
            y = shiftdim(y,1);
            continue
        end        
        siz = size(y);
        n = siz(1);
        y = reshape(y,n,[]);
        y = bsxfun(@times,y,w{dim});
        y(1,:) = y(1,:)/sqrt(2);
        y = ifft(y,[],1);
        y = real(y*sqrt(2*n));
        I = (1:n)*0.5+0.5;
        I(2:2:end) = n-I(1:2:end-1)+1;
        y = y(I,:);
        y = reshape(y,siz);
        y = shiftdim(y,1);            
    end
end
        
y = reshape(y,sizy);

end

function [y,w] = dctn(y,DIM,w)

%DCTN N-D discrete cosine transform.
%   Y = DCTN(X) returns the discrete cosine transform of X. The array Y is
%   the same size as X and contains the discrete cosine transform
%   coefficients. This transform can be inverted using IDCTN.
%
%   DCTN(X,DIM) applies the DCTN operation across the dimension DIM.
%
%   Class Support
%   -------------
%   Input array can be numeric or logical. The returned array is of class
%   double.
%
%   Reference
%   ---------
%   Narasimha M. et al, On the computation of the discrete cosine
%   transform, IEEE Trans Comm, 26, 6, 1978, pp 934-936.
%
%   Example
%   -------
%       RGB = imread('autumn.tif');
%       I = rgb2gray(RGB);
%       J = dctn(I);
%       imshow(log(abs(J)),[]), colormap(jet), colorbar
%
%   The commands below set values less than magnitude 10 in the DCT matrix
%   to zero, then reconstruct the image using the inverse DCT.
%
%       J(abs(J)<10) = 0;
%       K = idctn(J);
%       figure, imshow(I)
%       figure, imshow(K,[0 255])
%
%   See also IDCTN, DCT, DCT2.
%
%   -- Damien Garcia -- 2008/06, revised 2009/11
%   website: <a
%   href="matlab:web('http://www.biomecardio.com')">www.BiomeCardio.com</a>

% ----------
%   [Y,W] = DCTN(X,DIM,W) uses and returns the weights which are used by the
%   program. If DCTN is required for several large arrays of same size, the
%   weights can be reused to make the algorithm faster. A typical syntax is
%   the following:
%      w = [];
%      for k = 1:10
%          [y{k},w] = dctn(x{k},[],w);
%      end
%   The weights (w) are calculated during the first call of DCTN then
%   reused in the next calls.
% ----------

error(nargchk(1,3,nargin))

y = double(y);
sizy = size(y);

% Test DIM argument
if ~exist('DIM','var'), DIM = []; end
assert(~isempty(DIM) || ~isscalar(DIM),...
    'DIM must be a scalar or an empty array')
assert(isempty(DIM) || DIM==round(DIM) && DIM>0,...
    'Dimension argument must be a positive integer scalar within indexing range.')

% If DIM is empty, a DCT is performed across each dimension

if isempty(DIM), y = squeeze(y); end % Working across singleton dimensions is useless
dimy = ndims(y);

% Some modifications are required if Y is a vector
if isvector(y)
    dimy = 1;
    if size(y,1)==1
        if DIM==1, w = []; return
        elseif DIM==2, DIM=1;
        end
        y = y.';
    elseif DIM==2, w = []; return
    end
end

% Weighting vectors
if ~exist('w','var') || isempty(w)
    w = cell(1,dimy);
    for dim = 1:dimy
        if ~isempty(DIM) && dim~=DIM, continue, end
        n = (dimy==1)*numel(y) + (dimy>1)*sizy(dim);
        w{dim} = exp(1i*(0:n-1)'*pi/2/n);
    end
end

% --- DCT algorithm ---
if ~isreal(y)
    y = complex(dctn(real(y),DIM,w),dctn(imag(y),DIM,w));
else
    for dim = 1:dimy
        if ~isempty(DIM) && dim~=DIM
            y = shiftdim(y,1);
            continue
        end
        siz = size(y);
        n = siz(1);
        y = y([1:2:n 2*floor(n/2):-2:2],:);
        y = reshape(y,n,[]);
        y = y*sqrt(2*n);
        y = ifft(y,[],1);
        y = bsxfun(@times,y,w{dim});
        y = real(y);
        y(1,:) = y(1,:)/sqrt(2);
        y = reshape(y,siz);
        y = shiftdim(y,1);
    end
end
        
y = reshape(y,sizy);



end



%% Paramètres fixes du problème
clc;clear;

%Lancer cette section avant de lancer la simulation sur simulink
%L'enregistrement des graphes se fais dans les sections suivantes

E=69e9;                                               %Module d'Young de l'anche      (Pa)
a=2.6e-4;                                             %Epaisseur de l'anche           (m)
l=220.0e-4;                                           %Longueur de l'anche            (m)
h=25e-4;                                              %Largeur de l'anche             (m)
rho_a=2699;                                           %Densité de l'anche             (kg/m^3)
f=(1/(2*pi))*(1.875^2)*sqrt((E*a^2)/(12*rho_a*l^4));  %Fréquence propre de l'anche    (Hz)
Te=1e-5;                                              %Période d'échantillonnage      (s)
e0=1e-4;                                              %Distance minimale anche/rigole (m)
rho_0=1.2;                                            %Densité du fluide              (kg/m^3)
mr=11.4e-6;                                           %Masse de l'anche               (kg)
mf=(8/(9*pi))*rho_0*l*h*(l^2+l*h+h^2)/(l+h);          %Masse ajoutée dû au fluide     (kg)
k=((2*pi*f)^2)*mr;                                    %Raideur                        (kg/s²)
tau_amor=20e-3;                                       %Taux d'amortissement           (ss dim.)
c=2*tau_amor*sqrt(k*mr);                              %Amortissement                  (kg/s)
xb=180;                                               %Abscisse du point B            (m)
P0=40;                                                %Pression du soufflet           (Pa)
y0=2e-4;                                              %Position initiale de l'anche   (m) 
x1=20e-4;                                             %Position du capteur de Paero   (m) e<x1<e+h
R=40e-2;                                              %Dist. micro acoustique/anche   (m)
c0=340;                                               %Vitesse moyenne de propagation (m/s)

%% Tracés de la pression acoustique/
clc;

t=P_ac.time';                                         %Vecteur temps                  (s)
subplot(3,1,3),plot(t,P_ac.signals.values(:,1),'k');  
xlabel('Temps (s)');
ylabel('Pression acoustique (Pa)');
title('Evolution temporelle de la pression acoustique');
grid on;

subplot(3,1,1),plot(t,Y.signals.values(:,1),'k');                     
xlabel('Temps (s)');
ylabel('Amplitude de l''anche (m)');
title('Evolution temporelle de l''amplitude de l''anche');
grid on;

subplot(3,1,2),plot(t,Force.signals.values(:,1),'k');                     
xlabel('Temps (s)');
ylabel('Force (N)');
title('Evolution temporelle de la force aérodynamique exercée sur l''anche');
grid on;

%% Spectres de la pression acoustique et du déplacement de l'anche
clc;

fe=1/Te;                                               %Fréquence d'échantilonnage     (Hz)
L1=size(P_ac.signals.values(:,1),1);                   %Dimension du signal P_ac
NFFT1=2^nextpow2(L1);      
bruit=5*randn(NFFT1,1);                                %bruit blanc
S1=fft(P_ac.signals.values(1:L1-1,1),NFFT1)+bruit;     %FFT du signal
f1=fe/2*linspace(0,1,NFFT1/2+1);                       %Vecteur fréquence              (Hz)
subplot(2,1,1),plot(f1(1:NFFT1/8),10*log(abs(S1(1:NFFT1/8))),'k');
xlabel('Fréquence (Hz)');
ylabel('Niveau de pression (dB)');
title('Spectre de la pression acoustique');
grid on;

L2=size(Y.signals.values(:,1),1);                     %Dimension du signal
NFFT2=2^nextpow2(L2);                                   
S2=fft(Y.signals.values(1:L2-1,1),NFFT2);             %FFT du signal Y
f2=fe/2*linspace(0,1,NFFT2/2+1);                      %Vecteur fréquence              (Hz)
subplot(2,1,2),plot(f2(1:NFFT2/8),10*log(abs(S2(1:NFFT2/8))),'k');
xlabel('Fréquence (Hz)');
ylabel('Amplitude (dB)');
title('Spectre du déplacement de l''anche');
grid on;


%% Filtre cavité à deux ports
clc;

f_cav=f;                                              %Fréq. de résonnance cavité    (Hz)
bt=0.5;                                               %Amortissement fluide cavité   ()
R=(sqrt(1./((f1.^2-f_cav^2).^2+bt.*f1.^2)))';         %Réponse de la cavité
subplot(2,1,2), plot(f1,R,'k');
xlabel('Fréquence (Hz)');
ylabel('Amplitude');
title('Réponse en vitesse de la cavité');
grid on;

Module_An_Cav=exp(8)*R.*abs(S1(1:NFFT1/2+1));         %exp(k) : amplification de k dB du signal
Ang=-pi/2-atan((f1.^2-f_cav^2)./(bt*f_cav.*f1))+ (angle(S1(1:NFFT1/2+1)))';
An_Cav=Module_An_Cav.*exp(i.*Ang');
subplot(2,1,1),plot(f1(1:NFFT1/8),10*log(Module_An_Cav(1:NFFT1/8)),'k');
xlabel('Fréquence (Hz)');
ylabel('Amplitude Anche/Cavité (dB)');
title('Spectre de la pression acoustique dans la cavité');
grid on;

%% Sortie audio
clc;

L3=size(An_Cav(:,1),1);                   
NFFT3=2^nextpow2(L3);                                   
Note=ifft(An_Cav);         
T1=Te/2*linspace(0,1,NFFT3/2+1); 

wavwrite(Note(:,1),fe,16,'C:\Users\maison\Desktop\Travail\Projet 5A\Code matlab\Simulink\son_anche.wav');

%Créer un fichier .wav dans le dossier répétoire et renseigner le chemin d'accès au fichier pour la
%création du fichier audio 

%% Recherche fréquences propres d'une poutre hétérogène à section variable
clc;clear;

syms f 

w=2*pi*f;
l=280e-4;
s=0.5*l;

h=25e-4;
b=2.6e-4;
epsi=5.3371e-4;
r=epsi/b;
rho1=7800;
S1=h*b;
E1=210e9;
I1=1/12*h*b^3;
alpha1=sqrt(sqrt((rho1*S1)/(E1*I1)));

rho2=7800;
S2=h*(b+epsi);
E2=210e9;
I2=1/12*h*(b+epsi)^3;
alpha2=sqrt(sqrt((rho2*S2)/(E2*I2)));

n=alpha1/alpha2;

b1=sqrt(w);
b2=n*b1;


A=[0,1,0,1,0,0,0,0;
    1,0,1,0,0,0,0,0;
    0,0,0,0,-sin(b2*l),-cos(b2*l),sinh(b2*l),cosh(b2*l);
    0,0,0,0,-cos(b2*l),sin(b2*l),cosh(b2*l),sinh(b2*l);
    0,0,0,0,-sin(b2*s),-cos(b2*s),-sinh(b2*s),-cosh(b2*s);
    0,0,0,0,-cos(b2*s),sin(b2*s),cosh(b2*s),sinh(b2*s);
    -sin(b1*s),-cos(b1*s),sinh(b1*s),cosh(b1*s),0,0,0,0;
    -cos(b1*s),sin(b1*s),cosh(b1*s),sinh(b1*s),0,0,0,0];

S =factor(simplify(det(A)));


for i=1:400
    Q(i)=subs(S,f,i)
    i=i+1;
end

m=size(Q,2);
f=(1:m);
plot(f,Q);
grid on;
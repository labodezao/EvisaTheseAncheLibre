function  modelsimple()

global  Mat_Modale pente_stat ForceMod Properties_mat Properties_tab_harmo Properties_Cav Properties_air NDDL L Vittemp Postemp bmoy DLS Qtemp hmoy DeltaTemps Voln Kp Pn tnm1 DeltaP Debit_sortie Debit_entree itertime TimeVP Pntemp Vntemp  ;
DLS = 10^-4;
NDDL = 2;
Pref= 2*10^-5;

Properties_mat = [ 4.550*10^-3 , 7800 , 4.259*10^-3 , 0.35*10^-3 , 2.1*10^11 ; 14.850*10^-3 , 7800 , 4.008*10^-3 , 0.2*10^-3 , 2.1*10^11 ; 9*10^-3 , 7800 , 3.699*10^-3 , 0.275*10^-3 , 2.1*10^11 ; 9*10^-3 , 7800 , 3.466*10^-3 , 1.5*10^-3 , 2.1*10^11 ] ; 
% du type [x0,rho0,b0,h0,E0  ;  xi,rhoi,bi,hi,Ei  ;  xn,rhon,bn,hn,En]
%Properties_mat = [ 5*10^-3 , 7800 , 4*10^-3 , 0.5*10^-3 , 2.1*10^11 ; 5*10^-3 , 7800 , 4*10^-3 , 0.5*10^-3 , 2.1*10^11 ;  5*10^-3 , 7800 , 4*10^-3 , 0.5*10^-3 , 2.1*10^11 ] ; 


Properties_Cav = [35*10^-3 ,15*10^-3 ,15*10^-3 , 4 *10^-3 , 4 *10^-3]; 
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
Decoupe_Temps        = 800;
DeltaTemps 			 = T0/(Decoupe_Temps) ; % increment de temps
Temps			     = 0:DeltaTemps:40*T0  ; % Vecteur temps que l'on discrétise en N découpes ;
Fs  = 1/DeltaTemps; % Sample time
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

Vol = Properties_Cav(1)*Properties_Cav(2)*Properties_Cav(3);


Debit_max = 2*290*150*10^-9 ;

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

Flechemax            = 8*10^-4

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

Mat_Modale = Matrice_Modes_Poutre(L);

[Mp,Kp] = matkm();
Mp;
Kp;

Val = eig(Kp(1:NDDL,1:NDDL),Mp(1:NDDL,NDDL+1:end)) 
Freq= sqrt(Val)./(2*pi)


options = odeset('Mass',Mp,'MassSingular','no','MStateDependence','no');


Time_index=zeros(1,length(Temps));

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


pente_stat =  - Flechemax/L  ;
Q0 = [ Deformee_Statique(L)/Mat_Modale(1,1); zeros(NDDL-1,1) ;0; zeros(NDDL-1,1)]



%% de la forme [pos,0000, vit,000]

Debit_entree =   Debit_max 
 if (Debit_entree ~= 0)


Pn = Properties_air(4);
tnm1         = 0;
DeltaP       = 0;
Debit_sortie = 0;
itertime     = 0;



Voln = Vol


 ode45(@Eq_Lame, Temps, Q0, options );

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


TimeVolPress = TimeVP(Time_index);

size(Qtemp)


Q        = smoothn(Qtemp,'robust')                  ;
Pos      = smoothn(Postemp(Time_index),'robust')    ;
Vit      = smoothn(Vittemp(Time_index),'robust')    ;
Force    = smoothn(ForceMod(Time_index),'robust')   ;
PressCav = smoothn(Pntemp(Time_index),'robust')     ;
VolCav   = smoothn(Vntemp(Time_index),'robust')     ;

figure
plot(Pos)
xlabel('tim(s)')
ylabel('Pos(s)')

figure
plot(Q)
xlabel('tim(s)')
ylabel('Debit sortie(m3/s)')

figure
plot(Vit)
xlabel('tim(s)')
ylabel('Vit(m/s)')

figure
plot(Force)
xlabel('tim(s)')
ylabel('Force(N)')

figure
plot(VolCav)
xlabel('tim(s)')
ylabel('Vol(m3)')

figure
plot(PressCav)
xlabel('tim(s)')
ylabel('Pression(Pa)')

savefile = 'MatRes.mat';
save( savefile, 'TimeVolPress' ,'Q','Pos','Vit','Vol','Debit_entree','pente_stat' ); 


end
 
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
function dQ = Eq_Lame(t,Q) % on met ici dans d le second membre donc Delta pression entre l'extrados et l'intrados de la lame u(1) est X alors que u(2) est sa dérivée

global  Voln Pn Qtemp Kp tnm1 TimeVP Pntemp Vntemp itertime Debit_entree NDDL L Postemp Vittemp Mat_Modale ForceMod ;


if tnm1==0
dQ=Q;


else
    
Deltat = t-tnm1;

%%

Qstatic =[ Deformee_Statique(L)/Mat_Modale(1,1); zeros(NDDL-1,1) ;0; zeros(NDDL-1,1)];

Q = Q + Qstatic;

[Fp,Volnp1,Pnp1] = matf(Q ,Debit_entree, Voln, Pn, Deltat);
dQ = (Fp-Kp*Q); 

%%

TimeVP(itertime)            = t                                 ;
Pntemp(itertime)            = Pn                                ;
Vntemp(itertime)            = Voln                              ;
Postemp(itertime)           = Mat_Modale(1,1:NDDL)*Q(1 : NDDL)   ;
Vittemp(itertime)           = Mat_Modale(2,NDDL+1:end)*Q(NDDL+1:end)       ;
ForceMod(itertime)          = Fp(1)   ;
Qtemp(itertime)             = Debit_entree                      ;
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
gamma_sigmo = Properties_Cav(5);
beta_sigmo = -2200;
gamma_sigmo2 =-Properties_Cav(4);

DeltaP =  ( Pn - 10^5);
Posn = Mat_Modale(1,1:NDDL)*Q(1 : NDDL);
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
      TQtot_open = abs(TQ1_open + TQ2_open + TQ3_open) ;



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
      TQtot_close = abs(TQ1_close + TQ2_close + TQ3_close)                            ;


 TQ_clap =  abs(40.52*0.91^(abs(atand(Posn/L))));

 
pondersigmoa = exp(beta_sigmo*(Posn + gamma_sigmo))/(1+exp(beta_sigmo*(Posn + gamma_sigmo))) + (1/(1+exp(beta_sigmo*(Posn+gamma_sigmo2))))^2  ;

 Funct_Ksi = TQtot_close/S_Inter^2 + ((TQtot_open + TQ_clap) / S_Trou^2 - TQtot_close/S_Inter^2)*pondersigmoa ;    
 Debit_sortie = sign(DeltaP)*(abs(2*DeltaP)/(Properties_air(2)*Funct_Ksi) )^0.5     ;

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
 
Qlf= Qlf + Qltemp;
  
 end

 
gammacv= Properties_air(3);

dV   = DeltaTemps*( Debit_entree - Debit_sortie - Qlf) ;
   
   Volume_Cavitenp1 = Vn  - dV  ;  
   Pnp1 = Pn*(Vn/Volume_Cavitenp1)^gammacv  ;

 
   DeltaP = (   Pnp1 -Properties_air(4))                             ; %

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


Mp = [ zeros(NDDL) M; -eye(NDDL) zeros(NDDL)] ;
Kp = [ K zeros(NDDL) ; zeros(NDDL) eye(NDDL) ] ;



Val = eig(K,M) ;

Freq= sqrt(Val)./(2*pi);

end


function [Mat_Mod] = Matrice_Modes_Poutre (x)
global NDDL L ;


Mat_Mod=zeros(2,NDDL);
for i_mod = 1:NDDL
    
[Bi,sig] = BL_Sigma(i_mod);
 
Mat_Mod(1,i_mod) = (cosh(Bi/L*x)-cos(Bi/L*x)-sig*(sinh(Bi/L*x)-sin(Bi/L*x)))
Mat_Mod(2,i_mod+NDDL) = (cosh(Bi/L*x)-cos(Bi/L*x)-sig*(sinh(Bi/L*x)-sin(Bi/L*x)))
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

%% Find the extreme maxim values 
% and the corresponding indexes
%oRIGINAL:
% extrMaxValue = y(find( diff(sign(diff(y)) )==-2  )+1);
% extrMaxIndex =   find(diff(sign(diff(y)))==-2)+1;
%%---------------------------------------------------- 

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



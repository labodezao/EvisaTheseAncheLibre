function varargout = accomodel(varargin)
% ACCOMODEL M-file for accomodel.fig
%      ACCOMODEL, by itself, creates a new ACCOMODEL or raises the existing
%      singleton*.
%
%      H = ACCOMODEL returns the handle to a new ACCOMODEL or the handle to
%      the existing singleton*.
%
%      ACCOMODEL('CALLBACK',hObject,eventData,handles,...) calls the local
%      end function named CALLBACK in ACCOMODEL.M with the given input arguments.
%
%      ACCOMODEL('Property','Value',...) creates a new ACCOMODEL or raises the
%      existing singleton*.  Starting from the left, property value pairs are
%      applied to the GUI before accomodel_OpeningFcn gets called.  An
%      unrecognized property name or invalid value makes property application
%      stop.  All inputs are passed to accomodel_OpeningFcn via varargin.
%
%      *See GUI Options on GUIDE's Tools menu.  Choose "GUI allows only one
%      instance to run (singleton)".
%
% See also: GUIDE, GUIDATA, GUIHANDLES

% Edit the above text to modify the response to help accomodel

% Last Modified by GUIDE v2.5 13-Feb-2015 12:32:10

% Begin initialization code - DO NOT EDIT
gui_Singleton = 1;
gui_State = struct('gui_Name',       mfilename, ...
                   'gui_Singleton',  gui_Singleton, ...
                   'gui_OpeningFcn', @accomodel_OpeningFcn, ...
                   'gui_OutputFcn',  @accomodel_OutputFcn, ...
                   'gui_LayoutFcn',  [] , ...
                   'gui_Callback',   []);
if nargin && ischar(varargin{1})
    gui_State.gui_Callback = str2func(varargin{1});
end

if nargout
    [varargout{1:nargout}] = gui_mainfcn(gui_State, varargin{:});
else
    gui_mainfcn(gui_State, varargin{:});
end
% End initialization code - DO NOT EDIT


% --- Executes just before accomodel is made visible.
end
function accomodel_OpeningFcn(hObject, eventdata, handles, varargin)
% This end function has no output args, see OutputFcn.
% hObject    handle to figure
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)
% varargin   command line arguments to accomodel (see VARARGIN)

% Choose default command line output for accomodel
handles.output = hObject;

% Update handles structure
guidata(hObject, handles);

% UIWAIT makes accomodel wait for user response (see UIRESUME)
% uiwait(handles.Main);
setappdata(0  , 'hMainGui'    , gcf);
setappdata(gcf  , 'Reed_FileName'    , 'Reed_Selected.mat');
setappdata(gcf, 'fhUpdateAxes', @Load_Reed);

%setappdata(gcf,   'Reed_Selected'    , 'Reed_Selected.mat');


% --- Outputs from this end function are returned to the command line.
end
function varargout = accomodel_OutputFcn(hObject, eventdata, handles)
% varargout  cell array for returning output args (see VARARGOUT);
% hObject    handle to figure
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Get default command line output from handles structure
varargout{1} = handles.output;




% --------------------------------------------------------------------
end
function Menu_Fichier_Callback(hObject, eventdata, handles)
% hObject    handle to Menu_Fichier (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)


% --------------------------------------------------------------------
end
function Menu_Edition_Callback(hObject, eventdata, handles)
% hObject    handle to Menu_Edition (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)


% --------------------------------------------------------------------
end
function F_Rdatabase_Callback(hObject, eventdata, handles)
% hObject    handle to F_Rdatabase (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

end
% --------------------------------------------------------------------
function uipushtool4_ClickedCallback(hObject, eventdata, handles)
% hObject    handle to uipushtool4 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

end
% --- Executes on button press in Button_Compute.
 function Button_Compute_Callback(hObject, eventdata, handles)
% hObject    handle to Button_Compute (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

global  Mat_Modale pente_stat ForceMod Properties_mat Properties_tab_harmo Properties_Cav Properties_air Tablo_plaquette NDDL L Vittemp Postemp bmoy DLS Qtemp hmoy DeltaTemps Voln Kp Pn tnm1 DeltaP Debit_sortie Debit_entree itertime TimeVP Pntemp Vntemp  ;

%% init_var

Properties_Cav= get(handles.Tab_propcav,'Data');
Properties_tab_harmo= get(handles.Tab_propsb,'Data');
Properties_air= get(handles.Tab_propair,'Data');
Tablo_paramodel= get(handles.Tab_paramodel,'Data');
Tablo_bound= get(handles.Tab_bound,'Data');
Tablo_plaquette = get(handles.Plaquette_Tab,'Data');
Properties_mat= get(handles.Prop_Mat_Tab,'Data');


DLS = Tablo_plaquette(3);
NDDL = Tablo_paramodel(3);
Pref= 2*10^-5;


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
Raideur_Equival		 = 3*Emoy*Imoy/(L^3)    ;% raideur equivalente de la poutre pour le systeme a 1 ddl
wo				     = sqrt(Raideur_Equival/Masse) ;  % Puslation propre estim√©e de la lame
T0					 = 2*pi/wo   	 ;% Periode propre estim√©e de l'osilation de l'anche
Decoupe_Temps        = Tablo_paramodel(1);
DeltaTemps 			 = T0/(Decoupe_Temps)  ;% increment de temps
Temps			     = 0:DeltaTemps:Tablo_paramodel(2)*T0  ; % Vecteur temps que l'on discr√©tise en N d√©coupes ;
Fs  = 1/DeltaTemps % Sample time
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%Boundaries%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


Vol = Properties_Cav(1)*Properties_Cav(2)*Properties_Cav(3);


Debit_max = Tablo_bound(1);


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

Flechemax      =  Tablo_bound(2);


Mat_Modale = Matrice_Modes_Poutre(L);

[Mp,Kp] = matkm();
Val = eig(Kp(1:NDDL,NDDL+1:end),Mp(1:NDDL,1:NDDL)) 
Freq= sqrt(Val)./(2*pi)



options = odeset('Mass',Mp,'MassSingular','no','MStateDependence','no','OutputFcn',@odeplot);


Time_index=zeros(1,length(Temps));

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


pente_stat =  - Flechemax/L  ;
Q0 = [zeros(NDDL ,1);Deformee_Statique(L)/Mat_Modale(1,1); zeros(NDDL-1)]
% de la forma Vit0 Pos0
%Kp*Q0

Debit_entree =   Debit_max 
 if (Debit_entree ~= 0)


Pn = Properties_air(4);
tnm1         = 0;
DeltaP       = 0;
Debit_sortie = 0;
itertime     = 0;



Voln = Vol


[Time,Oderes]= ode45(@Eq_Lame, Temps, Q0, options );

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


Vit_Pos=Mat_Modale*Oderes';

Vit      = Vit_Pos(1,:);
Pos      = Vit_Pos(2,:);
Force    = smoothn(ForceMod(Time_index),'robust')   ;
PressCav = smoothn(Pntemp(Time_index),'robust')     ;
VolCav   = smoothn(Vntemp(Time_index),'robust')     ;



 %%%%%%%%%%%%%%%%%%%---------TRESP--------------%%%%%%%%%%%%%%%%%%%%%
[env] = envelope(Time,Pos);
figure
plot(Time(1:length(env)),env,Time,Pos)
S = lsiminfo(env,Time(1:length(env)));
irest = find( Time(1:length(env)) > S.SettlingTime ,1)
TResp = S.SettlingTime 

if((irest > 0.90*length(Pos)))
irest=floor(0.90*length(Pos));
end

extrMaxValue = find( diff(sign(diff(Pos(irest:end))) )==-2 ,4 )+1;
iend =    extrMaxValue(end);
Time(irest+iend)

n=length(Pos(irest:irest+iend))-1;%  /* graph it ñ try zooming while its upÖnot much visible until you do*/>n=length(wave)-1;                                             
NFFT = 2^nextpow2(n); % Next power of 2 from length of y

Y = fft(Pos(irest:irest+iend),NFFT)/L;
f = Fs/2*linspace(0,1,NFFT/2+1);

% Plot single-sided amplitude spectrum.
figure
plot(f,2*abs(Y(1:NFFT/2+1))) 
title('Single-Sided Amplitude Spectrum of y(t)')
xlabel('Frequency (Hz)')
ylabel('|Y(f)|')


 
 
%min max values
ms1=Fs/(Freq(1)*8);                 % maximum speech Fx at 1000Hz
ms20=Fs/(Freq(1)*0.8);                  % minimum speech Fx at 50Hz
% do fourier transform of windowed signal
Y=fft(Pos(irest:irest+iend)').*hamming(length(Pos(irest:irest+iend)));
% cepstrum is DFT of log spectrum
C=fft(log(abs(Y)+eps));

if(length(C)> floor(ms20)-1)
    [~,fx]=max(abs(C(floor(ms1):floor(ms20)-1)));
%---------------------------------------------------------------------------
freqtemp=Fs/(ms1+fx-1);
Ofrequency= freqtemp
else
   freqtemp=0;
end





TotDSP = spl(PressCav,'air');

Norm_Pos=1/2*Pos/(max(Pos))
Fs_wav= 1/(TimeVolPress(2)-TimeVolPress(1));
wavwrite(Norm_Pos,Fs_wav,16,['reed','.wav']);               %/* read file into memory */


 figure
 plot(Time,Vit)
 xlabel('tim(s)')
 ylabel('vit(m/s)')
 title(['Vit Vs time for Deb=',num2str(Debit_entree),'m3/s Vol=',num2str(Vol),'m3 and Def stat=',num2str(pente_stat),'m '])
 
 
 
figure
plot(Time,Pos)
xlabel('tim(s)')
ylabel('Pos(s)')
title(['Position Vs time for Deb=',num2str(Debit_entree),'m3/s Vol=',num2str(Vol),'m3 and Def stat=',num2str(pente_stat),'m '])



figure
plot(TimeVolPress,Force)
xlabel('tim(s)')
ylabel('Force(N)')
title(['Force over reed Vs time for Deb=',num2str(Debit_entree),'m3/s Vol=',num2str(Vol),'m3 and Def stat=',num2str(pente_stat),'m '])

figure
plot(TimeVolPress,VolCav)
xlabel('tim(s)')
ylabel('Vol(m3)')
title(['Cavity volume Vs time for Deb=',num2str(Debit_entree),'m3/s Vol=',num2str(Vol),'m3 and Def stat=',num2str(pente_stat),'m '])

figure
plot(TimeVolPress,PressCav)
xlabel('tim(s)')
ylabel('Pression(Pa)')
title(['Pression Vs time for Deb=',num2str(Debit_entree),'m3/s Vol=',num2str(Vol),'m3 and Def stat=',num2str(pente_stat),'m '])

savefile = 'MatRes.mat';
save( savefile, 'TimeVolPress' ,'Pos','Vit','Time',    'Vol','Debit_entree','Flechemax'          ,'TotDSP' ); 


end

% --------------------------------------------------------------------
end 
function E_Rdata_Callback(hObject, eventdata, handles)
% hObject    handle to E_Rdata (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)
reeddatabase;


% --- Executes on selection change in popupmenu1.
end 
function popupmenu1_Callback(hObject, eventdata, handles)
% hObject    handle to popupmenu1 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: contents = cellstr(get(hObject,'String')) returns popupmenu1 contents as cell array
%        contents{get(hObject,'Value')} returns selected item from popupmenu1


% --- Executes during object creation, after setting all properties.
end 
function popupmenu1_CreateFcn(hObject, eventdata, handles)
% hObject    handle to popupmenu1 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: popupmenu controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end


% --- Executes when entered data in editable cell(s) in uitable1.
end 
function uitable1_CellEditCallback(hObject, eventdata, handles)
% hObject    handle to uitable1 (see GCBO)
% eventdata  structure with the following fields (see UITABLE)
%	Indices: row and column indices of the cell(s) edited
%	PreviousData: previous data for the cell(s) edited
%	EditData: string(s) entered by the user
%	NewData: EditData or its converted form set on the Data property. Empty if Data was not changed
%	Error: error string when failed to convert EditData to appropriate value for Data
% handles    structure with handles and user data (see GUIDATA)


% --------------------------------------------------------------------
end 
function uipushtool5_ClickedCallback(hObject, eventdata, handles)
% hObject    handle to uipushtool5 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)
reeddatabase;






%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%  Model Code %%%%%%%%%%%%%%%%%%%%%%%%%%%%%





%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%  Data Analysis Code %%%%%%%%%%%%%%%%%%%%%




% --- Executes on button press in Button_Open.
end 
function Button_Open_Callback(hObject, eventdata, handles)
% hObject    handle to Button_Open (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

file = uigetfile('*.mat');
        if ~isequal(file, 0)  
            load(file,'Properties_mat','Plaquette_mat')  
            set(handles.Prop_Mat_Tab,'Data', Properties_mat  );
            set(handles.Plaquette_Tab,'Data', Plaquette_mat  ); 
            set(handles.Prop_Mat_Tab,'Data', Properties_mat  );
            set(handles.Pan_reed_data,'Visible','on');
            set(handles.Nbr_troncon,'Data', length(Properties_mat(:,1)));
            
            if length(Properties_mat(:,1)) > 1
            for i = 1:length(Properties_mat(:,1))-1   
            yreed(2*i) = Properties_mat(i,4);    
            yreed(2*i+1) = Properties_mat(i+1,4); 
            xreed(2*i) = sum(Properties_mat(1:i,1)) ;
            xreed(2*i+1) =xreed(2*i) ;
            end
            xreed = [0,xreed(2:end),sum(Properties_mat(:,1)),sum(Properties_mat(:,1))];
            yreed= [Properties_mat(1,4),yreed(2:end),Properties_mat(end,4),0];
            else
             xreed = [0,Properties_mat(1,1),Properties_mat(1,1)];
             yreed= [Properties_mat(1,4),Properties_mat(1,4),0];    
            end
            area(handles.Axes_reed,xreed,yreed);            
        end


% --- Executes on button press in pushbutton4.
end 


function pushbutton6_Callback(hObject, eventdata, handles)
% hObject    handle to pushbutton6 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)


% --- Executes on button press in pushbutton5.
end
function pushbutton5_Callback(hObject, eventdata, handles)
% hObject    handle to pushbutton5 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)


% --- Executes on button press in checkbox2.
end
function checkbox2_Callback(hObject, eventdata, handles)
% hObject    handle to checkbox2 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hint: get(hObject,'Value') returns toggle state of checkbox2


% --- Executes on button press in checkbox1.
end
function checkbox1_Callback(hObject, eventdata, handles)
% hObject    handle to checkbox1 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hint: get(hObject,'Value') returns toggle state of checkbox1


% --- Executes on button press in pushbutton7.
end 
function pushbutton7_Callback(hObject, eventdata, handles)
% hObject    handle to pushbutton7 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)
modeloptins


% --- Executes on button press in Button_computestatic.
end 
function Button_computestatic_Callback(hObject, eventdata, handles)
% hObject    handle to Button_computestatic (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

paramsmodel = get(handles.Tab_paramodel,'Data');
NDDL=paramsmodel(3);

if NDDL <1 
paramsmodel(3)=1;
set(handles.Tab_paramodel,'Data',paramsmodel);
NDDL = 1 ;
end

Calc_def_mod(   get(handles.Prop_Mat_Tab,'Data'  ), handles );
deftrace(          get(handles.Prop_Mat_Tab,'Data'  ),NDDL, handles );



% --- Executes on button press in pushoptions.
end 
function pushoptions_Callback(hObject, eventdata, handles)
% hObject    handle to pushoptions (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)



end
function  deftrace(Properties_mat,NDDL ,handles)

syms x ; 
%Properties_mat = [ 4.550*10^-3 , 7800 , 4.259*10^-3 , 0.35*10^-3 , 2.1*10^11 ; 14.850*10^-3 , 7800 , 4.008*10^-3 , 0.2*10^-3 , 2.1*10^11 ; 9*10^-3 , 7800 , 3.699*10^-3 , 0.275*10^-3 , 2.1*10^11 ; 9*10^-3 , 7800 , 3.466*10^-3 , 1.5*10^-3 , 2.1*10^11 ] ; 
% du type [x0 (longeur tronÁon ),rho0 (densitÈ moyenne du troncon) ,b0 (largeur -constante- de l'anche) ,h0 (Epaisseur) ,E0 (Module Young)  ;  xi,rhoi,bi,hi,Ei  ;  xn,rhon,bn,hn,En] 
% Note :
% Rem  :


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
 end
 
M(i,j) = (M_ij);
K(i,j) = (K_ij);
 end


end


Val = eig(K,M) ;

Freq= sqrt(Val)./(2*pi);

set(handles.Freq,'Data', Freq)
set(handles.Axes_FFT, 'Visible', 'on');
set(handles.axes_deformee, 'Visible', 'on');

stem(handles.Axes_FFT,Freq,ones(size(Freq)));

end

function Calc_def_mod(Properties_mat, handles)
%% calcul de la dÈformÈe du iËme mode   
 % du type [x0 (longeur tronÁon ),rho0 (densitÈ moyenne du troncon) ,b0 (largeur -constante- de l'anche) ,h0 (Epaisseur) ,E0 (Module Young)  ;  xi,rhoi,bi,hi,Ei  ;  xn,rhon,bn,hn,En] 
% Note :
% Rem  :
   L= sum(Properties_mat(:,1));
   P=1;
   [nsection,nparam] = size(Properties_mat) ;
   X=zeros(1,50*nsection);
   Def=zeros(1,50*nsection);
   Xi=0;
   Defi=0;
   Penti=0;
   xn = 0;
   xnp1=  Properties_mat(1,1);
   pente(1)=0;
   fleche(1)=0;
   A=0;
   B=0;
   for k=1:nsection  
   
   
   if k>1
   
   
   xn = xnp1;
   xnp1= xnp1 + Properties_mat(k,1);
   Xtr = xn: (xnp1-xn)/100 : xnp1;
   
   
   A  = pente(k) + P/(24*Properties_mat(k,5)*Properties_mat(k,3)*Properties_mat(k,4)^3/12)*( 4*Xtr(1)^3 - 12*L*Xtr(1)^2 + 12*Xtr(1)*L^2 );
   B = fleche(k) + P*Xtr(1)^2/(24*Properties_mat(k,5)*Properties_mat(k,3)*Properties_mat(k,4)^3/12)*(Xtr(1)^2 - 4*L*Xtr(1) + 6*L^2) - A*Xtr(1) ;
   
   
   
   Deftr = -P*Xtr(2:end).^2/(24*Properties_mat(k,5)*Properties_mat(k,3)*Properties_mat(k,4)^3/12).*(Xtr(2:end).^2-4*L*Xtr(2:end)+6*L^2) + A*Xtr(2:end) + B;
   Penttr = -P/(24*Properties_mat(k,5)*Properties_mat(k,3)*Properties_mat(k,4)^3/12)*( 4*Xtr(2:end).^3 - 12*L*Xtr(2:end).^2 + 12*Xtr(2:end)*L^2) + A; 
   
   Xi= [Xi, Xtr(2:end)];
   Defi = [Defi, Deftr];
   Penti = [Penti,Penttr];
   
       else
 
  Xtr = xn: (xnp1-xn)/100 : xnp1;
  Deftr = -P*(Xtr).^2/(24*Properties_mat(k,5)*Properties_mat(k,3)*Properties_mat(k,4)^3/12).*(Xtr.^2 - 4*L*Xtr + 6*L^2);
  Penttr = -P/(24*Properties_mat(k,5)*Properties_mat(k,3)*Properties_mat(k,4)^3/12)*( 4*Xtr.^3 - 12*L*Xtr.^2 + 12*Xtr*L^2) + A;
 
  Xi= [Xi, Xtr];
   Defi = [Defi, Deftr];
   Penti = [Penti,Penttr];
   
       end
       
   pente(k+1)  =  Penttr(end);
   fleche(k+1) = Deftr(end);
   
   end

   
   
X   = Xi(2:end)  ;

Def = Defi(2:end)/max(abs(Defi)) ;
Pent= Penti(2:end);


plot(handles.axes_deformee,X',Def');



% --- Executes on button press in Button_Save.
end 
function Button_Save_Callback(hObject, eventdata, handles)
% hObject    handle to Button_Save (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)
Properties_mat = get(handles.Prop_Mat_Tab,'Data'  );
Plaquette_mat = get(handles.Plaquette_Tab,'Data'  );

uisave({'Properties_mat','Plaquette_mat'},'*.mat');


% --- Executes on button press in pushbutton16.
end 

function pushbutton16_Callback(hObject, eventdata, handles)
% hObject    handle to pushbutton16 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)
set(handles.Prop_Mat_Tab,'Data', zeros(1,5) );
set(handles.Plaquette_Tab,'Data', zeros(1,2) );

cla(handles.Axes_reed);
set(handles.Pan_reed_data,'Visible','on');


% --- Executes on button press in Button_Saveparams.
end
function Button_Saveparams_Callback(hObject, eventdata, handles)
% hObject    handle to Button_Saveparams (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)


% --- Executes on button press in Button_Open_param.
end
function Button_Open_param_Callback(hObject, eventdata, handles)
% hObject    handle to Button_Open_param (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)


% --- Executes on button press in pushbutton20.
end 
function pushbutton20_Callback(hObject, eventdata, handles)
% hObject    handle to pushbutton20 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)


% --- Executes on button press in Button_Saveresults.
end
function Button_Saveresults_Callback(hObject, eventdata, handles)
% hObject    handle to Button_Saveresults (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)


% --- Executes on button press in Button_Soundsynthesis.
end
function Button_Openresults_Callback(hObject, eventdata, handles)
% hObject    handle to Button_Soundsynthesis (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)


% --- Executes during object deletion, before destroying properties.
end 
function Tab_paramodel_DeleteFcn(hObject, eventdata, handles)
% hObject    handle to Tab_paramodel (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)







%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

end 
function [ds] = Deformee_Statique(x)
% x      		: [ParamÔøΩtre de la fonction : position longitudinale ou on recheche la d√©form√©e modale]
% ds 			: [Valeur de la d√©form√©e statique en x]
%----------------------------------------------------------------------
 global pente_stat;
 ds=pente_stat*x;
 
 

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
end 
function dQ = Eq_Lame(t,Q) % on met ici dans d le second membre donc Delta pression entre l'extrados et l'intrados de la lame u(1) est X alors que u(2) est sa d√©riv√©e

global  Voln Pn  Kp tnm1 TimeVP Pntemp Vntemp itertime Debit_entree NDDL   Mat_Modale ForceMod ;


if tnm1==0
dQ=Q;


else
    
Deltat = t-tnm1;

%%

%Qstatic =[zeros(NDDL ,1);Deformee_Statique(L)/Mat_Modale(2,1); zeros(NDDL-1)];
%possiblement faux!


%Q = Q + Qstatic;

[Fp,Volnp1,Pnp1] = matf(Q ,Debit_entree, Voln, Pn, Deltat);
dQ = (Fp-Kp*Q); 

%%

TimeVP(itertime)            = t                                 ;
Pntemp(itertime)            = Pn                                ;
Vntemp(itertime)            = Voln                              ;
ForceMod(itertime)          = Mat_Modale(1,1:NDDL)*Fp(1:NDDL)                             ;
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
Voln = Volnp1                                                   ;
Pn = Pnp1                                                       ;

end
tnm1 =t                                                         ;
itertime = itertime +1                                          ;



%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
end

function [Fp , Volume_Cavitenp1,Pnp1 ] = matf(Q, Debit_entree , Vn, Pn, DeltaTemps)
global Mat_Modale Properties_mat Properties_Cav Tablo_plaquette Properties_air NDDL L Debit_sortie  DLS Properties_tab_harmo bmoy hmoy 
  syms x  ;
[nsection,nparam] = size(Properties_mat) ;  
gamma_sigmo = Tablo_plaquette(2);
beta_sigmo = -2200;
gamma_sigmo2 =-Tablo_plaquette(1);

DeltaP =  ( Pn - 10^5); %Pa
Posn = Mat_Modale(2,NDDL+1:end)*Q(NDDL+1 : end);
S_Table        = Properties_tab_harmo(2)*Properties_tab_harmo(1)  ; %// m2
S_Inter        = DLS*(2*L+ bmoy +2*DLS)  ;              %m2              
S_Trou         = 2*(L+DLS)*DLS+DLS*(Properties_mat(end,3)) ; 
Per_Lame = 4*DLS+4*L+2*(Properties_mat(end,3)+2*DLS)+2*DLS;
Per_Trou = 2*(L+DLS)+2*(Properties_mat(end,3)+2*DLS);
S_Anche        = sum(Properties_mat(:,1).*Properties_mat(:,3)); %OK
if (Posn>0)
    Etrou=Tablo_plaquette(1);
else
    Etrou=Tablo_plaquette(2);
end
    
Eplame= hmoy;

if(Debit_sortie ==0)
Re_open = Debit_entree*DLS/(S_Trou*Properties_air(1));%su
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
      TQ1_open = Kpc_open                                     ; %termes pertes de charges reguli√®res su
      TQ2_open = (1-S_Trou/S_Table)^2  ; %terme pertes de charges singuli√®res elargissement                   su
      TQ3_open = (1/0.65 - 1)^2  ; %terme pertes de charges singuli√®res retrecissement  su      
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
      TQ1_close = Kpc_close               ; %termes pertes de charges reguli√®res
      TQ2_close = (1-S_Inter/S_Table)^2                                          ; %terme pertes de charges singuli√®res elargissement
      TQ3_close = (1/0.65 - 1)^2 ; %terme pertes de charges singuli√®res retrecissement   
      TQtot_close = TQ1_close + TQ2_close + TQ3_close                            ;


 TQ_clap =  2.6116*(abs(atan(Posn/L)))^(-1.06);

 
pondersigmoa = exp(beta_sigmo*(Posn + gamma_sigmo))/(1+exp(beta_sigmo*(Posn + gamma_sigmo))) + (1/(1+exp(beta_sigmo*(Posn+gamma_sigmo2))))^2  ;

 Funct_Ksi = TQtot_close*Per_Lame*Etrou/S_Inter^3 + ((TQtot_open + TQ_clap)*Per_Trou*Eplame / S_Trou^3 - TQtot_close*Per_Lame*Etrou/S_Inter^3)*pondersigmoa ;    
 Debit_sortie = sign(DeltaP)*(8*abs(DeltaP)/(Properties_air(2)*Funct_Ksi) )^0.5     ;

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
Qli= Q(j)*Mat_Modale(1,j)*Properties_mat( k,3 )*((L*(sin((Bi*xn)/L) - sin((Bi*xnp1)/L)))/Bi - (L*(sinh((Bi*xn)/L) - sinh((Bi*xnp1)/L)))/Bi + (L*Si*(cos((Bi*xn)/L) - cos((Bi*xnp1)/L)))/Bi + (L*Si*(cosh((Bi*xn)/L) - cosh((Bi*xnp1)/L)))/Bi);
Qltemp= Qltemp +Qli;
  end
 
Qlf= Qlf + Qltemp;
  
 end
 
gammacv= Properties_air(3);%su

dV   = DeltaTemps*( -Debit_entree + Debit_sortie + Qlf) ;%m3
   
   Volume_Cavitenp1 = Vn  + dV  ;  %m3
   Pnp1 = Pn*(Vn/Volume_Cavitenp1)^gammacv  ;%pa
   DeltaP = (   Pnp1 -Properties_air(4))                              ;%pa


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




%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
end

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
  
M(i,j) = (M_ij);
K(i,j) = (K_ij);
 end

end


Mp = [M zeros(NDDL);zeros(NDDL) -eye(NDDL)] ;
Kp = [zeros(NDDL) K;  eye(NDDL) zeros(NDDL)] ;
% validÈ

%Val = eig(K,M) ;

%Freq= sqrt(Val)./(2*pi);




end

function [Mat_Mod] = Matrice_Modes_Poutre (x)
global NDDL L ;


Mat_Mod=zeros(2,NDDL);
for i_mod = 1:NDDL
    
[Bi,sig] = BL_Sigma(i_mod);
 
Mat_Mod(1,i_mod) = (cosh(Bi/L*x)-cos(Bi/L*x)-sig*(sinh(Bi/L*x)-sin(Bi/L*x)));
Mat_Mod(2,i_mod+NDDL) = (cosh(Bi/L*x)-cos(Bi/L*x)-sig*(sinh(Bi/L*x)-sin(Bi/L*x)));


end

Mat_Mod


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
end

function [Bl,sigma] = BL_Sigma(n)
%/ n            : numero du mode ;
% x      		: [Parametre de la fonction : position longitudinale ou on recheche la d√©form√©e modale]
% Offset 		: [valeur de l'offset du √† la d√©form√©e statique en x]
% Bl     		: [Longeur de l'anche : Variable Externe]
% sigma 	 	: [Longeur de l'anche : Variable Externe]
% L 	: [Longeur de l'anche : Variable Externe]
% f 			: [variable de sortie de la fonction : donne la valeur de la d√©form√©e modale en un point x]
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


% --- Executes on button press in pushbutton4.
function pushbutton4_Callback(hObject, eventdata, handles)
% hObject    handle to pushbutton4 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)
Calc_Tresp(TimePressVol,Pos);
fft_calc(TimePressVol,Pos);
Calc_Dsp()

end

function [TResp,irest] =    Calc_Tresp(Temps,Signal)
 %%%%%%%%%%%%%%%%%%%---------TRESP--------------%%%%%%%%%%%%%%%%%%%%%
[env] = envelope(signal',smoothn(Pos',10^3));
S = lsiminfo(env,signal(1:length(env)));
irest = find( TimeVolPress(1:length(env)) > S.SettlingTime ,1);
TResp = S.SettlingTime ;

if((irest > 0.90*length(Pos)))
irest=floor(0.90*length(Pos))
end


    
end
%%%%%%%%%%%%%%%%%%%%%%%%------FFT------%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

function [C, Ofrequency]=fft_calc(Temps,Signal)

%Fs = 1/((Temps(2)- Tenps(1))/20) ;% Sampling frequency
 %FFTY = fft(InterPos(T0:T1)-mean(InterPos(T0:T1))*ones(size(InterPos(T0:T1))),length(InterPos(T0:T1)));
 %Pyy = FFTY.*conj(FFTY)/length(InterPos(T0:T1));
 %freq = Fs/length(InterPos(T0:T1))*(0:2047);


%min max values
ms1=Fs/(Freq(1)*8);                 % maximum speech Fx at 1000Hz
ms20=Fs/(Freq(1)*0.8);                  % minimum speech Fx at 50Hz
% do fourier transform of windowed signal
Y=fft(smoothn(Pos(irest:end),10^6).*hamming(length(Pos(irest:end))));
% cepstrum is DFT of log spectrum
C=fft(log(abs(Y)+eps));


if(length(C)> floor(ms20)-1)
    [~,fx]=max(abs(C(floor(ms1):floor(ms20)-1)));
%---------------------------------------------------------------------------
freqtemp=Fs/(ms1+fx-1);
Ofrequency= freqtemp;
else
   freqtemp=0;
end

%t=0:1/fs:(length(wave)-1)/fs;                                   % /* and get sampling frequency */
%plot(t,wave); 
%n=length(wave)-1;%  /* graph it ñ try zooming while its upÖnot much visible until you do*/>n=length(wave)-1;                                             
%f=0:fs/n:fs;
%wavefft=abs(fft(wave));                              %   /* perform Fourier Transform */
%plot(f,wavefft);


end

function Sound_Synthesis(Signal,Fs)
TotDSP = spl(Signal,'air');
sound(Signal,Fs);%         /* see what it sounds like */
wavwrite(Signal,Fs,['reed.wav']);               %/* read file into memory */
end

%%%%%%%%%%%%%%%%%%%DSP%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
function[TotDSP]= Calc_Dsp()


    end


% --- Executes on button press in Button_Soundsynthesis.
function Button_Soundsynthesis_Callback(hObject, eventdata, handles)
% hObject    handle to Button_Soundsynthesis (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)
Sound_Synthesis(Pos,Fs)
end

% --- Executes on button press in pushbutton23.
function pushbutton23_Callback(hObject, eventdata, handles)
% hObject    handle to pushbutton23 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)
end
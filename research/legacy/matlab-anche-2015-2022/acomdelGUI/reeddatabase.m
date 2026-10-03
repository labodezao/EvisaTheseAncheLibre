function varargout = reeddatabase(varargin)
%REEDDATABASE M-file for reeddatabase.fig
%      REEDDATABASE, by itself, creates a new REEDDATABASE or raises the existing
%      singleton*.
%
%      H = REEDDATABASE returns the handle to a new REEDDATABASE or the handle to
%      the existing singleton*.
%
%      REEDDATABASE('Property','Value',...) creates a new REEDDATABASE using the
%      given property value pairs. Unrecognized properties are passed via
%      varargin to reeddatabase_OpeningFcn.  This calling syntax produces a
%      warning when there is an existing singleton*.
%
%      REEDDATABASE('CALLBACK') and REEDDATABASE('CALLBACK',hObject,...) call the
%      local function named CALLBACK in REEDDATABASE.M with the given input
%      arguments.
%
%      *See GUI Options on GUIDE's Tools menu.  Choose "GUI allows only one
%      instance to run (singleton)".
%
% See also: GUIDE, GUIDATA, GUIHANDLES

% Edit the above text to modify the response to help reeddatabase

% Last Modified by GUIDE v2.5 11-Feb-2015 12:32:45

% Begin initialization code - DO NOT EDIT
gui_Singleton = 1;
gui_State = struct('gui_Name',       mfilename, ...
                   'gui_Singleton',  gui_Singleton, ...
                   'gui_OpeningFcn', @reeddatabase_OpeningFcn, ...
                   'gui_OutputFcn',  @reeddatabase_OutputFcn, ...
                   'gui_LayoutFcn',  [], ...
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


% --- Executes just before reeddatabase is made visible.
function reeddatabase_OpeningFcn(hObject, eventdata, handles, varargin)
% This function has no output args, see OutputFcn.
% hObject    handle to figure
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)
% varargin   unrecognized PropertyName/PropertyValue pairs from the
%            command line (see VARARGIN)

% Choose default command line output for reeddatabase
handles.output = hObject;

% Update handles structure
guidata(hObject, handles);

% UIWAIT makes reeddatabase wait for user response (see UIRESUME)
% uiwait(handles.figure1);




% --- Outputs from this function are returned to the command line.
function varargout = reeddatabase_OutputFcn(hObject, eventdata, handles)
% varargout  cell array for returning output args (see VARARGOUT);
% hObject    handle to figure
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Get default command line output from handles structure
varargout{1} = handles.output;


% --- Executes on button press in B_Open.
function B_Open_Callback(hObject, eventdata, handles)
% hObject    handle to B_Open (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)
file = uigetfile('*.mat');
        if ~isequal(file, 0)
            load(file)  
            set(handles.Prop_Mat_Tab,'Data', Properties_mat  );
            set(handles.Plaquette_Tab,'Data', Plaquette_mat  ); 
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


% --- Executes on button press in B_Select.
function B_Select_Callback(hObject, eventdata, handles)
% hObject    handle to B_Select (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)


% --- Executes on button press in B_Ok.
function B_Ok_Callback(hObject, eventdata, handles)
% hObject    handle to B_Ok (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)


% --- Executes on button press in B_Save.
function B_Save_Callback(hObject, eventdata, handles)
% hObject    handle to B_Save (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)
Properties_mat = get(handles.Prop_Mat_Tab,'Data'  );
Plaquette_mat = get(handles.Plaquette_Tab,'Data'  );

uisave({'Properties_mat','Plaquette_mat'},'*.mat');


% --- Executes when entered data in editable cell(s) in Prop_Mat_Tab.
function Prop_Mat_Tab_CellEditCallback(hObject, eventdata, handles)
% hObject    handle to Prop_Mat_Tab (see GCBO)
% eventdata  structure with the following fields (see UITABLE)
%	Indices: row and column indices of the cell(s) edited
%	PreviousData: previous data for the cell(s) edited
%	EditData: string(s) entered by the user
%	NewData: EditData or its converted form set on the Data property. Empty if Data was not changed
%	Error: error string when failed to convert EditData to appropriate value for Data
% handles    structure with handles and user data (see GUIDATA)
            
            Properties_mat = get(handles.Prop_Mat_Tab,'Data'  );
         
            if (length(Properties_mat(:,1))-1 >1)
              
         for i = 1:length(Properties_mat(:,1))-1   
            yreed(2*i) = Properties_mat(i,4);    
            yreed(2*i+1) = Properties_mat(i+1,4); 
            xreed(2*i) = sum(Properties_mat(1:i,1)) ;
            xreed(2*i+1) =xreed(2*i) ;
         end
         
            xreed = [0,xreed(2:end),sum(Properties_mat(:,1)),sum(Properties_mat(:,1))];
            yreed= [Properties_mat(1,4),yreed(2:end),Properties_mat(end,4),0];
         
         else
             xreed = [0,0,sum(Properties_mat(:,1)),sum(Properties_mat(:,1))];
             yreed= [0,Properties_mat(1,4),Properties_mat(end,4),0];
             
         end
         
            area(handles.Axes_reed,xreed,yreed); 


% --- Executes during object creation, after setting all properties.
function figure1_CreateFcn(hObject, eventdata, handles)
% hObject    handle to figure1 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called


% --- Executes during object creation, after setting all properties.
function Axes_FFT_CreateFcn(hObject, eventdata, handles)
% hObject    handle to Axes_FFT (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: place code in OpeningFcn to populate Axes_FFT
rectangle('Position',[1,2,5,10],'Curvature',[0,0],...
          'FaceColor','r')
      


% --- Executes on button press in Button_Compute.
function Button_Compute_Callback(hObject, eventdata, handles)
% hObject    handle to Button_Compute (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)
set(handles.Pan_Curves, 'Visible', 'on');

dof=get(handles.DOF,'Data');

NDDL = dof{1};

if NDDL <1 
dof{1}=1;
set(handles.DOF,'Data',dof);
NDDL = 1 ;
end

Calc_def_mod(   get(handles.Prop_Mat_Tab,'Data'  ), handles );
matkm(          get(handles.Prop_Mat_Tab,'Data'  ),NDDL, handles );



function [Mp,Kp] = matkm(Properties_mat,NDDL ,handles)


syms x ;
%Properties_mat = [ 4.550*10^-3 , 7800 , 4.259*10^-3 , 0.35*10^-3 , 2.1*10^11 ; 14.850*10^-3 , 7800 , 4.008*10^-3 , 0.2*10^-3 , 2.1*10^11 ; 9*10^-3 , 7800 , 3.699*10^-3 , 0.275*10^-3 , 2.1*10^11 ; 9*10^-3 , 7800 , 3.466*10^-3 , 1.5*10^-3 , 2.1*10^11 ] ; 
% du type [x0 (longeur tron�on ),rho0 (densit� moyenne du troncon) ,b0 (largeur -constante- de l'anche) ,h0 (Epaisseur) ,E0 (Module Young)  ;  xi,rhoi,bi,hi,Ei  ;  xn,rhon,bn,hn,En] 
% Note :
% Rem  :


L  =  sum(Properties_mat(:,1))

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


Val = eig(K,M) ;

Freq= sqrt(Val)./(2*pi);
set(handles.Freq,'Data', Freq)
stem(handles.Axes_FFT,Freq,ones(size(Freq)));



function Calc_def_mod(Properties_mat, handles)
%% calcul de la d�form�e du i�me mode   
 % du type [x0 (longeur tron�on ),rho0 (densit� moyenne du troncon) ,b0 (largeur -constante- de l'anche) ,h0 (Epaisseur) ,E0 (Module Young)  ;  xi,rhoi,bi,hi,Ei  ;  xn,rhon,bn,hn,En] 
% Note :
% Rem  :
%%
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
% testDeftr = -P*Xt(1)^2/(24*Properties_mat(k,5)*Properties_mat(k,3)*Properties_mat(k,4)^3/12)*(Xt(1)^2-4*L*Xt(1)+6*L^2) + pente(k)*(Xt(1))+fleche(k)
% testfleche = fleche(k)
% testpente  =  -P/(24*Properties_mat(k,5)*Properties_mat(k,3)*Properties_mat(k,4)^3/12)*(4*Xt(1)*L^2 - 12*L*Xt(1)^2 + 12*Xt(1)^3)
% tpente = pente(k)
   
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

      

function  [Omega_n ]= Pulsa_nat(n) 

[Bl,~]=BL_Sigma(n);
E=B*h^3/12;
Omega_n =(Bl)^2*(E*I/(Roh*A*L^4))^0.5 ;


% --- Executes on button press in Button_New.
function Button_New_Callback(hObject, eventdata, handles)
% hObject    handle to Button_New (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)
set(handles.Prop_Mat_Tab,'Data', zeros(1,5) );
cla(handles.Axes_reed);
 set(handles.Pan_reed_data,'Visible','on');


% --- Executes during object creation, after setting all properties.
function Pan_reed_data_CreateFcn(hObject, eventdata, handles)
% hObject    handle to Pan_reed_data (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called


% --- Executes during object creation, after setting all properties.
function Axes_reed_CreateFcn(hObject, eventdata, handles)
% hObject    handle to Axes_reed (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: place code in OpeningFcn to populate Axes_reed


% --- Executes during object creation, after setting all properties.
function Prop_Mat_Tab_CreateFcn(hObject, eventdata, handles)
% hObject    handle to Prop_Mat_Tab (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called



function edit1_Callback(hObject, eventdata, handles)
% hObject    handle to edit1 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of edit1 as text
%        str2double(get(hObject,'String')) returns contents of edit1 as a double


% --- Executes during object creation, after setting all properties.
function edit1_CreateFcn(hObject, eventdata, handles)
% hObject    handle to edit1 (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end


% --- Executes when entered data in editable cell(s) in Nbr_troncon.
function Nbr_troncon_CellEditCallback(hObject, eventdata, handles)
% hObject    handle to Nbr_troncon (see GCBO)
% eventdata  structure with the following fields (see UITABLE)
%	Indices: row and column indices of the cell(s) edited
%	PreviousData: previous data for the cell(s) edited
%	EditData: string(s) entered by the user
%	NewData: EditData or its converted form set on the Data property. Empty if Data was not changed
%	Error: error string when failed to convert EditData to appropriate value for Data
% handles    structure with handles and user data (see GUIDATA)

 nbr_trcon = get(handles.Nbr_troncon ,'Data') ;
 Prop_sav  = get(handles.Prop_Mat_Tab,'Data') ;
% size(Prop_sav)
 if  length( Prop_sav(:,1) ) < nbr_trcon
   set(handles.Prop_Mat_Tab,'Data', [Prop_sav ; zeros(nbr_trcon-length( Prop_sav(:,1)),5)] );  
 else
   set(handles.Prop_Mat_Tab,'Data', Prop_sav(1:nbr_trcon,:) );    
 end
 

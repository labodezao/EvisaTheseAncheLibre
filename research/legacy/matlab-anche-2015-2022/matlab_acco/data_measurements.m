function data_measurements
clc
clear all
close all

%%
 folderpath = 'D:\science ewen\acco\ewen 2011\large_reed\';
 cd (folderpath);
aa = 1;
bb = 1;


graph_allinone         = 0          ;
graph_phasisportaitall = 0          ;
savegraphphasis        = 0          ;
list_t                 = dir ('t**')


for a = 1:length(list_t(:,1))
    %for a = [1]
    astr = list_t(a,1).name   ;      
    aa
    cd([folderpath,astr])           
    clear listing 
    listing = dir('**.vna')  ;       
    
    for b = 1:length(listing(:,1)) %mettre dans b les valeurs de pression
    %for b = [1:3] %mettre dans b les valeurs de pression
     bb 
    bstr = listing(b,1).name;
 
        eval(['load ',bstr,' -mat'])
        info =  whos('-file',bstr);
        
  
%%        
        Sens_KuLite = 1.15*10^2 ;
        Sens_Ray = 1;
        
        
  
%%        
        %Load the differents matrices
        vto=find(SLm.tdxvec == 0,1) ;
       
        y0=mean(SLm.scmeas(1,1).tdmeas(vto));
        ONES= y0*ones(size(SLm.scmeas(1,1).tdmeas)) ;
        
        vtf= length(SLm.scmeas(1,1).tdmeas(vto:end));
        if (SLm.scmeas(1,1).tdmeas(vto:end) == 0)
        vtf = find (SLm.scmeas(1,1).tdmeas(vto:end) == 0,1);
        end
        Pos(1:length(SLm.scmeas(1,1).tdmeas(vto:vtf))) =  SLm.scmeas(1,1).tdmeas(vto:vtf) - ONES(vto:vtf) ;
       
        TimeVolPress(1:length(SLm.tdxvec(vto:vtf))) = SLm.tdxvec(vto:vtf);
        %we keep just the positive time ;)
        
        
        Timeinterp=0: (TimeVolPress(2)- TimeVolPress(1))/20: TimeVolPress(end);
        InterPos =interp1(TimeVolPress(:),Pos(:),Timeinterp,'cubic');
       
       
        %%
        Kulite_largereed(1:length(SLm.scmeas(1,4).tdmeas(vto:vtf))) = SLm.scmeas(1,4).tdmeas(vto:vtf);
        Pmic_largereed(1:length(SLm.scmeas(1,3).tdmeas(vto:vtf))) = Sens_Ray*SLm.scmeas(1,3).tdmeas(vto:vtf);
        Curent_largereed(1:length(SLm.scmeas(1,2).tdmeas(vto:vtf))) = SLm.scmeas(1,2).tdmeas(vto:vtf);
           
        
        in_pressure = mean(SLm.scmeas(1,4).tdmeas(floor(vto+(vtf-vto)/2):vtf)) * Sens_KuLite;
        input_pressure_estimate(bb,aa) = in_pressure ;   
        
       [max_env,imaxenv ] = max(Pos(:)); 
       DeltaT   = 1/SampleRate(1,1);
       Reed_Velocity(1:length(InterPos(2:end))) = (InterPos(2:end)-InterPos(1:end-1))./DeltaT; 
       

    S0= 1.5*80*25*10^-9;
   
    if aa<10
    dV= 60/27*(aa-1)*S0;
    else
    dV= 60/27*(9)*S0+60/13.5*(aa-9)*S0;    
    end
    
    
    V(aa) = 60*S0-dV;
       
       if (max_env > 0.2 && length(TimeVolPress) > 2000  )
            
% figure
% plot(Timeinterp,InterPos);
 %works fine  
     
    
        
%% TRESP        
[Stime,T0,T1] = envelope(Timeinterp,InterPos);

%T0
%T1

%irestinterp = find( Timeinterp > Stime ,1);
%irest= find( TimeVolPress(:,bb,aa) > Stime ,1);
irest= find( TimeVolPress(:) > Stime ,1);
TResp(bb,aa) = Stime ;


 
 

%% Trouver une seule periode du signal



%  figure
%  plot(Timeinterp(T0:T1),InterPos(T0:T1));
% works fine  



% 
 
  Fs = 1/((TimeVolPress(2)- TimeVolPress(1))/20) ;% Sampling frequency
 FFTY = fft(InterPos(T0:T1)-mean(InterPos(T0:T1))*ones(size(InterPos(T0:T1))),length(InterPos(T0:T1)));
 Pyy = FFTY.*conj(FFTY)/length(InterPos(T0:T1));
 freq = Fs/length(InterPos(T0:T1))*(0:2047);
%  figure
%  plot(freq,Pyy(1:length(freq)))
%  title('Power spectral density')
%  xlabel('Frequency (Hz)')

 [M,Ind]= max(Pyy) ;
Ofrequency(bb,aa)=freq(Ind);
 
%  %% test matworks d'la merde !
% 
% x=InterPos(T0:T1);
% c  = cceps(x);
% t = 0:1/Fs:x(end)-(1/Fs);
% figure
% plot(t(15:75).*1e3,c(15:75)); xlabel('msec');
% [~,I] = max(c(15:55));
% fprintf('Complex cepstrum F0 estimate is %3.2f Hz.\n', 1/(t(I+15)));
%  
 

%% DSP

TotDSP_Cav(bb,aa) = spl(Kulite_largereed(irest:end),'air');

TotDSP_Ray(bb,aa) = spl(Pmic_largereed(irest:end),'air');

%% Graphs        
       
if graph_allinone == 1
fig_allinone =  figure('PaperType', 'A4') ;
plot(Timeinterp(:),InterPos(:)) 
title([' Magnitude for p= ', num2str(in_pressure) ,'mBars and Vol = ',num2str(V(aa)),'m^3'])

saveName = ([' Oscilattions vs time for p= ', num2str(in_pressure) ,'mBars and Vol = ',num2str(V(aa)),'m^3' '.jpg']);
    print(fig_allinone,'-djpeg',saveName,'-r550')
close 
end


if graph_phasisportaitall == 1
fig_phasisportait =  figure('PaperType', 'A4') ;
%  EnvVelo          = Reed_Velocity(T0:T1);
%         EnvVelo(EnvVelo > 1) = 1;
%         EnvVelo(EnvVelo < 1) = 0;
%        [ix0] = find(diff(EnvVelo)~=0 , 50); %calcle les 5 premiers changements de signes de la vitesse
%         ioff = T0 + ix0(10); 
%         ion = T0 + ix0(1);
%         if length(InterPos(min(ion,ioff):max(ion,ioff),bb,aa)) <5
%         ioff = T0 + ix0(30); 
%         end
oldpath = cd;
cd('D:\science ewen\acco\ewen 2011\');            
        
tempell= fit_ellipse(InterPos(T0:T1-1), Reed_Velocity(T0:T1-1)) ;

cd(oldpath);
  
subplot(2,1,1);
    
plot(tempell.xell,tempell.yxell,InterPos(T0:T1-1), Reed_Velocity(T0:T1-1)); 
title({[' Phase portrait for p= ',  num2str(in_pressure) ,' mBars, t= ',astr,' and a= ', num2str(tempell.a)],[' b= ', num2str(tempell.b),' and phi(rad)= ', num2str(tempell.phi),' parameters for ellipse']})
xlabel(' x(t) ')
ylabel(' dx(t)/dt ')


subplot(2,1,2)
plot(Timeinterp,InterPos)
title([' All graph for p= ', num2str(in_pressure) ,' and turn = ',astr])
xlabel(' t[s] ')
ylabel(' x(t)/dt ')
clear tempell
end   
    
if savegraphphasis ==1
    saveName = ([' Phase portrait for p= ',bstr,' and turn = ',astr , '.jpg']);
    print(fig_phasisportait,'-djpeg',saveName,'-r550')
close       
end




       end
       
       clear (info.name)
       
        bb = bb+1;
      
     end
  %% Avant de passer au volume n+1 on trace les courbes dsp=f(debit),dsp=f(debit) et dsp=f(debit) qu'on interpole de manière à avoir les vecteurs de pression ne commun
       
 

    
    bb = 1;
    aa = 1+aa;

end

   
cd(folderpath)           ;
 save('Results.mat', 'TResp' , 'Ofrequency', 'TotDSP_Cav', 'TotDSP_Ray','V', 'input_pressure_estimate' );
 load('Results.mat')
 
Press_interpol= min(input_pressure_estimate(input_pressure_estimate~=0))+(max(input_pressure_estimate)-min(input_pressure_estimate(input_pressure_estimate~=0)))/2:(max(input_pressure_estimate)-min(input_pressure_estimate(input_pressure_estimate~=0)))/40:max(input_pressure_estimate) ;
      
 for index= 1:length(TotDSP_Ray(1,:))  
       
    
   [indexmax] = find (input_pressure_estimate(:,index) ) ;
    
        InterDsp =interp1(input_pressure_estimate(indexmax,index),TotDSP_Ray(indexmax,index),Press_interpol,'nearest','extrap');
     DSP(1:length(InterDsp),index)=InterDsp;
     InterDsp=0;
     
       InterFreq =interp1(input_pressure_estimate(indexmax,index),Ofrequency(indexmax,index),Press_interpol,'nearest','extrap');
 Freq(1:length(InterFreq),index)=InterFreq;
   InterFreq=0;     

   
   InterTresp =interp1(input_pressure_estimate(indexmax,index),TResp(indexmax,index),Press_interpol,'nearest','extrap');
 ResTime(1:length(InterTresp),index) =InterTresp;
      InterTresp=0;
indexmax =0;
   


end

 cd(folderpath)           ;
 save('Results.mat', 'TResp' , 'Ofrequency', 'TotDSP_Cav', 'TotDSP_Ray','V', 'input_pressure_estimate', 'ResTime','Freq', 'DSP','Press_interpol'  );
 
figure

[XDSP,YDSP] = meshgrid(V,Press_interpol);
%ZDSP(:,:) = smoothn(TotDSP_Ray(:,:),'robust');
ZDSP(:,:) = DSP;

% size(XDSP)
% size(YDSP)
% size(ZDSP)

%plot3(XDSP,YDSP,ZDSP)
surf(XDSP,YDSP,ZDSP)
shading interp
 grid on
 title ('Dsp(Volume , Volumic inlet air flow )'  ) 
ylabel('Pression[mBars]'     )
xlabel('Volume [m^3]'     )
zlabel('Dsp_Spl [db]')



figure

[XOfreq,YOfreq] = meshgrid(V,Press_interpol);
ZOfreq = smoothn(Freq,'robust');
%plot3(XOfreq,YOfreq,ZOfreq);
surf(XOfreq,YOfreq,ZOfreq);
shading interp
grid on
title ('Freq(Volume , Volumic inlet air flow )'  ) 
ylabel('Volume [m^3]'     )
xlabel('Debit[m^3/s]'     )
zlabel('Fondamental Frequency [db]')


figure

[XResp,YResp] = meshgrid(V,Press_interpol);
%ZResp(:,:) = smoothn(TResp(:,:),'robust');
ZResp(:,:) = ResTime;

%plot3(XResp,YResp,ZResp);
surf(XResp,YResp,ZResp);
shading interp
grid on
title ('seattling time (Volume , Volumic inlet air flow )'  ) 
xlabel('Volume [m^3]'     )
ylabel('Volumic inlet  air flow[m^3/s]'     )
zlabel('Response time [s]')


end



function ellipse_t = fit_ellipse( x , y )
%
% initialize
orientation_tolerance = 1e-3;

% empty warning stack
lastwarn( '' );

% prepare vectors, must be column vectors
x = x(:);
y = y(:);

% remove bias of the ellipse - to make matrix inversion more accurate. (will be added later on).
mean_x = mean(x);
mean_y = mean(y);
x = x-mean_x;
y = y-mean_y;

% the estimation for the conic equation of the ellipse
X = [x.^2, x.*y, y.^2, x, y ];
a = sum(X)/(X'*X);

% check for warnings
if ~isempty( lastwarn )
    disp( 'stopped because of a warning regarding matrix inversion' );
    ellipse_t = [];
    return
end

% extract parameters from the conic equation
[a,b,c,d,e] = deal( a(1),a(2),a(3),a(4),a(5) );

% remove the orientation from the ellipse
if ( min(abs(b/a),abs(b/c)) > orientation_tolerance )
    
    orientation_rad = 1/2 * atan( b/(c-a) );
    cos_phi = cos( orientation_rad );
    sin_phi = sin( orientation_rad );
    [a,b,c,d,e] = deal(...
        a*cos_phi^2 - b*cos_phi*sin_phi + c*sin_phi^2,...
        0,...
        a*sin_phi^2 + b*cos_phi*sin_phi + c*cos_phi^2,...
        d*cos_phi - e*sin_phi,...
        d*sin_phi + e*cos_phi );
    [mean_x,mean_y] = deal( ...
        cos_phi*mean_x - sin_phi*mean_y,...
        sin_phi*mean_x + cos_phi*mean_y );
else
    orientation_rad = 0;
    cos_phi = cos( orientation_rad );
    sin_phi = sin( orientation_rad );
end

% check if conic equation represents an ellipse
test = a*c;
switch (1)
case (test>0),  status = '';
case (test==0), status = 'Parabola found';  warning( 'fit_ellipse: Did not locate an ellipse' );
case (test<0),  status = 'Hyperbola found'; warning( 'fit_ellipse: Did not locate an ellipse' );
end

% if we found an ellipse return it's data
if (test>0)
    
    % make sure coefficients are positive as required
    if (a<0), [a,c,d,e] = deal( -a,-c,-d,-e ); end
    
    % final ellipse parameters
    X0          = mean_x - d/2/a;
    Y0          = mean_y - e/2/c;
    F           = 1 + (d^2)/(4*a) + (e^2)/(4*c);
    [a,b]       = deal( sqrt( F/a ),sqrt( F/c ) );    
    long_axis   = 2*max(a,b);
    short_axis  = 2*min(a,b);

    % rotate the axes backwards to find the center point of the original TILTED ellipse
    R           = [ cos_phi sin_phi; -sin_phi cos_phi ];
    P_in        = R * [X0;Y0];
    X0_in       = P_in(1);
    Y0_in       = P_in(2);
  % rotation matrix to rotate the axes with respect to an angle phi
    
    % the ellipse
    theta_r         = linspace(0,2*pi);
    ellipse_x_r     = X0 + a*cos( theta_r );
    ellipse_y_r     = Y0 + b*sin( theta_r );
    rotated_ellipse = R * [ellipse_x_r;ellipse_y_r];
xrotated_ellipse =rotated_ellipse(1,:);
yrotated_ellipse =rotated_ellipse(2,:);
    
     % pack ellipse into a structure
    ellipse_t = struct( ...
        'a',a,...
        'b',b,...
        'phi',orientation_rad,...
        'X0',X0,...
        'Y0',Y0,...
        'xell',xrotated_ellipse,...
        'yxell',yrotated_ellipse,...
        'X0_in',X0_in,...
        'Y0_in',Y0_in,...
        'long_axis',long_axis,...
        'short_axis',short_axis,...
        'status','' );
else
    % report an empty structure
    ellipse_t = struct( ...
        'a',[],...
        'b',[],...
        'phi',[],...
        'X0',[],...
        'Y0',[],...
        'X0_in',[],...
        'Y0_in',[],...
        'long_axis',[],...
        'short_axis',[],...
        'status',status );
end
    
    

    
 end


function [tresp,Ti,Tf] = envelope(x,y,interpMethod)



%%%%%%%%%% à revoir





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

extrMaxValue = y(find( diff(sign(diff(y)) )==-2 ) +1);
extrMaxIndex =   find(diff(sign(diff(y)))==-2)+1;

up = extrMaxValue;
up_x = x(extrMaxIndex);

if (length(up_x)>1 && length(x)>1 && length(up)>1 && length(find(diff(up)==0)) < floor(length(up)*0.15) )
yp0 =interp1(up_x,up,x,);
yp=yp0;


s=100;
itersmooth=1;
while(length(find(diff(sign(diff(yp)))==+2) )> 10)
itersmooth=itersmooth+1;
    yp = smoothn(yp,s*100);
s=s*100;

end

%figure
%plot(yp)

Cutindex =   find(  diff(sign(diff(yp)))==-2,3)+1;
if (~isempty(Cutindex))
[~,icutindexmax]= min(abs(yp0(Cutindex)-ones(size(yp0(Cutindex)))*mean(yp0(floor(0.90*length(yp0)):floor(0.95*length(yp0)))))) ;
S = lsiminfo(yp0(1:Cutindex(icutindexmax)),x(1:length(yp0(1:Cutindex(icutindexmax)))));
tresp=S.SettlingTime;
%%
length(x)
Icut = find(x>tresp,1);
ystable=y(Icut:end);
xstable=x(Icut:end);

extrMaxValue = ystable(find( diff(sign(diff(ystable)) )==-2 ) +1);
extrMaxIndex =   find(diff(sign(diff(ystable)))==-2)+1;

up = extrMaxValue;
up_x = xstable(extrMaxIndex);


troisquart=floor(0.75*length(up));
[~,secondmaxup]= min( abs(ones(size(up(troisquart+1:end)))*up(1) - up(troisquart+1:end)));
%%

Ti = Icut;
if (secondmaxup+troisquart+1 < length(up_x) )
Tf = (find(x > up_x(secondmaxup+troisquart+1),1));    
else
tresp=0;    
Ti=1;
Tf=length(y); 
end

end


else
tresp=0;    
Ti=1;
Tf=length(y);
end
else
tresp=0;    
Ti=1;
Tf=length(y);
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





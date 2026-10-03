function  fleche_ponctuelle()
clc
Properties_mat = [ 4.550*10^-3 , 7800 , 4.259*10^-3 , 0.35*10^-3 , 2.1*10^11 ; 14.850*10^-3 , 7800 , 4.008*10^-3 , 0.2*10^-3 , 2.1*10^11 ; 9*10^-3 , 7800 , 3.699*10^-3 , 0.275*10^-3 , 2.1*10^11 ; 9*10^-3 , 7800 , 3.466*10^-3 , 1.5*10^-3 , 2.1*10^11 ] ; 

%Properties_mat = [ 5*10^-3 , 7800 , 4*10^-3 , 0.5*10^-3 , 2.1*10^11 ; 5*10^-3 , 7800 , 4*10^-3 , 0.5*10^-3 , 2.1*10^11 ] ; 

% du type [x0 (longeur tronçon ),rho0 (densité moyenne du troncon) ,b0 (largeur -constante- de l'anche) ,h0 (Epaisseur) ,E0 (Module Young)  ;  xi,rhoi,bi,hi,Ei  ;  xn,rhon,bn,hn,En] 
% Note :
% Rem  :
    P=1;
   [nsection,nparam] = size(Properties_mat) ;
   X=zeros(1,50*nsection);
   Def=zeros(1,50*nsection);
   Xi=0;
   Defi=0;
   xn = 0;
   xnp1=  Properties_mat(1,1);
   pente(1)=0;
   fleche(1)=0;
   for k=1:nsection  
   L= Properties_mat(k,1);
       if k>1
           
   xn = xnp1;
   xnp1= xnp1 + Properties_mat(k,1);
   
   Xtr = xn: (xnp1-xn)/10 : xnp1;
   Xt= Xtr-xn*ones(size(Xtr)) ;
   
   Deftr = -P*Xt.^2/(24*Properties_mat(k,5)*Properties_mat(k,3)*Properties_mat(k,4)^3/12).*(Xt.^2-4*L*Xt+6*L^2) + pente(k)*(Xt)+fleche(k);
   %Deftr = 2*Xt.^2/(Properties_mat(k,5)*Properties_mat(k,3)*Properties_mat(k,4)^3/12).*(Xt.^2-4*L*Xt) + pente(k)*(Xt)+fleche(k);
   %Deftr = 2*Xt.^2/(Properties_mat(k,5)*Properties_mat(k,3)*Properties_mat(k,4)^3/12).*(Xt.^2-4*L*Xt) + pente(k)*(Xt)+fleche(k);
   
% testDeftr = -P*Xt(1)^2/(24*Properties_mat(k,5)*Properties_mat(k,3)*Properties_mat(k,4)^3/12)*(Xt(1)^2-4*L*Xt(1)+6*L^2) + pente(k)*(Xt(1))+fleche(k)
% testfleche = fleche(k)
% testpente  =  -P/(24*Properties_mat(k,5)*Properties_mat(k,3)*Properties_mat(k,4)^3/12)*(4*Xt(1)*L^2 - 12*L*Xt(1)^2 + 12*Xt(1)^3)
% tpente = pente(k)
   
   Xi= [Xi, Xtr];
   Defi = [Defi, Deftr];
   
       else
 
  Xtr = xn: (xnp1-xn)/10 : xnp1;
  Xt= Xtr-xn*ones(size(Xtr)) ;
  Deftr = -P*(Xt).^2/(24*Properties_mat(k,5)*Properties_mat(k,3)*Properties_mat(k,4)^3/12).*(Xt.^2 - 4*L*Xt + 6*L^2);
    
  Xi= [Xi, Xtr];
   Defi = [Defi, Deftr];
   
       end
       
   pente(k+1)  =  -P/(24*Properties_mat(k,5)*Properties_mat(k,3)*Properties_mat(k,4)^3/12)*(4*Xt(end)*L^2 - 12*L*Xt(end)^2 + 12*Xt(end)^3);
   fleche(k+1) = Deftr(end);
   
   end

   
   
X   = Xi(2:end)  ;

Def = Defi(2:end)/max(abs(Defi)) ;
figure
plot(X',Def');

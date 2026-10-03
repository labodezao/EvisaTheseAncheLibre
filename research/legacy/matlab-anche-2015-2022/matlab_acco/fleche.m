function  fleche()
clc
close all
Properties_mat = [ 4.550*10^-3 , 7800 , 4.259*10^-3 , 0.35*10^-3 , 2.1*10^11 ; 14.850*10^-3 , 7800 , 4.008*10^-3 , 0.2*10^-3 , 2.1*10^11 ; 9*10^-3 , 7800 , 3.699*10^-3 , 0.275*10^-3 , 2.1*10^11 ; 9*10^-3 , 7800 , 3.466*10^-3 , 1.5*10^-3 , 2.1*10^11 ] ; 

%Properties_mat = [ 5*10^-3 , 7800 , 4*10^-3 , 0.5*10^-3 , 2.1*10^11 ; 5*10^-3 , 7800 , 4*10^-3 , 0.5*10^-3 , 2.1*10^11 ;  5*10^-3 , 7800 , 4*10^-3 , 0.5*10^-3 , 2.1*10^11 ] ; 

% du type [x0 (longeur tronçon ),rho0 (densité moyenne du troncon) ,b0 (largeur -constante- de l'anche) ,h0 (Epaisseur) ,E0 (Module Young)  ;  xi,rhoi,bi,hi,Ei  ;  xn,rhon,bn,hn,En] 
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
   pente= []
   pente(1)=0;
   fleche(1)=0;
   A=0;
   B=0;
   for k=1:nsection  
   
   
   if k>1
   
   
   xn = xnp1;
   xnp1=Properties_mat[0,0]
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

figure
plot(X',Def');
figure
plot(X',Pent');



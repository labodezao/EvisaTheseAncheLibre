function [Mp,Kp] = matkm()

// Initialisation des variables de sortie (non trouvée dans les variables d'entrée)
Mp=[];
Kp=[];



// Affiche un avertissement pour une exception en virgule flottante
ieee(1);

// !! L.2: La fonction inconnue sym n'est pas convertie, la séquence d'appel originale est utilisée.
x = sym("x","f");

Properties_mat = [4.55*(10^-3),7800,4.259*(10^-3),0.35*(10^-3),2.1*(10^11);14.85*(10^-3),7800,4.008*(10^-3),0.2*(10^-3),2.1*(10^11);9*(10^-3),7800,3.699*(10^-3),0.275*(10^-3),2.1*(10^11);9*(10^-3),7800,3.466*(10^-3),1.5*(10^-3),2.1*(10^11)];
Properties_mat = [5*(10^-3),7800,4*(10^-3),0.5*(10^-3),2.1*(10^11);5*(10^-3),7800,4*(10^-3),0.5*(10^-3),2.1*(10^11);5*(10^-3),7800,4*(10^-3),0.5*(10^-3),2.1*(10^11)];

// du type [x0 (longeur tronçon ),rho0 (densité moyenne du troncon) ,b0 (largeur -constante- de l''anche) ,h0 (Epaisseur) ,E0 (Module Young)  ;  xi,rhoi,bi,hi,Ei  ;  xn,rhon,bn,hn,En] 
// Note :
// Rem  :

NDDL = 2;
// ! L.12: mtlb(:) peut être remplacé par :() ou : que : soit un M-file ou non.
// ! L.12: mtlb(:) peut être remplacé par :() ou : que : soit un M-file ou non.
// !! L.12: La fonction inconnue mtlb n'est pas convertie, la séquence d'appel originale est utilisée.
L = mtlb_sum(mtlb_double(Properties_mat(mtlb(mtlb(:)),1)));


// !! L.15: La fonction inconnue sym n'est pas convertie, la séquence d'appel originale est utilisée.
M = sym(zeros(NDDL,NDDL));
// !! L.16: La fonction inconnue sym n'est pas convertie, la séquence d'appel originale est utilisée.
K = sym(zeros(NDDL,NDDL));
[nsection,nparam] = size(Properties_mat);
for i = 1:NDDL
  // !! L.19: La fonction inconnue BL_Sigma n'est pas convertie, la séquence d'appel originale est utilisée.
  [Bi,Si] = BL_Sigma(i);

  for j = 1:NDDL
    // !! L.22: La fonction inconnue BL_Sigma n'est pas convertie, la séquence d'appel originale est utilisée.
    [Bj,Sj] = BL_Sigma(j);
    M_ij = 0;
    K_ij = 0;
    xn = 0;
    xnp1 = Properties_mat(1,1);
  
    for k = 1:nsection
      if k>1 then
        xn = xnp1;
        xnp1 = mtlb_a(mtlb_double(xnp1),mtlb_double(Properties_mat(k,1)));
      end;
    
    
      //% Calcul des coefficients de matrices
    
      // !! L.37: La fonction inconnue int n'est pas convertie, la séquence d'appel originale est utilisée.
      // L.37: (Attention, conflit de nom : le nom de la fonction a été changé de int en %int).
      kij = %int(mtlb_diff(mtlb_s(mtlb_s(cosh((mtlb_double(Bi)/L)*mtlb_double(x)),cos((mtlb_double(Bi)/L)*mtlb_double(x))),mtlb_double(Si)*mtlb_s(sinh((mtlb_double(Bi)/L)*mtlb_double(x)),sin((mtlb_double(Bi)/L)*mtlb_double(x)))),2)*mtlb_diff(mtlb_s(mtlb_s(cosh((mtlb_double(Bj)/L)*mtlb_double(x)),cos((mtlb_double(Bj)/L)*mtlb_double(x))),mtlb_double(Sj)*mtlb_s(sinh((mtlb_double(Bj)/L)*mtlb_double(x)),sin((mtlb_double(Bj)/L)*mtlb_double(x)))),2),xn,xnp1);
      // !! L.38: La fonction inconnue int n'est pas convertie, la séquence d'appel originale est utilisée.
      // L.38: (Attention, conflit de nom : le nom de la fonction a été changé de int en %int).
      mij = %int(mtlb_s(mtlb_s(cosh((mtlb_double(Bi)/L)*mtlb_double(x)),cos((mtlb_double(Bi)/L)*mtlb_double(x))),mtlb_double(Si)*mtlb_s(sinh((mtlb_double(Bi)/L)*mtlb_double(x)),sin((mtlb_double(Bi)/L)*mtlb_double(x))))*mtlb_s(mtlb_s(cosh((mtlb_double(Bj)/L)*mtlb_double(x)),cos((mtlb_double(Bj)/L)*mtlb_double(x))),mtlb_double(Sj)*mtlb_s(sinh((mtlb_double(Bj)/L)*mtlb_double(x)),sin((mtlb_double(Bj)/L)*mtlb_double(x)))),xn,xnp1);
      K_ij = mtlb_a(K_ij,(((mtlb_double(kij)*mtlb_double(Properties_mat(k,5)))*mtlb_double(Properties_mat(k,3)))*(mtlb_double(Properties_mat(k,4))^3))/12);
      M_ij = mtlb_a(M_ij,((mtlb_double(mij)*mtlb_double(Properties_mat(k,2)))*mtlb_double(Properties_mat(k,3)))*mtlb_double(Properties_mat(k,4)));
      //Mtest=double(int( (cosh(Bi/L*x)-cos(Bi/L*x)-Si*(sinh(Bi/L*x)-sin(Bi/L*x)))*(cosh(Bj/L*x)-cos(Bj/L*x)-Sj*(sinh(Bj/L*x)-sin(Bj/L*x))) , 0 , L) )*Properties_mat(k,2)*Properties_mat(k,3)*Properties_mat(k,4) 
      //Ktest=double(int( diff(cosh(Bi/L*x)-cos(Bi/L*x)-Si*(sinh(Bi/L*x)-sin(Bi/L*x)),x,2)*diff(cosh(Bj/L*x)-cos(Bj/L*x)-Sj*(sinh(Bj/L*x)-sin(Bj/L*x)),x,2)  , 0 , L) )*Properties_mat(k,5)*Properties_mat(k,3)*Properties_mat(k,4)^3/12
    end;
  
    M(i,j) = M_ij;
    K(i,j) = K_ij;
  end;
end;


[%v0$1,%v1$2] = spec(K,M);Val = %v0$1 ./%v1$2

Freq = sqrt(Val) ./(2*%pi)
endfunction

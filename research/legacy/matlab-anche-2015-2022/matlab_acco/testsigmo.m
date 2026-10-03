Posn=-4*10^-3:0.0001:4*10^-3;
gamma_sigmo = 1*10^-3;
beta_sigmo = -6000;
gamma_sigmo2 =-3*10^-3;

sigmo=exp(beta_sigmo*(Posn + gamma_sigmo))./(1+exp(beta_sigmo*(Posn + gamma_sigmo))) + (1./(1+exp(beta_sigmo*(Posn+gamma_sigmo2)))).^2  ;
%sigmo = (1./(1+exp(beta_sigmo*(Posn+gamma_sigmo2)))) ;
figure
plot(Posn,sigmo)
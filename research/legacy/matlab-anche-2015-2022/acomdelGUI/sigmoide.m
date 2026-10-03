
Posn = 0:0.001:90;
gamma_sigmo = 3*10^-3;
beta_sigmo = 20000;
gamma_sigmo2 =-0;
pondersigmoa = 1./1+exp(beta_sigmo*(Posn + gamma_sigmo))
figure
plot (Posn, pondersigmoa)
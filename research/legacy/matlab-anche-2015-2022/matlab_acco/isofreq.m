clear all
clc

x=0.01:0.001:10;


a14=x.^(1/4);
a12=x.^2;
a1=x;
a2= x.^2;
a4=x.^4;
am12=x.^2;
am14=x.^(-1/4);
am4=x.^-4;


figure
plot(x,a14,x,a12,x,a1,x,a2,x,a4,x,am12,x,am14,x,am4)
title('Courbes isofréquences des anches')
xlabel('Paramètre modifié entre la configuration 1 et 2')
ylabel('Valeur à modifier sur le paramètre choisi ')
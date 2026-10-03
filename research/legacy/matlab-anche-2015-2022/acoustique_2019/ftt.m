clear
fe = 8000;
f0 = 1300;
L = 1024;
N = 128;
xn = sin(2*pi*(f0/fe)*(0:N-1));
figure(1); hold off
plot(xn,'.-');
axis([0 N-1 -1.2 1.2])
tfd1 = fft(xn(1:16), L);
tfd1_db = 20*log10(abs(tfd1(1:L/2)));
tfd2 = fft(xn(1:128), L);
tfd2_db = 20*log10(abs(tfd2(1:L/2)));
axe_freq = (0:L/2-1)*fe/L;
figure(2); hold off
plot(axe_freq, tfd1_db, '.-'); hold on
plot(axe_freq, tfd2_db, '.-r');
plot(f0*[1 1], [-50 50], 'k')
axis([0 fe/2 -50 50])
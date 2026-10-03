[y, Fs] = wavread('carre98.4.wav'); % y is sound data, Fs is sample frequency.
t = (1:length(y))/Fs;         % time

ind = find(t>0.1 & t<0.12);   % set time duration for waveform plot
figure; subplot(1,2,1)
plot(t(ind),y(ind))  
axis tight         
title(['Waveform of '])

N = 2^18;                     % number of points to analyze
subplot(1,2,2)
plot(t(1:N),y(1:N));
c = fft(y(1:N))/N;            % compute fft of sound data
p = 2*abs( c(2:N/2));         % compute power at each frequency
f = (1:N/2-1)*Fs/N;           % frequency corresponding to p

figure
%subplot(1,2,2)
semilogy(f,p)
axis([0 4000 10^-4 1])                
title(['Power Spectrum of ' ])
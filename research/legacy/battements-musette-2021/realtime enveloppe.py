import numpy as np
import scipy.signal as sig
import matplotlib.pyplot as plt

# Parameters
N = 1300
t = np.arange(0,N)
f = 1.0/20

# Discontinuous amplitude envelope
A = np.ones(t.size)
A[1*t.size/5:2*t.size/5] = .2

# Time signal with noise
y = A*np.sin(2*np.pi*f*t)
y += (np.random.rand(N)*2-1)*.2

# Filter noise
filt = True
if filt :
    cutoff = int(N*f*1.5)
    yrms1 = (y**2).mean()**.5
    yF = np.fft.fft(y)
    yF[cutoff:]=0               # Filter
    y = np.real(np.fft.ifft(yF))
    yrms2 = (y**2).mean()**.5   # Keep signal energy
    y *= yrms1/yrms2

# Calculate envelope
envelope = np.abs(sig.hilbert(y));


# Plots
plt.figure(1, figsize=[10,7], dpi=100)
plt.clf()
plt.plot(A, label='Actual envelope')
plt.plot(y, label='Time signal')
plt.plot(envelope, '.', label='Calculated envelope')
plt.legend(loc='lower right')
plt.show()
plt.draw()
plt.pause(.1)
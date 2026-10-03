######################################################################################################
#                                                                                                    # 
# 1)Reads wav 1 or 2 ch and plot signal.                                                             #
# 2)Estimate envelope and sonogram                                                                   #
# 3)Make consecutive plots of "step_time" size in file with current wav name for each file in r_dir  #
#                                                                                                    #
#                                         C. Jarne 05-01-2017 V1.0                                   #                           
######################################################################################################

# libraries 
import numpy as np
import scipy
import os
import scipy.stats as stats

from scipy.io import wavfile
import wave, struct
import matplotlib.pyplot as pp

from pylab import *
import scipy.signal.signaltools as sigtool
import scipy.signal as signal
from scipy.fftpack import fft

# Here directory (put the name and path). Directory only with .wav files

r_dir ="D:/GoogleDrive/python/test demodulation/"

# Parameters

Fmax         = 10000 #maximum frequency for the sonogram [Hz]
step_time    = 4   #len for the time serie segment  [Seconds]->>>>>>>>> Change it to zoom in the signal time!!
w_cut        = 40   #Frequency cut for our envelope implementation [Hz]
w_cut_simple = 150   #Frecuency cut for the low-pass envelope [Hz]


###################################
#1) Function envelope with rms slide window (for the RMS-envelope implementation)

def window_rms(inputSignal, window_size):
    a2 = np.power(inputSignal,2)
    window = np.ones(window_size)/float(window_size)
    return np.sqrt(np.convolve(a2, window, 'valid'))

##################################

#2) Filter is directly implemented in Abs(signal)

##################################
#3) our implementation !

def getEnvelope(inputSignal):
# Taking the absolute value

    absoluteSignal = []
    for sample in inputSignal:
        absoluteSignal.append (abs (sample))

    # Peak detection

    intervalLength = 35 # change this number depending on your Signal frequency content and time scale
    outputSignal = []

    for baseIndex in range (0, len (absoluteSignal)):
        maximum = 0
        for lookbackIndex in range (intervalLength):
            maximum = max (absoluteSignal [baseIndex - lookbackIndex], maximum)
        outputSignal.append (maximum)

    return outputSignal


##################################
#Loop over sound files in directory

for root, sub, files in os.walk(r_dir):
    files = sorted(files)
    for f in files:       
        if f.endswith(".wav"):
            w= scipy.io.wavfile.read(os.path.join(root, f))
            base=os.path.basename(f.replace(".wav",""))
            dir = os.path.dirname(base)
            print(os.path.isdir(base))
            if not os.path.isdir(base):
                os.mkdir(base)       


            x     = w[1]/max(w[1])
            x_size= x.size


            v1    = np.arange(float (x_size))# not stereo

            c     = np.c_[v1,x]



            cc=c.T #transpose

            x = cc[0]
            x1= cc[1]
  

  

        
        #Low Pass Frequency for Filter definition (envelope case 2)

            W2       = float(w_cut_simple)/w[0] #filter parameter Cut frequency over the sample frequency
            (b2, a2) = signal.butter(1, W2, btype='lowpass')        

            #Filter definition for our envelope (3) implementation

            W1       = float(w_cut)/w[0] #filter parameter Cut frequency over the sample frequency
            (b, a)   = signal.butter(4, W1, btype='lowpass')

            
            p        = np.arange(x_size)*float(1)/w[0]        
                      

            stop      = x_size
            step      = int(step_time*w[0]) # Time interval * sample rate
            intervalos= np.arange(0, x_size,step)

            print( intervalos)
            print('-------------------')
            print('The step: ',step)
            print('-------------------')

            time1=x*float(1)/w[0]

            ##chop time serie##

                      

  

            # envelope our implementation
            


            x2_part                   = x1
            aver_vs                   = getEnvelope(x2_part)
            filtered_aver_vs          = signal.filtfilt(b, a, aver_vs)
            time_part                 = time1

                #Figure definition
            pp.figure(figsize=(20,9.5*0.6))
            pp.title('Sound Signal')
            

                #Uncoment what envelope you whant to plot

            grid(True)

            #Signal
            label_S,= pp.plot(x*float(1)/w[0],x1, color='c',label='Time Signal',linewidth=0.05)

     
                # Our implementation #
                #envelope_pre,=pp.plot(time_part,aver,color='k',label='Second step for envelope',linewidth=1)# Pre-envelope                               
            envelope_3,= pp.plot(time_part,filtered_aver_vs/max(filtered_aver_vs), color='r',label='Final Peak aproach  envelope',linewidth=0.3)


            pp.ylabel('Amplitude [Arbitrary units]')        
            pp.xlim(0,max(time1)+0.001)
            pp.xticks(np.arange(0,max(time1),0.1),fontsize = 8)
            #pp.yticks(np.arange(-15000,15000+5000,5000),fontsize = 12)
            pp.tick_params( axis='x', labelbottom='off')
            pp.tick_params( axis='y', labelleft='off')
            
            pp.legend([label_S,envelope_3],['Time Signal','Final Peak aproach  envelope'],fontsize= 'x-small',loc=4)

        
            figname = "%s.png" %(str(base))    
            pp.savefig(os.path.join(base,figname),dpi=400)
            pp.close('all')

            ###############################################################
            #save in plot file txt with data if necesary

            #f_out     = open('plots/%s.txt' %(str(base)+'_'+str(delta_t*float(1)/float(w[0]))), 'w')                
            #xxx       = np.c_[time_part,x2_part,filtered_aver,filtered_aver_vs]
            #np.savetxt(f_out,xxx,fmt='%f %f %f %f',delimiter='\t',header="time   #sound   #sound-evelope   #vS-envelope") 
                                              
            print ('.---All rigth!!!----.')



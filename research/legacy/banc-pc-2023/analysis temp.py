# -*- coding: utf-8 -*-
"""
Created on Wed Jul 19 20:39:18 2023

@author: labodezao
"""


#%%Enveloppes
imf = emd.sift.sift(x)
IP, IF, IA = emd.spectra.frequency_transform(imf, sample_rate, 'hilbert')
freq_range = (0.1, 10, 80, 'log')
f, hht = emd.spectra.hilberthuang(IF, IA, freq_range, sum_time=False)

#%%Data analysis
upper_env = emd.sift.interp_envelope(x, mode='upper')
lower_env = emd.sift.interp_envelope(x, mode='lower')
avg_env = (upper_env+lower_env) / 2


#%%plots
emd.plotting.plot_imfs(imf)
fig = plt.figure(figsize=(10, 6))
emd.plotting.plot_hilberthuang(hht, time_vect, f,
                               time_lims=(2, 4), freq_lims=(0.1, 15),
                               fig=fig, log_y=True)


#%% Sonometer
# mic sensitivity correction and bit conversion
mic_sens_dBV = 47.0 # mic sensitivity in dBV + any gain
mic_sens_corr = np.power(10.0,mic_sens_dBV/20.0) # calculate mic sensitivity conversion factor

f_vec = samp_rate*np.arange(chunk/2)/chunk # frequency vector based on window size and sample rate
# A-weighting function and application
f_vec = f_vec[1:]
R_a = ((12194.0**2)*np.power(f_vec,4))/(((np.power(f_vec,2)+20.6**2)*np.sqrt((np.power(f_vec,2)+107.7**2)*(np.power(f_vec,2)+737.9**2))*(np.power(f_vec,2)+12194.0**2)))
a_weight_data_f = (20*np.log10(R_a)+2.0)+(20*np.log10(fft_data[1:]/0.00002))
a_weight_sum = np.sum(np.power(10,a_weight_data_f/20)*0.00002)
print(20*np.log10(a_weight_sum/0.00002))
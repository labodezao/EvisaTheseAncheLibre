# -*- coding: utf-8 -*-
"""
Created on Fri Apr 14 22:06:37 2023

@author: labodezao
"""
import h5py

Decoupe_Sections = 8       # int
Decoupe_Pressions = 8      # int
Decoupe_Clapet = 8         # int
with h5py.File('test.hdf5', 'w') as f:
	Mesures_Press = f.create_dataset('Mesures_Press', (2,Decoupe_Clapet,Decoupe_Sections, Decoupe_Pressions,Decoupe_Clapet,2,1),  maxshape=(2,Decoupe_Clapet,Decoupe_Sections, Decoupe_Pressions,Decoupe_Clapet,2, None ))
	print(Mesures_Press.shape )
print('lalala')



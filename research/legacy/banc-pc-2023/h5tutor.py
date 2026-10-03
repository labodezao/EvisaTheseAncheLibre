# -*- coding: utf-8 -*-
"""
Created on Fri Apr 14 21:30:38 2023

@author: labodezao
"""
import h5py
import numpy as np

with h5py.File('movie_dataset.hdf5', 'w') as f:
   d = f.create_dataset('dataset', (1024, 1024, 1),  maxshape=(1024, 1024, None ))
   d.resize((1024,1024,2))

d.resize((1024,1024,2))
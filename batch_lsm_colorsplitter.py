# -*- coding: utf-8 -*-
"""
Created on Wed Jan 14 13:13:02 2015

@author: georg
"""
import IOtools as io
import sys
import os
    
filelist_file = sys.argv[1]

with open(filelist_file,'r') as fH:
        paths = [line.strip() for line in fH.readlines()]

for path in paths:
    print "processing file: " + path
#    outpath = os.path.splitext(path)[0] + '.tif'
    io.split_color_lsm(path)

#sys.stdout.write("\n") # move the cursor to the next line
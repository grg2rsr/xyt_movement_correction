# -*- coding: utf-8 -*-
"""
Created on Mon Sep 29 15:42:37 2014

@author: georg
"""

"""
a submitter script for aligning movement correcting a two-color measurement. The
background channel is used for calculating the transforms, which are also applied
to the signal channel. See xyt_movement_correction_lib.movement_correct_two_color()
for a detailed description.

submitter is called with 
    first argument: path to tiff file that serves as the background template
    second argument: path to the tiff file that gets the same transformation as
        the first argument ('signal')
    third argument: stimulus onset frame number
    
"""

#==============================================================================
# IMPORTS
#==============================================================================
import scipy as sp
import sys
import os

import IOtools as io
import xyt_movement_correction_lib as moco


#==============================================================================
# flags
#==============================================================================
tmp_mode = True # writes all elastix files to the scratch of the clusters node or to /tmp
cleanup = True # if True delete all elastix generated files afterwards

#==============================================================================
# run
#==============================================================================

if __name__ == '__main__':
    
    ### args
    data_bg_path = os.path.abspath(sys.argv[1]) # path to background tstack
    data_sg_path = os.path.abspath(sys.argv[2]) # path to signal tstack
    odor_onset_frame = sp.int16(sys.argv[3])
    
    data_bg_path_orig = data_bg_path    
    data_sg_path_orig = data_sg_path

    ### preparations    
    if tmp_mode == True: 
        data_bg_path = moco.make_tmp_dir(data_bg_path)
        data_sg_path = moco.make_tmp_dir(data_sg_path)        
        
    data_bg_transformed, data_sg_transformed = moco.movement_correct_two_color(data_bg_path, data_sg_path, odor_onset_frame)
    io.save_tstack(data_bg_transformed,os.path.splitext(data_bg_path_orig)[0] + '_bg_moco.tif')
    io.save_tstack(data_sg_transformed,os.path.splitext(data_sg_path_orig)[0] + '_sg_moco.tif')   
    
    if cleanup:
        moco.cleanup(data_bg_path)
        moco.cleanup(data_sg_path) # only one needed? TEST 
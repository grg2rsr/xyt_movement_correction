# -*- coding: utf-8 -*-
"""
Created on Mon Sep 29 15:42:37 2014

@author: georg
"""

"""
a submitter script for movement correction of a xyt tiff stack (t is the pages).
See xyt_movement_correction_lib.movement_correct_tstack() for a detailed
description.

submitter is called with 
    first argument: path to tiff file
    second argument: stimulus onset frame number
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
tmp_mode = True # if True writes all elastix files to the scratch of the clusters node or to /tmp, if not uses the same folder as the data
cleanup = True # if True delete all elastix generated files afterwards

#==============================================================================
# run
#==============================================================================

if __name__ == '__main__':
    
    ### nontesting
    data_path = os.path.abspath(sys.argv[1])
    odor_onset_frame = sp.int16(sys.argv[2])

    ### testings    
#    data_path = '/home/georg/python/xyt_movement_correction/test_data/stack_trunc.tif'    
#    odor_onset_frame = 5
    
    ### preparations
    data_path_orig = data_path
    if tmp_mode:
        data_path = moco.make_tmp_dir(data_path) 
    
    ### run
    data_affine_transformed, data_signal, data_background, data_background_bspline_transformed, data_bspline_transformed = moco.movement_correct_tstack(data_path,odor_onset_frame)
    
    ### save
    io.save_tstack(data_affine_transformed,os.path.splitext(data_path_orig)[0] + '_affine.tif')
    io.save_tstack(data_signal,os.path.splitext(data_path_orig)[0] + '_signal.tif')
    io.save_tstack(data_background,os.path.splitext(data_path_orig)[0] + '_background.tif')
    io.save_tstack(data_background_bspline_transformed,os.path.splitext(data_path_orig)[0] + '_background_bspline.tif') # this one is needed for multicolor correction!
    io.save_tstack(data_bspline_transformed,os.path.splitext(data_path_orig)[0] + '_full.tif')
    
    ### cleanup
    if cleanup:
        moco.cleanup(data_path)

# -*- coding: utf-8 -*-
"""
Created on Mon Sep 29 15:48:34 2014

@author: georg
"""

"""
a submitter script for aligning multiple xyt measurements to a common reference.
See xyt_movement_correction_lib.align_tstacks() for a detailed description.

submitter is called with 
    first argument: path to single tiff file (tstack, t in individual tiff pages)
    second argument: a file containing the paths to the other tiff files from
        the experiment. One path per line.
"""

#==============================================================================
# IMPORTS
#==============================================================================

import sys
import os

import IOtools as io
import xyt_movement_correction_lib as moco


#==============================================================================
# flags
#==============================================================================
tmp_mode = True # writes all elastix files to the scratch of the clusters node or to /tmp
cleanup = True # if True delete all elastix generated files afterwards
verbose = True

if __name__ == '__main__':

    ### args
    data_path = os.path.abspath(sys.argv[1]) # path to the individual tstack that is to be aligned based on the tstacks whose paths are in the tstack_paths_file
    tstack_paths_file = sys.argv[2] # file containing the paths to the stacks from which the global reference is generated
    
    if verbose:
        print
        print "### multi stack align ###"
        print 'data file: ',data_path
        print 'tstacks file: ',tstack_paths_file
        
    subdir = None
    if len(sys.argv) == 4:
        # third argument specifies subfolder for output
        subdir = sys.argv[3]
        if verbose:
            print 'output subdirectory: ',subdir
    
    print 'all args', sys.argv
    
    with open(tstack_paths_file,'r') as fH:
        tstack_paths = [os.path.abspath(line.strip()) for line in fH.readlines()]
        
    ### preparations
    data_path_orig = data_path
    
    if tmp_mode:
        if verbose:
            print "running in tmp mode"
        # copying the data to the scratch
        data_path = moco.make_tmp_dir(data_path)
        
        # also copying the background_bspline to scratch. it needs to be in the same folder
#        bspline_path = os.path.splitext(data_path_orig)[0][:-5] + '_background_bspline.tif'  # FIXME: hardcoded -5 remove a '_full'
        bspline_path = '_'.join(data_path_orig.split('_')[:-1]) + '_background_bspline.tif' # fix       
        bspline_path = moco.make_tmp_dir(bspline_path) # the bpline file is copied into the same folder than the data (PID named)
    
    if verbose:
        print "running align ... "
    data_affine_aligned, data_bspline_aligned, ref_img_global = moco.align_tstacks(data_path,tstack_paths)
    
    # output path generation:
    if subdir:
        outdir = os.path.join(os.path.dirname(data_path_orig),subdir)
        moco.makedirs(outdir)
        pass
    else:
        outdir = os.path.dirname(data_path_orig)
    
    # save in same folder, append 'affineglobal.tif' / 'bsplineglobal.tif'
    affine_path = os.path.join(outdir,os.path.splitext(os.path.basename(data_path_orig))[0] + 'affineglobal.tif') # lacking underscore in name to circumvent .lst compatibility problems
    bspline_path = os.path.join(outdir,os.path.splitext(os.path.basename(data_path_orig))[0] + 'bsplineglobal.tif')

    if verbose:
        print "output directory: ", outdir
        print "affine path: ", affine_path
        print "bspline path: ", bspline_path

    io.save_tstack(data_affine_aligned,affine_path) 
    io.save_tstack(data_bspline_aligned,bspline_path)
    
    io.save_tiff(ref_img_global,os.path.dirname(data_path_orig) + '/ref_img_global.tif')
#    tifffile.imsave(os.path.dirname(data_path_orig) + '/ref_img_global.tif',ref_img_global.T)
    
    if cleanup:
        if verbose:
            print "running cleanup"
        moco.cleanup(data_path)

    if verbose:
        print "all done!"
        print
    
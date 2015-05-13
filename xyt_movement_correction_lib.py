# -*- coding: utf-8 -*-
"""
Created on Wed Sep  4 14:24:54 2013

@author: georg
"""

"""

SUMMARY: This library provides tools for a movement correction for xyt stacks. For 
linear and nonlinear movement correction, the elastix package is used 
(http://elastix.isi.uu.nl/index.php)

3 Corrections are implemented: movement_correct_tstack, align_tstacks and 

DETAILS: Transformix and Elastix need the data to be in the .mhd format. For
this, all ndarrays are dumped on disk at the location specifyed by the variable 
tmp_path, where a folder named with the Process ID is created where all temp
data is written. If the cleanup flag is set in the calling scripts, this is 
deleted after the correction run.

Image data needs to be in the tiff format and tiff2nparray conversions are all
handled by the tifffile library. Image data is assumed to be 16 bit.
  
LINKS:
http://www.lfd.uci.edu/~gohlke/code/tifffile.py.html
http://elastix.isi.uu.nl/index.php

"""

#==============================================================================
# IMPORTS
#==============================================================================
import scipy as sp

import sys
import time
import os
import subprocess
import scipy.ndimage as ndimage
import tifffile as tifffile
import IOtools as io

#==============================================================================
### CONSTANTS DECLARATIONS
#==============================================================================

# flags
cluster = True # configured for the hpc2
testing = False  # runs with low res/few iterations
verbose = False # for full elastix output

toplevel_dir = os.path.split(os.path.realpath(__file__))[0]

# normal parameter files
if not(testing):
    bspline_parameters_path = toplevel_dir + '/parameters_bspline.txt'
    affine_parameters_path = toplevel_dir + '/parameters_affine.txt'
    bspline_lowres_parameters_path = toplevel_dir + '/parameters_bspline_lowres.txt'

# parameter files for testing
if testing:
    bspline_parameters_path = toplevel_dir + '/parameters_bspline_testing.txt'
    affine_parameters_path = toplevel_dir + '/parameters_affine_testing.txt'
    bspline_lowres_parameters_path = toplevel_dir + '/parameters_bspline_lowres_testing.txt'

# cluster:
if cluster:
    elastix_bin = '/home/graiser/elastix/bin/elastix'
    transformix_bin = '/home/graiser/elastix/bin/transformix'
    tmp_path = '/scratch/data/graiser'
   
# Desktop
if not(cluster):
    elastix_bin = 'elastix'
    transformix_bin = 'transformix'
#    elastix_bin = '/home/georg/programs/elastix/bin/elastix'
#    transformix_bin = '/home/georg/programs/elastix/bin/elastix/transformix'
    tmp_path = '/tmp'


#==============================================================================
### MISC HELPERS
#==============================================================================

def calc_ref_img(data,odor_onset_frame):
    """ generates a reference image for registration based on the frames before
    the odor onset, by simple average along z axis"""
    ref_img = sp.average(data[:,:,:odor_onset_frame],axis=2)
    ref_img = ref_img.astype('uint16')
    return ref_img

def makedirs(path):
    try:
        os.makedirs(path)
    except OSError:
        pass
    
def calc_ref_stack(tstack_paths,odor_onset_frame=None):
    """ for aligning multiple, tstack_paths is a list containing the paths to the
    individual stacks """
    
    # allocate
    x,y,z = io.read_tiffstack(tstack_paths[0]).shape
    n = len(tstack_paths)
    ref_stack = sp.zeros((x,y,n))
    
    for i,path in enumerate(tstack_paths):
        """ if a _background_bspline file exists in the directory, use it! This
        is usually the case as a normal registration protocoll was run on the 
        individual files
        if _background_bspline.tif doesn't exist, use regular calculation"""
        bspline_path = os.path.splitext(path)[0][:-5] + '_background_bspline.tif'  # HARDCODED: the -5 remove a '_full' FIXME
        if os.path.exists(bspline_path):
            ref_stack[:,:,i] = sp.average(io.read_tiffstack(bspline_path),axis=2)
        else:
            ref_stack[:,:,i] = calc_ref_img(io.read_tiffstack(path),odor_onset_frame)
        pass
    
    return ref_stack.astype('uint16')
    
def make_tmp_dir(data_path):
    """ copies the data to scratch into folder named with the processes ID """
    tmpdir_path = tmp_path + '/' + str(os.getpid())
    makedirs(tmpdir_path)
    command = ' '.join(['cp',data_path,tmpdir_path])
    subprocess.call(command,shell=True)
    
    data_path_tmp = tmpdir_path + '/' + os.path.basename(data_path)
    
    # FIXME dirty workaround again, see run elastix for possible solution
    while not(os.path.exists(data_path_tmp)):
        time.sleep(1)
        pass    
    
    return data_path_tmp
    
def cleanup(data_path):
    """ removing all elastix generated files, which are placed under 
    data_path/elastix/exp_name by convention """
    print "removing all elastix generated files ... "
    exp_name = get_exp_name(data_path)
    command = 'rm -r ' + os.path.split(data_path)[0] + '/elastix/' + exp_name
    print command
    out = subprocess.call(command,shell=True)
    if out != 0:
        print "error occured during remove, code: " + str(out)
        
def get_exp_name(path):
    """ this corresponds to the name of the experiment file e.g. '../../testdata.tif' -> 'testdata' """
    return os.path.splitext(os.path.basename(path))[0]
    
#==============================================================================
### HELPERS elastix
#==============================================================================

def run_elastix(img,ref_img,parameter_filepath,outpath):
    """ this function recieves the data as np arrays, generates the mhd files in 
    the directory outpath, runs elastix with the parameter_file on it. input
    and output files are thus going to be in the same directory.
    Then the mhd file is read again and returned as an array """

    # make the directories
    makedirs(outpath)
    
    # write tiffs into outpath
    img_tiffpath = outpath + '/image.tif'
    io.save_tiff(img,img_tiffpath)    
    
    ref_img_tiffpath = outpath + '/ref_image.tif'       
    io.save_tiff(ref_img,ref_img_tiffpath)

    # generate mhd files
    img_mhdpath = os.path.splitext(img_tiffpath)[0] + '.mhd'
    io.tiff2mhd(img_tiffpath,outpath=img_mhdpath,dtype='float32')
    
    ref_img_mhdpath = os.path.splitext(ref_img_tiffpath)[0] + '.mhd'
    io.tiff2mhd(ref_img_tiffpath,ref_img_mhdpath,dtype='float32')
    
    # run elastix  
    command = ' '.join([elastix_bin,'-f','\''+ref_img_mhdpath+'\'','-m','\''+img_mhdpath+'\'','-out','\''+outpath+'\'','-p','\''+parameter_filepath+'\''])
    
    # silencing output: http://stackoverflow.com/questions/11269575/how-to-hide-output-of-subprocess-in-python-2-7
    if verbose:
        retcode = subprocess.call(command, shell=True)
    else:
        FNULL = open(os.devnull, 'w')
        retcode = subprocess.call(command, shell=True, stdout=FNULL, stderr=subprocess.STDOUT) # silenced shell
    
    if retcode != 0:
        print "Elastix error! ", retcode
        sys.exit()
        
    # FIXME needed
    # Problem: the cluster seems to start the processes completely detached
    # so the script continues to run here and then read_mhd fails because
    # there is nothing yet to read
    # dirty hack with sleep
        
    while not(os.path.exists(outpath + '/result.0.mhd')):
        time.sleep(2)
        pass

    # possible solution from http://stackoverflow.com/questions/4965159/python-how-to-redirect-output-with-subprocess
    # needs to be tested on cluster!
#    p = subprocess.Popen(my_cmd, shell=True)
#    os.waitpid(p.pid, 0)    
    
    # read elastix output, convert it to uint16 tif
    output = io.read_mhd(outpath + '/result.0.mhd')
    output = output.clip(0.0,2.0**16).astype('uint16')
    
    # dump elastix output for inspection
    io.mhd2tiff(outpath + '/result.0.mhd')
    return output

def run_transformix(img_mhdpath,transformation_filepath,outpath):
    """
    executes the transformix call, reads the result mhd afterwards and returns
    the array of the transformed data
    """
    # run transformix
    command = ' '.join([transformix_bin,'-def all -in','\''+img_mhdpath+'\'','-out','\''+outpath+'\'','-tp','\''+transformation_filepath+'\''])
    
    if verbose:
        retcode = subprocess.call(command, shell=True)
    else:
        FNULL = open(os.devnull, 'w')
        retcode = subprocess.call(command, shell=True, stdout=FNULL, stderr=subprocess.STDOUT) # silenced
       
    
    if retcode != 0:
        print "Transformix error! ", retcode
        sys.exit()    
    
    output = io.read_mhd(outpath + '/result.mhd').clip(0.0,2.0**16).astype('uint16')
    
    # dump transformix output for inspection
    io.mhd2tiff(outpath + '/result.mhd')
    
    return output


#==============================================================================
### transformations
#==============================================================================
    
    
def transform_tstack(data, data_path, ref_img, output_subdir='', mode='affine'):
    """
    loops over the frames in a xyt stack and applies the specified transform in
    the kwarg mode to the ref_img. This generates also the transform_parameters
    files, so this routine actually applies and finds transformations.
        
    data_path is the path to the xyt stack
    
    ref_img is the reference image to which data is registered
    
    output_subdir is the name of the output directory under .../elastix/'exp_name'/output_subdir
    
    mode is either affine or bspline
        
    infos on inverse transform
    http://lists.bigr.nl/pipermail/elastix/2012-August/000892.html
    """
#    print "finding inverse transform", os.path.basename(path)
    
    data_transformed = sp.zeros(data.shape)
    
    print "processing file:", data_path
    print "transform mode", mode
    
    if mode == 'affine':
        parameters_path = affine_parameters_path
    if mode == 'bspline':
        parameters_path = bspline_parameters_path
    if mode == 'bspline_lowres':
        parameters_path = bspline_lowres_parameters_path
        
    for frame in range(data.shape[2]):
        elastix_subdir = os.path.dirname(data_path) + '/elastix'
        exp_name = get_exp_name(data_path) 
        frame_i_of_n = 'frame_' + str(frame) + '_' + str(data.shape[2]) # FIXME this has a zeroth frame?
        
        tempdir = elastix_subdir + '/' + exp_name + '/' + output_subdir + '/' + frame_i_of_n
        makedirs(tempdir)
        
        print "frame ", str(frame), "/",str(data.shape[2])
        output = run_elastix(data[:,:,frame],ref_img,parameters_path,tempdir)
        
        data_transformed[:,:,frame] = output 
        
    return data_transformed.clip(0,65536).astype('uint16')

def apply_transform(data, data_path, tp_paths, output_subdir=''):
    """
    applies transforms from another elastix run to a xyt stack using transformix
    
    data is the xyt array that is to be transformed
    
    data_path is the path to the data, however, this can also be a different path:
    From this the experiment name is deduced, so for example when applying 
    transformations accross channels, this can be always be the path of the first
    channel
    
    tp_paths is a list of paths to each individual tp file. This allows to have
    one transformation applied to different frames    
    
    output_subdir has the same behaviour as in transform_tstack
    """
    
    
#    data = sp.swapaxes(data,0,1)
    data_transformed = sp.zeros(data.shape)
    
    ### folder preparations
    elastix_subdir = os.path.dirname(data_path) + '/elastix'
    exp_name = get_exp_name(data_path)
    
    print "running transformix: ", data_path
    
    for frame in range(data.shape[2]):

        ## folder for thie iteration        
        frame_i_of_n = 'frame_' + str(frame) + '_' + str(data.shape[2])
        tempdir = elastix_subdir + '/' + exp_name + '/' + output_subdir + '/' + frame_i_of_n 
        makedirs(tempdir)

        # dumping the array to tiff and convert to mhd
        tifpath = tempdir + '/frame.tif'
#        tifffile.imsave(tifpath,data[:,:,frame]) # FIXME kickme
        io.save_tiff(data[:,:,frame],tifpath)
        mhd_path = os.path.splitext(tifpath)[0] + '.mhd'
        io.tiff2mhd(tifpath,mhd_path,dtype='float32')
        
        transform_parameter_filepath = tp_paths[frame]
                
        # run transformix
        output = run_transformix(mhd_path, transform_parameter_filepath,tempdir)
        
        data_transformed[:,:,frame] = output
        pass
    
    return data_transformed.clip(0,65536).astype('uint16')

       
  

#==============================================================================
### main functions
#==============================================================================


#==============================================================================
# single
#==============================================================================
def movement_correct_tstack(data_path, odor_onset_frame, ref_img=None):
    """
    data_path: the full absolute path to the xyt tiff stack
    odor_onset_frame: an int defining the last frame without response
    ref_img: if provided, align to this
    
    The movement correction procedure takes the following steps:
    1) An average frame of the first frames before odor onset is computed. This
    is the reference image.
    2) An affine transform of each frame of the stack to the ref_img is computed
    3) The ref_img is substracted from each frame of this stack, leading to a stack
    containing only the signal
    4) The signal stack is substracted from the affine corrected stack. This results
    in a stack with only the background
    5) a new ref_img is computed on the by averaging the full background stack
    6) The transformation for a nonlinear bspline transform of the background stack
    to the new ref_img is computed. This transformation is not applied, but saved
    7) the nonlinear transformation is applied to the result of step 2) , the affine
    corrected stack including the signals. This is the final result.
    
    This two stage correction, first affine, then nonlinear works well on images in
    which the shape of the structure does not change much, but has a lot of xy 
    movement. The nonlinear correction can actually be worse than the affine, but 
    can also lead to a significant improvement.
    """
    
    data = io.read_tiffstack(data_path)
         
    # 1) generating a reference image out of the first few images from the stack
    if ref_img == None:
        ref_img = calc_ref_img(data,odor_onset_frame)
    
    # 2) registering all images to the reference image using affine transform
    data_affine_transformed = transform_tstack(data, data_path, ref_img, output_subdir='affine', mode='affine')
    
    # generating a new (better) reference image
    ref_img_affine_transformed = calc_ref_img(data_affine_transformed,odor_onset_frame)
    
    # 3) extracting the signal
    data_signal = data_affine_transformed.astype('float') - ref_img_affine_transformed[:,:,sp.newaxis].astype('float')
    data_signal = data_signal.clip(0,65536).astype('uint16')
    
    # smoothing the signal
    data_signal_filt = sp.zeros(data_signal.shape)
    for frame in range(data_signal.shape[2]):
        data_signal_filt[:,:,frame] = ndimage.gaussian_filter(data_signal[:,:,frame],sigma=0.75)
        pass
    data_signal_filt = data_signal_filt.clip(0,65536).astype('uint16')
    
    # 4) extracting the background
    data_background = data_affine_transformed.astype('float') - data_signal_filt.astype('float')
    data_background = data_background.clip(0,65536).astype('uint16')

    # 5) generating average background image
    ref_img_background = calc_ref_img(data_background,data.shape[2])
    
    # 6) finding bspline transform for each background image to the average
    data_background_bspline_transformed = transform_tstack(data_background, data_path, ref_img_background, output_subdir='bspline', mode='bspline')
    """just for completeness: in this call, the data_path is not the path of data, as data doesn't have a path. 
    However, it is kept because inside the function the exp name is deduced from data_path"""
        
    # 7) applying the transform to the affine registered data containing the signal
    exp_name = get_exp_name(data_path)

    tp_paths = []
    for frame in range(data.shape[2]):
        frame_i_of_n = 'frame_' + str(frame) + '_' + str(data.shape[2])
        tp_path =  os.path.dirname(data_path) + '/elastix/' + exp_name + '/bspline/' + frame_i_of_n + '/TransformParameters.0.txt'
        tp_paths.append(tp_path)
    
    data_bspline_transformed = apply_transform(data_affine_transformed, data_path, tp_paths, output_subdir='bspline_on_signal')
    """ the same as above applies here. data_path is the path to the original data, what is transformed here is data_affine_transformed"""
                
        
    return data_affine_transformed, data_signal, data_background, data_background_bspline_transformed, data_bspline_transformed


#==============================================================================
# multiple
#==============================================================================

def align_tstacks(data_path,tstack_paths,reference_mode='first'):
    """ this function is used to align a single trial to a set of other tirals to
    a common reference. This reference is chosen depending on the keyword
    reference_mode: if 'first', the time average of the first trial in the 
    tstack_paths list is taken (from background bspline), if 'global', a global
    average from all trials is computed.
    
    data_path: path to the tstack that will be aligned
    tstack_paths: a list with paths to the other tstacks of the experiment
    
    the alignment is computed as a 2 step process, first affine 
    and then bspline. Both are returned
    """
    
    print "aligning dataset ", data_path
    
    data = io.read_tiffstack(data_path)
    
    # calculate global reference image - the first measurement is defined as the
    # 'global goal'
    ref_stack = calc_ref_stack(tstack_paths)
    
    if reference_mode == 'first':
        ref_img_global = ref_stack[:,:,0].astype('uint16')
    
    if reference_mode == 'global':
        ref_img_global = sp.average(ref_stack,axis=2).astype('uint16')
        # Note: this performs usually worse than first, but is less arbitrary
           
    # compute one transform of the average of each stack to the global ref, then apply this transform to all the frames in the stack
#    bspline_path = os.path.splitext(data_path)[0][:-5] + '_background_bspline.tif'  # FIXME HARDCODED: the -5 remove a '_full'
    bspline_path = '_'.join(data_path.split('_')[:-1]) + '_background_bspline.tif' # fix  

    # this block is hacked in to deal with the aljas dataset, can be ignored in all others:
    # if existing, use the bspline_background as a basis to calculate the reference
    if os.path.exists(bspline_path):
        data_avg = sp.average(io.read_tiffstack(bspline_path),axis=2)
    else:
        data_avg = calc_ref_img(data,20)
        pass    
    
    # this should be sufficient in the future
#    data_avg = sp.average(io.read_tiffstack(bspline_path),axis=2)    
    
    exp_name = get_exp_name(data_path)
    
    ## first pass: affine
    # find transform ...    
    outpath = os.path.split(data_path)[0] + '/elastix/' + exp_name + '/global_affine'
    makedirs(outpath)
    run_elastix(data_avg,ref_img_global,affine_parameters_path,outpath)
    
    # ... and apply to each frame
    transform_parameters_filepath = outpath + '/TransformParameters.0.txt'
    tp_paths = [transform_parameters_filepath] * data.shape[2]
    data_affine_aligned = apply_transform(data, data_path, tp_paths, output_subdir='affine_aligned')
    bspline_data_affine_aligned = apply_transform(io.read_tiffstack(bspline_path), bspline_path, tp_paths, output_subdir='bspline_affine_aligned')
    
    # generate new avg
    data_avg_after_affine = sp.average(bspline_data_affine_aligned,axis=2)
    
    ## second pass: bspline    
    # find transform ...    
    outpath = os.path.split(data_path)[0] + '/elastix/' + exp_name + '/global_bspline'
    makedirs(outpath)
    run_elastix(data_avg_after_affine,ref_img_global,bspline_lowres_parameters_path,outpath)
    
    # ... and apply to each frame
    transform_parameters_filepath = outpath + '/TransformParameters.0.txt'
    tp_paths = [transform_parameters_filepath] * data.shape[2]
        
    data_bspline_aligned = apply_transform(data_affine_aligned, data_path, tp_paths, output_subdir='bspline_aligned')
    
    return data_affine_aligned, data_bspline_aligned, ref_img_global


#==============================================================================
# 2 channel, one ref
#==============================================================================

def movement_correct_two_color(data_bg_path,data_sg_path,odor_onset_frame):
    """
    ARGUMENTS:
    data_bg_path: absolute path to the xyt stack with the background/reference channel
    data_sg_path: absolute path to the xyt stack with the signal, that will receive all transformations
    odor_onset_frame: last frame without a repsonse

    DESCRIPTION:
    Corrects for movement in two seperate files, one being a background/reference
    channel onto which all transformations are computed and applied, and one 
    being a signal channel which also gets all the transformations computed on 
    the reference channel
    
    NOTES:
    Initially written for kristinas data: one channel is background (mb staining)
    one channel is the signal.
    
    abbreviations in this script:
    bg = background
    sg = signal
    
    For now, only affine is applied
    
    """

    # read
    data_bg = io.read_tiffstack(data_bg_path)
    data_sg = io.read_tiffstack(data_sg_path)
    
    # calc ref img
    ref_img = calc_ref_img(data_bg, odor_onset_frame)
    
    # registering all images to the reference image using affine transform
    data_bg_transformed = transform_tstack(data_bg, data_bg_path, ref_img, output_subdir='affine', mode='affine')

    # applying the same transform to the signal channel
    exp_name = get_exp_name(data_bg_path)

    tp_paths = []
    for frame in range(data_bg.shape[2]):
        frame_i_of_n = 'frame_' + str(frame) + '_' + str(data_bg.shape[2])
        tp_path =  os.path.dirname(data_bg_path) + '/elastix/' + exp_name + '/affine/' + frame_i_of_n + '/TransformParameters.0.txt'
        tp_paths.append(tp_path)
    
    data_sg_transformed = apply_transform(data_sg, data_sg_path, tp_paths, output_subdir='affine_from_bg_on_signal')
    
    return data_bg_transformed, data_sg_transformed

if __name__ == '__main__':
    print "use submitter scripts to run"


    
    
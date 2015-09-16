
# xyt_movement_correction
## Overview

A python toolkit based on `elastix` to remove xy movement artifacts from `xyt` functional imaging data. In experiments such as calcium imaging from neurons, the goal is to extract time-traces based on pixel coordinates from the recorded `xyt`-data.
Brain movement makes it difficult to reliably extract signals from a specific point in the measurement over time within a trial, as well as for example drifts over longer time spans. Therefore, image registration techniques can help to  maintain the same morphological structures at the same coordinates during the timespan of the experiment as a postprocessing step.

## Usage
There are several python scripts for executing individual functions. Currently, the image data has to be in the `.tiff` format, in which the tiff pages are the individual `xy`-frames, and each consecutive page is a time point (a converter for the Zeiss `.lsm` format is included).

### remove xy movement from a single trial
`python single_stack_aligner.py data.tif onset_frame`
+ `data.tif` is the path to your data that will be transformed
+ `stimulus_onset_frame` is the number of the last frame without stimulus induced activiy, this is used to calculate the background activity

removes xy movement based on the following steps:

1. An average frame of the first frames before odor onset is computed. This is the initial reference image.
2. An affine transform of each frame of the stack to the reference image is computed and applied to each frame.
3. The reference is substracted from each frame of this stack, leading to a stack containing only the signal.
4. The signal stack is substracted from the affine corrected stack. This results in a stack with only the background.
5. A new reference image is computed on the by averaging the background stack
6. The transformation for a nonlinear bspline transform of the background stack to the new reference is calculated.
7. The resulting transform of step 6. is applied to the result of step 2), the affine corrected stack including the signals. This is the final result.

### align several trials with each other
`python multi_stack_aligner.py data.tif file_list.txt`
+ `data.tif` is the path to your data that will be transformed
+ `file_list.txt` is a file that contains paths to the data of the other trials of the measurement

this function is used to align a single trial to a set of other trials. If this is applied to all trials within a single measurement session, they will be aligned to a 'common morphological space'

### remove xy movement based on a background signal
`python multicolor_stack_aligner.py data_template.tif data_signal.tif stimulus_onset_frame `
+ `data_template.tif` path to the data that contains the background or template data
+ `data_signal.tif` path to the data that contains the actual signal

for two-color imaging experiments, such as when RFP is used as a neuropil marker, and GCaMP is used for recording the neuronal activity, the RFP signal can be used to serve as a template for calculating the transformations that will then be applied to both channels.

## Dependencies
+ elastix http://elastix.isi.uu.nl/
+ scipy


# -*- coding: utf-8 -*-
"""
Created on Fri Sep 16 12:00:45 2016

@author: jelman

This script takes Tobii .gazedata file from HVLT recall-rocgnition as input. It 
first performs interpolation and filtering, The first 1 sec of recall instructions 
is used as baseline. Dilation at each second is produced. 

Some procedures and parameters adapted from:
Jackson, I. and Sirois, S. (2009), Infant cognition: going full factorial 
    with pupil dilation. Developmental Science, 12: 670-679. 
    doi:10.1111/j.1467-7687.2008.00805.x

Hoeks, B. & Levelt, W.J.M. Behavior Research Methods, Instruments, & 
    Computers (1993) 25: 16. https://doi.org/10.3758/BF03204445
"""

from __future__ import division, print_function, absolute_import
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import pupil_utils
try:
    # for Python2
    import Tkinter as tkinter
    import tkFileDialog as filedialog
except ImportError:
    # for Python3
    import tkinter
    from tkinter import filedialog


def plot_trials(pupildf, fname):
    sns.set_style("ticks")
    p = sns.lineplot(data=pupildf, x="Timestamp",y="Dilation")
    plt.tight_layout()
    plot_outname = pupil_utils.get_proc_outfile(fname, "_PupilPlot.png")
    plot_outname = plot_outname.replace("-Delay","-Recall")
    p.figure.savefig(plot_outname)
    plt.close()
    
    
def clean_trials(df):
        dfresamp = pupil_utils.resamp_filt_data(df, filt_type='low', string_cols=['CurrentObject'])
        baseline = dfresamp['DiameterPupilLRFilt'].first('1000ms').mean()
        dfresamp['Baseline'] = baseline
        dfresamp['Dilation'] = dfresamp['DiameterPupilLRFilt'] - dfresamp['Baseline']
        dfresamp = dfresamp[dfresamp.CurrentObject=='Recall']
        dfresamp.index = pd.to_datetime((dfresamp.index - dfresamp.index[0]).total_seconds(), unit='s')
        return dfresamp
        
   
def proc_subject(filelist):
    """Given an infile of raw pupil data, saves out:
        1. Session level data with dilation data summarized for each trial
        2. Dataframe of average peristumulus timecourse for each condition
        3. Plot of average peristumulus timecourse for each condition
        4. Percent of samples with blinks """
    for fname in filelist:
        print('Processing {}'.format(fname))
        if (os.path.splitext(fname)[-1] == ".gazedata") | (os.path.splitext(fname)[-1] == ".csv"):
            df = pd.read_csv(fname, sep="\t")
        elif os.path.splitext(fname)[-1] == ".xlsx":
            df = pd.read_excel(fname)
        else: 
            raise IOError('Could not open {}'.format(fname))
        subid = pupil_utils.get_subid(df['Subject'], fname)
        timepoint = pupil_utils.get_timepoint(df['Session'], fname)
        df = df[df.CurrentObject.str.contains("Recall", na=False)]
        df = pupil_utils.deblink(df)
        dfresamp = clean_trials(df)
        dfresamp1s = dfresamp.resample('1S', closed='right', label='right').mean()
        dfresamp1s.index = dfresamp1s.index.round('S')
        dfresamp1s = dfresamp1s.dropna(how='all')
        pupildf = dfresamp1s.reset_index().rename(columns={
                                            'index':'Timestamp',
                                            'DiameterPupilLRFilt':'Diameter',
                                            'BlinksLR':'BlinkPct'})
        pupilcols = ['Subject', 'Timestamp', 'Dilation',
                     'Baseline', 'Diameter', 'BlinkPct']
        pupildf = pupildf[pupilcols].sort_values(by='Timestamp')
        # Set subject ID and session as (as type string)
        pupildf['Subject'] = subid
        pupildf['Session'] = timepoint  
        pupil_outname = pupil_utils.get_proc_outfile(fname, '_ProcessedPupil.csv')
        pupil_outname = pupil_outname.replace("-Delay","-Recall")
        pupildf.to_csv(pupil_outname, index=False)
        print('Writing processed data to {0}'.format(pupil_outname))
        plot_trials(pupildf, fname)

        #### Create data for 15 second blocks
        dfresamp15s = pupildf.resample('15s', on='Timestamp', closed='right', label='right').mean()
        pupilcols = ['Subject', 'Trial', 'Condition', 'Timestamp', 'Dilation',
                     'Baseline', 'DiameterPupilLRFilt', 'BlinksLR']
        pupildf15s = dfresamp15s.reset_index()[pupilcols].sort_values(by=['Trial','Timestamp'])
        pupildf15s = pupildf15s[pupilcols].rename(columns={'DiameterPupilLRFilt':'Diameter',
                                         'BlinksLR':'BlinkPct'})
        # Set subject ID as (as type string)
        pupildf15s['Subject'] = subid
        pupildf15s['Timestamp'] = pd.to_datetime(pupildf15s.Timestamp).dt.strftime('%H:%M:%S')
        pupil15s_outname = pupil_utils.get_proc_outfile(fname, '_ProcessedPupil_Quartiles.csv')
        'Writing quartile data to {0}'.format(pupil15s_outname)
        pupildf15s.to_csv(pupil15s_outname, index=False)

    
if __name__ == '__main__':
    if len(sys.argv) == 1:
        print('')
        print('USAGE: {} <raw pupil file> '.format(os.path.basename(sys.argv[0])))
        print("""Processes single subject data from HVLT task and outputs csv
              files for use in further group analysis. Takes eye tracker data 
              text file (*.gazedata) as input. Removes artifacts, filters, and 
              calculates dilation per 1s.Also creates averages over 15s blocks.""")
        print('')
        root = tkinter.Tk()
        root.withdraw()
        # Select files to process
        filelist = filedialog.askopenfilenames(parent=root,
                                              title='Choose HVLT recall-recognition pupil gazedata file to process')       
        filelist = list(filelist)
        # Run script
        proc_subject(filelist)

    else:
        filelist = [os.path.abspath(f) for f in sys.argv[1:]]
        proc_subject(filelist)


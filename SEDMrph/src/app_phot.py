# -*- coding: utf-8 -*-
"""
Created on Sat May 23 18:23:02 2015

@author: nadiablago
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
from matplotlib import pylab as plt

try:
    from pyraf import iraf 
except:
    print "Not loading iraf"
import os, sys, math
import pyfits as pf
import zscale
import time
import fitsutils

ref_stars_file = "/Users/nadiablago/Documents/Projects/M101/cats/ref_stars_ps1.csv"
ref_stars_file_sdss = "/Users/nadiablago/Documents/Projects/M101/cats/ref_stars_sdss.csv"
ref_stars_file_2mass = "/Users/nadiablago/Documents/Projects/M101/cats/ref_stars_2mass.csv"
ref_stars_file_johnson = "/Users/nadiablago/Documents/Projects/M101/cats/ref_stars_johnson.csv"



def get_app_phot(coords, image, plot_only=False, store=True,wcsin="world", fwhm=np.nan):
    '''
    coords: files: 
    wcsin: can be "world", "logic"
    '''
    # Load packages; splot is in the onedspec package, which is in noao. 
    # The special keyword _doprint=0 turns off displaying the tasks 
    # when loading a package. 
    
    if (not plot_only):
        iraf.noao(_doprint=0)
        iraf.digiphot(_doprint=0)
        iraf.apphot(_doprint=0)
        iraf.unlearn("apphot")
    
    out_name = image +  ".seq.mag"
    clean_name = image + ".app.mag"
    
    # Read values from .ec file
    ecfile= image+".ec"
    filter_value=''.join(ecfile).split('.',1)[0]
    
    if (not np.isnan(fwhm)):
        fwhm_value = fwhm
    if (fitsutils.has_par(image, 'FWHM')):
        fwhm_value = fitsutils.get_par(image, 'FWHM')
    airmass_value = fitsutils.get_par(image, 'FWHM')
    exptime = fitsutils.get_par(image, 'EXPTIME')
    gain = fitsutils.get_par(image, 'GAIN')

    try:      
        with open(''.join(ecfile),'r') as f:
            for line in f:
                if "airmass" in line:
                    airmass_value = line.split('=',1)[1]
                else:
                    airmass_value = 1
                if "FWHM" in line:
                    print line
                    fwhm_value =  line.split('FWHM=',1)[1]
                    fwhm_value = fwhm_value.rsplit("aperture")[0]
    except:
        pass
    
    print "FWHM", fwhm_value
    aperture_rad = math.ceil(float(fwhm_value)*3)      # Set aperture radius to three times the PSF radius
    sky_rad= math.ceil(float(fwhm_value)*4)
    
    print aperture_rad, sky_rad

    if (not plot_only):

        if os.path.isfile(out_name): os.remove(out_name)
        if os.path.isfile(clean_name): os.remove(clean_name)

        # Check if files in list, otherwise exit
        if not ecfile:
           print "No .ec files in directory, exiting"
           sys.exit()
        
        
   
   
        iraf.noao.digiphot.apphot.qphot(image = image,\
        cbox = 25. ,\
        annulus = sky_rad ,\
        dannulus = 10. ,\
        aperture = str(aperture_rad),\
        coords = coords ,\
        output = out_name ,\
        plotfile = "" ,\
        zmag = 0. ,\
        exposure = "exptime" ,\
        airmass = "airmass" ,\
        filter = "filters" ,\
        obstime = "DATE" ,\
        epadu = gain ,\
        interactive = "no" ,\
        radplots = "yes" ,\
        verbose = "no" ,\
        graphics = "stdgraph" ,\
        display = "stdimage" ,\
        icommands = "" ,\
        wcsin = wcsin,
        wcsout = "logical",
        gcommands = "") 

        '''iraf.noao.digiphot.apphot.phot(image = image,\
            skyfile = "",\
            coords  = coords,\
            output  = out_name,\
           plotfil = "",\
           datapar = "",\
           centerp = "",\
           fitskyp = "",\
           photpar = "",\
           interac = "no",\
           radplot = "no",\
           icomman = "",\
           gcomman = "",\
           wcsin = wcsin,
           wcsout = "logical",
           fwhmpsf = float(fwhm_value),\
           datamin = 0   ,\
           datamax = 63500,\
           ccdread =  "INDEF",\
           gain    =  "INDEF",\
           readnoi =  0,\
           epadu   =  2.0,\
           exposur = "EXPTIME",\
           airmass = "AIRMASS",\
           filter  = "FILTER",\
           obstime = "DATE-OBS",\
           calgori = "centroid",\
           salgori = "mode",\
           cbox    = 25.,\
           annulus = 30,\
           dannulu = 10,\
           zmag = 0.,\
           aperture = str(aperture_rad)
          # apert = str(aperture_rad),\
           #scale  =                   1.,\
           #emissio=                  "yes",\
           #sigma  =                "INDEF"           
           )'''
        
         
        #iraf.noao.digiphot.apphot.phot(image=image, cbox=5., annulus=12.4, dannulus=10., salgori = "centroid", aperture=9.3,wcsin="world",wcsout="tv", interac = "no", coords=coords, output=out_name)
        iraf.txdump(out_name, "id,xcenter,ycenter,xshift,yshift,fwhm,msky,stdev,mag,merr", "yes", Stdout=clean_name)
        
    
    ma = np.genfromtxt(clean_name, comments="#", dtype=[("id","<f4"),  ("X","<f4"), ("Y","<f4"), ("Xshift","<f4"), ("Yshift","<f4"),("fwhm","<f4"), ("ph_mag","<f4"), ("stdev","<f4"), ("fit_mag","<f4"), ("fiterr","<f4")])
    if (ma.size > 1):    
        m = ma[~np.isnan(ma["fit_mag"])]
    else:
        print "Only one object found!"
        m = np.array([ma])
        
    hdulist = pf.open(image)
    prihdr = hdulist[0].header
    img = hdulist[0].data * 1.
    nx, ny = img.shape

    
    
    dimX = int(4)
    dimY = int(np.ceil(len(m)*1./4))
    outerrad = sky_rad+10
    cutrad = outerrad + 15
    
    plt.suptitle("FWHM="+str(fwhm_value))
    k = 0
    for i in np.arange(dimX):
        for j in np.arange(dimY):
            if ( k < len(m)):
                ax = plt.subplot2grid((dimX,dimY),(i, j))
                y1, y2, x1, x2 = m[k]["X"]-cutrad, m[k]["X"]+cutrad, m[k]["Y"]-cutrad, m[k]["Y"]+cutrad
                try:
                    zmin, zmax = zscale.zscale(img[x1:x2,y1:y2], nsamples=1000, contrast=0.25)
                except:
                    sh= img[x1:x2,y1:y2].shape
                    if sh[0]>0 and sh[1]>0:
                        zmin = np.nanmin(img[x1:x2,y1:y2])
                        zmax = np.nanmax(img[x1:x2,y1:y2])
                        continue
                    else:
                        continue
                ax.imshow(img[x1:x2,y1:y2], aspect="equal", extent=(-cutrad, cutrad, -cutrad, cutrad), origin="lower", cmap=matplotlib.cm.gray_r, interpolation="none", vmin=zmin, vmax=zmax)
                c1 = plt.Circle( (0, 0), edgecolor="r", facecolor="none", radius=5.)
                c2 = plt.Circle( (0, 0), edgecolor="orange", facecolor="none", radius=sky_rad)
                c3 = plt.Circle( (0, 0), edgecolor="yellow", facecolor="none", radius=sky_rad+10)
                plt.gca().add_artist(c1)
                plt.gca().add_artist(c2)
                plt.gca().add_artist(c3)
                ax.set_xticks([])
                ax.set_yticks([])
        
                plt.text(+5, +5, "%d"%m[k]["id"])
                plt.text(-cutrad, -cutrad, "%.2f$\pm$%.2f"%(m[k]["fit_mag"], m[k]["fiterr"]), color="b")
            k = k+1
    
    plt.savefig(image + "plot.png")
    plt.clf()

    

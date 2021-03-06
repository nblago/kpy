
import argparse
import pdb
import numpy as np
import pylab as pl
import pyfits as pf
import sys


import NPK.Fit 
import NPK.Bar as Bar
from astropy.table import Table 

from scipy.spatial import KDTree 
import NPK.Standards as Stds
import scipy.signal as SG


from numpy.polynomial.chebyshev import chebfit, chebval

import Extraction
reload(NPK.Fit)
reload(Extraction)


def extract_info(infiles):
    

    headers = []

    update_rate = len(infiles) / (Bar.setup() - 1)
    for ix, file in enumerate(infiles):
        if ix % update_rate == 0: Bar.update()
        FF = pf.open(file )
        FF[0].header['filename'] = file
        if 'JD' not in FF[0].header:
            #print "Skipping %s" % file
            continue
        headers.append(FF[0].header)
    
    Bar.done()
    
    return sorted(headers, key=lambda x: x['JD'])

def identify_observations(headers):
    '''Return a list of object name, observation number, and list of files.

    e.g. will return:

    {'STD-BD+25d4655': {1: ['...']}, {2: ['...']}, 
           'PTF14dvo': {1: ['...', '...']}}
    
    where STD-BD+25d4655 was observed at the beginning and end of night. SN
    14dov was observed once with A-B.'''
    JD = 0

    objcnt = {}
    objs = {}
    calibs = {}

    curr = ""
    for header in headers:
        if header['JD'] < JD:
            raise Exception("Headers not sorted by JD")
        JD = header['JD']

        fname = header['filename']
        obj = header['OBJECT']
        name = header['NAME']
        exptime = header['exptime']
        adcspeed = header['ADCSPEED']
        if "test" in obj: continue
        if "Calib" in obj or "bias" in obj:

            def appendToCalibs(Str):

                if Str in obj:
                    if "bias" in Str:
                        Str = "%s%1.1f" % (Str, adcspeed)
                        prefix = ""
                        suffix = ""
                    elif "Xe" in Str or "Hg" in Str or "Cd" in Str or "Ne" in Str or "dome" in Str:
                        prefix = "b_"
                        suffix = ""
                    else:
                        prefix = "crr_b_"
                        suffix = ""

                    calibs[Str] = calibs.get(Str, [])
                    calibs[Str].append(prefix + fname + suffix)

            appendToCalibs("bias")
            appendToCalibs("dome")
            appendToCalibs("Xe")
            appendToCalibs("Hg")
            appendToCalibs("Cd")
            appendToCalibs("Ne")
            appendToCalibs("twilight")

        if "Focus:" in obj: continue
        if "dark" in obj: continue
        if "STOW" in name: continue
        if obj.rstrip() == "": continue
        name= name.replace(" ", "_")
        name= name.replace(")", "_")
        name= name.replace("(", "_")
        name= name.replace("[", "_")
        name= name.replace("]", "_")
        name= name.replace("/", "_")
        name= name.replace(":", "_")

        
        # The 'A' position defines the start of an object set
        if '[A]' in obj or name not in objcnt:
            cnt = objcnt.get(name, 0) + 1
            vals = objs.get(name, {})
            objcnt[name] = cnt
            vals[cnt] = [fname]
            objs[name] = vals
        else:
            try: cnt = objcnt[name]
            except: 
                import pdb
                pdb.set_trace()
            objs[name][cnt].append(fname)

    print "-- Calibrations --"
    for k,v in calibs.iteritems():
        print "%15s : %2.0i" % (k, len(v))

    return objs, calibs


make_preamble = '''
PY = ~/spy
PYC = ~/kpy/SEDM
EXTSINGLE =  $(PY) $(PYC)r/Extractor.py 
ATM =  $(PY) $(PYC)r/AtmCorr.py 
EXTPAIR =  $(PY) $(PYC)r/Extractor.py 
FLEXCMD = $(PY) $(PYC)r/Flexure.py
IMCOMBINE = $(PY) $(PYC)r/Imcombine.py
PLOT = $(PY) $(PYC)r/Check.py

BSUB = $(PY) $(PYC)/Bias.py
BGDSUB =  $(PY) $(PYC)r/SubtractBackground.py
CRRSUB =  $(PY) $(PYC)r/CosmicX.py

SRCS = $(wildcard ifu*fits)
BIAS = $(addprefix b_,$(SRCS))
CRRS = $(addprefix crr_,$(BIAS))
BACK = $(addsuffix .gz,$(addprefix bs_,$(CRRS)))
FLEX = $(subst .fits,.npy,$(addprefix flex_,$(BACK)))

crr_b_% : b_%
	$(CRRSUB) --niter 4 --sepmed --gain 1.0 --readnoise 5.0 --objlim 1.8 \\
		--sigclip 8.0 --fsmode convolve --psfmodel gaussy --psffwhm=2 \\
		$< $@ mask$@

bs_crr_b_%.gz : crr_b_%
	$(BGDSUB) fine.npy $<

flex_bs_crr_b_%.npy : bs_crr_b_%.fits.gz
	$(FLEXCMD) cube.npy $< --outfile $@

%_SEDM.pdf : sp_%.npy
	$(PLOT) --spec $< --savefig

.PHONY: cleanstds newstds

bias: bias0.1.fits bias2.0.fits $(BIAS)
bgd: $(BGD) bias
crrs: $(CRRS) 
back: $(BACK)

$(BIAS): bias0.1.fits bias2.0.fits
	$(BSUB) $(subst b_,,$@)

$(CRRS): 
	$(CRRSUB) --niter 4 --sepmed --gain 1.0 --readnoise 5.0 --objlim 1.8 \\
		--sigclip 8.0 --fsmode convolve --psfmodel gaussy --psffwhm=2 \\
		$(subst crr_,,$@) $@ mask$@

$(BACK): 
	$(BGDSUB) fine.npy $(subst .gz,,$(subst bs_,,$@))
    

seg_dome.fits: dome.fits
	$(PY) $(PYC)r/SexLamps.py dome.fits

seg_Hg.fits: Hg.fits
	$(PY) $(PYC)r/SexSpectra.py Hg.fits

dome.fits_segments.npy: seg_dome.fits
	$(PY) $(PYC)r/FindSpectra.py seg_dome.fits dome.fits dome.fits_segments --order 1

rough.npy: dome.fits_segments.npy seg_Hg.fits
	$(PY) $(PYC)r/Wavelength.py rough --hgfits Hg.fits --hgcat cat_Hg.fits.txt --dome dome.fits_segments.npy --outname rough 

fine.npy: rough.npy Cd.fits Xe.fits
	$(PY) $(PYC)r/Wavelength.py fine --cdfits Cd.fits --xefits Xe.fits --hgfits Hg.fits --hgassoc assoc_Hg.npy --outname fine

cube.npy: fine.npy
	$(PY) $(PYC)r/Cube.py fine.npy --step make --outname cube.npy
	$(PLOT) --cube cube.npy --savefig
	$(PLOT) --cube cube.npy --lambdarms --savefig

bs_twilight.fits.gz: twilight.fits fine.npy
	$(BGDSUB) fine.npy twilight.fits

bs_dome.fits.gz: dome.fits fine.npy
	$(BGDSUB) fine.npy dome.fits

dome.npy:
	$(PY) $(PYC)r/Extractor.py cube.npy --A dome.fits --outname dome --flat

flat-dome-700to900.npy: cube.npy dome.npy
	$(PY) $(PYC)r/Flat.py dome.npy
    
wave: fine.npy
cube: cube.npy

flex: back $(FLEX)

$(FLEX): cube.npy
	$(eval OUTNAME = $(subst .gz,,$@))
	$(FLEXCMD) cube.npy $(subst flex_,,$(subst npy,fits,$@)) --outfile $(OUTNAME)

stds: flat-dome-700to900.npy std-correction.npy

cleanstds:
	rm -f std-correction.npy Standard_Correction.pdf

newstds: cleanstds stds

'''

def MF_imcombine(objname, files, dependencies=""):
    
    filelist = " ".join(["%s " % file for file in files])
    first = "%s.fits: %s %s\n" % (objname, filelist, dependencies)

    if len(filelist) > 7:
        reject = "sigclip"
    else:
        reject = "none"
    second = "\t$(IMCOMBINE) --outname %s.fits --reject %s --Nlo 3 --Nhi 3 --files %s\n" % (objname, reject, filelist)

    if "bias" not in objname and "dome" not in objname:
        second += "\n%s.npy : cube.npy %s.fits\n\t$(EXTSINGLE) cube.npy --A %s.fits --outname %s.npy --flat_correction flat-dome-700to900.npy --nosky\n" % (objname, objname, objname, objname)

    return  first+second+"\n"


def MF_single(objname, obsnum, file, standard=None):
    '''Create the MF entry for a observation with a single file. '''

    #print objname, obsnum, file

    tp = {'objname': objname, 'obsfile': "bs_crr_b_%s" % file}
    tp['num'] = '_obs%s' % obsnum
    tp['outname'] = "%(objname)s%(num)s.npy" % tp

    if standard is None: tp['STD'] = ''
    else: tp['STD'] = "--std %s" % (standard)
    tp['flexname'] = "flex_bs_crr_b_%s.npy" % (file.rstrip(".fits"))

    first = '''# %(outname)s
%(outname)s: cube.npy %(flexname)s %(obsfile)s.gz
\t$(EXTSINGLE) cube.npy --A %(obsfile)s.gz --outname %(outname)s %(STD)s --flat_correction flat-dome-700to900.npy --Aoffset %(flexname)s

cube_%(outname)s.fits: %(outname)s
\t$(PY) $(PYC)r/Cube.py %(outname)s --step extract --outname cube_%(outname)s.fits
''' % tp
    second = '''corr_%(outname)s: %(outname)s
\t$(ATM) CORR --A %(outname)s --std %(objname)s --outname corr_%(outname)s\n''' %  tp
    fn = "%(outname)s" % tp

    if standard is None: return first+"\n", fn
    else: return first+second+"\n", fn 

    

def MF_AB(objname, obsnum, A, B):
    '''Create the MF entry for an A-B observation'''

    #print objname, obsnum, A, B
    tp = {'objname': objname, 'A': "bs_crr_b_" + A, 'B': "bs_crr_b_" + B}
    if obsnum == 1: tp['num'] = ''
    else: tp['num'] = '_obs%i' % obsnum
    tp['outname'] = "%(objname)s%(num)s.npy" % tp
    # we only use the flexure from the A image
    tp['flexname'] = "flex_bs_crr_b_%s.npy" % A.rstrip('.fits')

    tp['bgdnameA'] = "bgd_%s.npy" % (A.rstrip('.fits'))
    tp['bgdnameB'] = "bgd_%s.npy" % (B.rstrip('.fits'))  

    return '''# %(outname)s\n%(outname)s: cube.npy %(A)s.gz %(B)s.gz %(flexname)s
\t$(EXTPAIR) cube.npy --A %(A)s.gz --B %(B)s.gz --outname %(outname)s --flat_correction flat-dome-700to900.npy --Aoffset %(flexname)s\n\n''' %  tp, "%(outname)s " % tp


def MF_ABCD(objname, obsnum, files): 
    '''Create the MF entry for an A-B observation'''

    A,B,C,D = files
    tp = {'objname': objname, 'A': A, 'B': B, 'C': C, 'D': D}
    if obsnum == 1: tp['num'] = ''
    else: tp['num'] = '_obs%i' % obsnum
    tp['outname'] = "%(objname)s%(num)s.npy" % tp
    # we only use the flexure from the A image
    tp['flexname'] = "flex_%s.npy" % A.rstrip('.fits')
    return '''%(outname)s: fine.npy %(A)s %(B)s %(C)s %(D)s %(flexname)s
\t$(EXTPAIR) fine.npy --A %(A)s --B %(B)s --C %(C)s --D %(D)s --Aoffset %(flexname)s --outname %(outname)s \n''' %  tp, "%(outname)s" % tp



def to_makefile(objs, calibs):
    
    MF = ""

    all = ""
    stds = ""
    stds_dep = ""
    sci = ""
    
    flexures = ""

    for calibname, files in calibs.iteritems():
        
        if "bias" not in calibname:
            pass
        MF += MF_imcombine(calibname, files)
        all += "%s.fits " % calibname
    
    flatfiles = []
    for objname, observations in objs.iteritems():

        objname = objname.replace(" ", "_")
        objname = objname.replace(")", "_")
        objname = objname.replace("(", "_")
        objname = objname.replace("[", "_")
        objname = objname.replace("]", "_")

        for obsnum, obsfiles in observations.iteritems():
            flatfiles.append(obsfiles)

            # Handle Standard Stars
            if objname.startswith("STD-"):
                pred = objname[4:].rstrip().lower().replace("+","").replace("-","_")
                if pred in Stds.Standards:
                    standard = pred

                    for ix, obsfile in enumerate(obsfiles):
                        m,a = MF_single(objname, "%i_%i" % (obsnum, ix), 
                            obsfile, 
                            standard=standard)
                        MF += m
                        # don't need these in all: dependants of target "stds"
                        # all += a + " "
                        stds_dep += a + " "

                else: standard = None
                continue

            # Handle science targets
            #print "****", objname, obsnum, obsfiles
            if len(obsfiles) == 2:
                m,a = MF_AB(objname, obsnum, obsfiles[0], obsfiles[1])

                MF += m
                all += a + " "
                
                if not objname.startswith("STD-"):
                    sci += a + " "
            else:
                for obsfilenum, obsfile in enumerate(obsfiles):
                    standard = None

                    m,a = MF_single(objname, "%i_%i" % (obsnum,obsfilenum), 
                        obsfile)

                    if standard is not None:
                        stds += "corr_%s " % (a)

                    MF += m
                    all += a + " "
                    
                    if not objname.startswith("STD-") and not objname.startswith("STOW"):
                        sci += a + " "
            '''
            elif len(obsfiles) == 2:
                m,a = MF_AB(objname, obsnum, obsfiles[0], obsfiles[1])
                MF += m
                all += a + " "
            elif len(obsfiles) == 4:
                m,a = MF_ABCD(objname, obsnum, obsfiles)
                MF += m
                all += a + " "
            '''

    stds += " "


    preamble = make_preamble

    f = open("Makefile", "w")
    clean = "\n\nclean:\n\trm %s %s" % (all, stds)
    science = "\n\nscience: %s\n" % sci
    corr = "std-correction.npy: %s \n\t$(ATM) CREATE --outname std-correction.npy --files sp_STD*npy \n" % stds_dep

    f.write(preamble + corr + "\nall: stds %s%s%s" % (all, clean, science) + "\n" +
        MF + "\n" + flexures)
    f.close()

def make_plan(headers):
    '''Convert headers to a makefile
    
    Assumed headers sorted by JD'''

            
    objs, calibs = identify_observations(headers)
    to_makefile(objs, calibs)

if __name__ == '__main__':

    files = sys.argv[1:]
    to_process = extract_info(files)

    objs = make_plan(to_process)



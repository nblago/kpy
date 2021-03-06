import numpy as np

def getDegRaString(ra):
    if (type(ra) == np.ndarray):
        out = []
        for ri in ra:
            out.append(getDegRaString(ri))
        return np.array(out)
        
    if np.isreal(ra):
        return ra
    elif (":" in ra):
        raparams = ra.split(":")
    elif (" " in ra.strip()):
        raparams = ra.strip().split(" ")
    
    raparams = [float(r) for r in raparams]
    
    return  getDegRa(*tuple(raparams))

def getDegDecString(dec):
    
    if (type(dec) == np.ndarray):
        out = []
        for deci in dec:
            out.append(getDegDecString(deci))
        return np.array(out)
        
    if np.isreal(dec):
        return dec
    elif (":" in dec):
        decparams = dec.split(":")
    elif (" " in dec.strip()):
        decparams = dec.strip().split(" ")
    
    decparams = [float(r) for r in decparams]
    
    return  getDegDec(*tuple(decparams))
 
def getDegRa(hh, mm, ss):
	return  15*(hh + mm/60. + ss/3600.)

def getDegDec(hh, mm, ss):
	return  (hh + mm/60. + ss/3600.)

def getRaFromDeg(deg):
	hh = int(deg/15)
	mm = int((deg/15. - hh)*60)
	ss = ((deg/15. - hh)*60 - mm )*60
	return hh,mm,ss

def getDecFromDeg(deg):
	hh = int(deg)
	mm = int((deg - hh)*60)
	ss = ((deg - hh)*60 - mm )*60
	return hh,mm,ss

def hour2deg(ra_hour, deg_hour):
    ra = getDegRaString(ra_hour)
    dec = getDegDecString(deg_hour)
    return ra, dec
    
def deg2hour(ra_deg, dec_deg):
    ra_hour = getRaFromDeg(ra_deg)
    dec_hour = getDecFromDeg(dec_deg)
    return "%.2d:%.2d:%.2f"%(ra_hour), "%.2d:%.2d:%.2f"%(dec_hour)
    
def get_distance(ra1, dec1, ra2, dec2):
    '''
    Returns the distance in degrees between the two points.
    
    '''
    ra1=getDegRaString(ra1)
    ra2=getDegRaString(ra2)
    dec1=getDegDecString(dec1)
    dec2=getDegDecString(dec2)
    
    d = np.sqrt( ((ra2-ra1)*np.cos(np.deg2rad(dec1)))**2 + (dec2-dec1)**2 )
    
    #d = np.rad2deg(np.arccos(np.sin(dec1)*np.sin(dec2) + np.cos(dec1)*np.cos(dec2)*np.cos(ra1-ra2)))
    return d

def get_offset(ra1, dec1, ra2, dec2):
    '''
    Returns offset from ra1, dec1 position to ra2, dec2.
    
    returns ( East Offset [arcsec], 	North Offset [arcsec] )

    '''

    ra1=getDegRaString(ra1)
    ra2=getDegRaString(ra2)
    dec1=getDegDecString(dec1)
    dec2=getDegDecString(dec2)

    return (ra2 - ra1) * np.cos(np.deg2rad(dec1))*3600, (dec2-dec1)*3600
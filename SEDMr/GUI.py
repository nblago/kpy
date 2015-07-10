import NPK.Atmosphere as Atm
import NPK.PlotHelp as PH
import datetime
import numpy as np
import os
import pyfits
import scipy.io
import matplotlib.pyplot as pl
from matplotlib.backend_bases import KeyEvent 
from matplotlib.backend_bases import PickEvent
from scipy.interpolate import interp1d
from matplotlib.widgets import Cursor

import SEDMr.Spectra as SS


class PositionPicker(object):

    spectra = None
    Xs = None
    Ys = None
    Vs = None
    pointsize = None
    picked = None

    def __init__(self, spectra=None, figure=None, pointsize=50, bgd_sub=False):
        ''' Create spectum picking gui.

        Args:
            spectra: SEDMr.Spectra object
            figure: Figure to draw to [default is None or open a new figure
                window '''

        self.spectra = spectra
        self.pointsize = pointsize

        self.Xs, self.Ys, self.Vs = spectra.to_xyv()

        if bgd_sub:
            self.Vs -= np.median(self.Vs)

        pl.ioff()
        self.figure = pl.figure(figure)

        self.figure.canvas.mpl_connect("button_press_event", self)
        self.draw_cube()

    def draw_cube(self):
        pl.scatter(self.Xs, self.Ys, c=self.Vs, s=self.pointsize, linewidth=0)
        pl.ylim(-20,20)
        pl.xlim(-20,20)
        pl.colorbar()

        c = Cursor(self.figure.gca(), useblit=True)
        pl.show()

    def __call__(self, event):
        '''Event call handler for Picker gui.'''
        
        if event.name == 'button_press_event':
            print event.xdata, event.ydata
            self.picked = (event.xdata, event.ydata)
            pl.close(self.figure)
            


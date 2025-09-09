
if "bpy" in locals():
    import importlib
    importlib.reload(colormodels)
    importlib.reload(tulips3dGeometry)

else:
    from . import colormodels
    from . import tulips3dGeometry

import bpy
import numpy as np
import sys
from time import time
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, LogNorm
from scipy.interpolate import interp1d

import mesaPlot as mp


# ######################################################
# MESA DATA 
# ######################################################
def prepare_perceived_color_data(settings, verbose_timing=False):
    color = teff2rgb([10 ** m.hist.log_Teff[start_ind]])[0]

    def teff2rgb(t_ary):
        """Convert effective temperature to rgb colors.
        
        Convert effective temperature to rgb colors using colorpy.
        
        Parameters
        ----------
        t_ary : array
            Temperature array in K.
        
        Returns
        -------
        rgb_list: array
            Array with rgb colors. 
        """
        rgb_list = []
        for t in t_ary:
            rgb_list.append(colormodels.irgb_string_from_xyz(blackbody.blackbody_color(t)))
        return rgb_list

def prepare_energy_data(settings, verbose_timing=False):
    '''Reads in Energy production data from a mesa file'''
    time_index_step = settings.time_index_step

    # We use mesaplot to read in the mesa data
    if verbose_timing: _ = time()
    m = mp.MESA() # Create MESA object
    m.loadHistory(f=settings.mesa_file_path)
    if verbose_timing: print("Timing load mesa file: ", time()-_)

    # We need these indices for the burning data
    qtop = "burn_qtop_"
    qtype = "burn_type_"

    # A check if data is avaliable
    try:
        m.hist.data[qtop + "1"]
    except ValueError:
        raise KeyError(
            "No field " + qtop + "* found, add mixing_regions 40 and burning_regions 40 to your history_columns.list")

    star_masses = sm = m.hist.star_mass
    time_indices = len(star_masses)

    if verbose_timing: _ = time()
    R_star = []
    T_index = []
    start_ind = 0
    while start_ind < time_indices:
        print(start_ind)
        num_burn_zones = int([xx.split('_')[2] for xx in m.hist.data.dtype.names if qtop in xx][-1])
        # Per time stamp we will have radii and values, which we list in these variables:
        list_r = [np.abs(m.hist.data[qtop + str(region)][start_ind] * sm[start_ind]) for region in range(1, num_burn_zones + 1)]
        list_value = [m.hist.data[qtype + str(region)][start_ind] for region in range(1, num_burn_zones + 1)]
        # We make one data array
        _d = np.array([list_r, list_value])
        # We need to remove duplicates at the end where value==-9999
        _mask = _d[1] != -9999
        # Our cleaned up arrays containing the radii and burning values
        r, v = _d[0][_mask], _d[1][_mask] # Now you have data you can interpolate f = interp1d(r, v, kind='cubic')
        # We save the times where we sample and the stellar radius at that time        
        T_index.append(start_ind)
        R_star.append(r[-1]) 
        # And we make vertex colors
        tulips3dGeometry.make_vertex_colors(r, v, settings, vertex_colors_name_base="energy_ver_col_"+str(start_ind))
        # And increment the time index
        start_ind += time_index_step

    if verbose_timing: print("Timing energy data: ", time()-_, start_ind/time_index_step, "steps")
    
    # We save the time stamps and the stellar radii in a stellarProperties (Blender propertygroup object)
    obj = bpy.data.objects[settings.ob_name]
    obj.stellarProperties.clear() # Clear it just in case
    for _ in range(len(T_index)): obj.stellarProperties.add() # Create entries
    obj.stellarProperties.foreach_set("R_star", R_star) # Set data to the entries
    obj.stellarProperties.foreach_set("T_index", T_index)
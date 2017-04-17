# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

import numpy as np


def compute_qpcr_concentration(cp_vals, m = -3.231, b = 12.059,
                               dil_factor = 25000):
    """Computes molar concentration of libraries from qPCR Cp values.

    Returns a 2D array of calculated concentrations, in nanomolar units

    Parameters
    ----------
    cp_vals : numpy array of float
        The Cp values parsed from the plate reader
    m : float
        The slope of the qPCR standard curve
    b : float
        The intercept of the qPCR standard curve
    dil_factor: float or int
        The dilution factor of the samples going into the qPCR

    Returns
    -------
    np.array of floats
        A 2D array of floats
    """
    qpcr_concentration = np.power(10,((cp_vals - b) / m)) * dil_factor / 1000

    return(qpcr_concentration)


def compute_shotgun_pooling_values_eqvol(sample_concs, total_vol = 60):
    """Computes molar concentration of libraries from qPCR Cp values.

    Returns a 2D array of calculated concentrations, in nanomolar units

    Parameters
    ----------
    sample_concs : list of float
        The concentrations calculated via qPCR (nM)
    total_vol : float
        The total volume to pool (µL)

    Returns
    -------
    np.array of floats
        A 2D array of floats
    """
    per_sample_vol = (float(total_vol) / float(sample_concs.size)) * 1000.0
    
    sample_vols = np.zeros([sample_concs.shape[0], sample_concs.shape[1]]) +
                  float(per_sample_vol)
    water_vols = np.zeros([sample_concs.shape[0], sample_concs.shape[1]])
    
    return(sample_vols, water_vols)


def compute_shotgun_pooling_values_qpcr(sample_concs, sample_fracs = None,
                                        min_conc = 10, floor_conc = 50,
                                        total_nmol = .01):
    """
    sample_concs: 2D array of float
        nM calculated by compute_qpcr_concentration
    sample_fracs: 2D of float
        fractional value for each sample (default 1/N)
    min_conc: float
        minimum nM concentration to be included in pool
    floor_conc: float
        minimum value for pooling for samples above min_conc
        corresponds to a maximum vol in pool
    total_nmol : float
        total number of nM to have in pool

    returns:
    sample_vols: list of float (L)
    """

    if sample_fracs is None:
        sample_fracs = np.ones(sample_concs.shape) / sample_concs.size
    
    # get samples above threshold
    sample_fracs_pass = sample_fracs.copy()
    sample_fracs_pass[sample_concs <= min_conc] = 0
    
    # renormalize to exclude lost samples
    sample_fracs_pass *= 1/sample_fracs_pass.sum()
    
    # floor concentration value
    sample_concs_floor = sample_concs.copy()
    sample_concs_floor[sample_concs < floor_conc] = floor_conc
    
    # calculate volumetric fractions including floor val
    sample_vols = (total_nmol * sample_fracs_pass) / sample_concs_floor
    
    # convert L to nL
    sample_vols *= 10**9
    
    return(sample_vols)


def estimate_pool_conc_vol(sample_vols, sample_concs):

    # scalar to adjust nL to L for molarity calculations
    nl_scalar = 10**-9
    
    # calc total pool pmols 
    total_pmols = np.multiply(sample_concs, sample_vols) * nl_scalar
    
    # calc total pool vol in nanoliters
    total_vol = sample_vols.sum()
    
    # pool pM is total pmols divided by total liters
    # (total vol in nL * 1 L / 10^9 nL)
    pool_conc = total_pmols.sum() / (total_vol * nl_scalar)
    
    return(pool_conc, total_vol)



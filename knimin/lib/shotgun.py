# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------
from __future__ import division

import numpy as np

from knimin import db


def compute_qpcr_concentration(cp_vals, m=-3.231, b=12.059, dil_factor=25000):
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
    qpcr_concentration = np.power(10, ((cp_vals - b) / m)) * dil_factor / 1000

    return(qpcr_concentration)


def compute_shotgun_pooling_values_eqvol(sample_concs, total_vol=60.0):
    """Computes molar concentration of libraries from qPCR Cp values.

    Returns a 2D array of calculated concentrations, in nanomolar units

    Parameters
    ----------
    sample_concs : numpy array of float
        The concentrations calculated via qPCR (nM)
    total_vol : float
        The total volume to pool (uL)

    Returns
    -------
    np.array of floats
        A 2D array of floats
    """
    per_sample_vol = (total_vol / sample_concs.size) * 1000.0

    sample_vols = np.zeros(sample_concs.shape) + per_sample_vol

    return(sample_vols)


def compute_shotgun_pooling_values_qpcr(sample_concs, sample_fracs=None,
                                        min_conc=10, floor_conc=50,
                                        total_nmol=.01):
    """Computes pooling volumes for samples based on qPCR estimates of
    nM concentrations (`sample_concs`).

    Reads in qPCR values in nM from output of `compute_qpcr_concentration`.
    Samples must be above a minimum concentration threshold (`min_conc`,
    default 10 nM) to be included. Samples above this threshold but below a
    given floor concentration (`floor_conc`, default 50 nM) will be pooled as
    if they were at the floor concentration, to avoid overdiluting the pool.

    Samples can be assigned a target molar fraction in the pool by passing a
    np.array (`sample_fracs`, same shape as `sample_concs`) with fractional
    values per sample. By default, will aim for equal molar pooling.

    Finally, total pooling size is determined by a target nanomolar quantity
    (`total_nmol`, default .01). For a perfect 384 sample library, in which you
    had all samples at a concentration of exactly 400 nM and wanted a total
    volume of 60 uL, this would be 0.024 nmol.

    Parameters
    ----------
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

    Returns
    -------
    sample_vols: np.array of floats
        the volumes in nL per each sample pooled
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
    """Estimates the actual molarity and volume of a pool.

    Parameters
    ----------
    sample_concs : numpy array of float
        The concentrations calculated via qPCR (nM)
    sample_vols : numpy array of float
        The calculated pooling volumes (nL)

    Returns
    -------
    pool_conc : float
        The estimated actual concentration of the pool, in nM
    total_vol : float
        The total volume of the pool, in nL
    """
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


def compute_shotgun_normalization_values(plate_layout, input_vol, input_dna):
    """Computes the normalization variables and stores them in the DB

    Parameters
    ----------
    plate_layout : list of list of dicts
        The shotgun plate layout in which each well contains this information
        {'sample_id': None, 'dna_concentration': None} in which the
        dna_concentration is represented in nanograms per microliter
    input_vol : float
        The maximum input volume in microliters
    input_dna : float
        The desired DNA for library prep in nanograms

    Returns
    -------
    2d numpy array, 2d numpy array, 2d numpy array
        The water volume and the sample volume per well, represented in
        nanoliters as well as the original dna concentrartion in ng/nL
    """
    input_dna = float(input_dna)
    input_vol = float(input_vol)
    rows = len(plate_layout)
    cols = len(plate_layout[0])
    dna_conc = np.zeros((rows, cols), dtype=np.float)
    for i in range(rows):
        for j in range(cols):
            dna_conc[i, j] = plate_layout[i][j]['dna_concentration']

    # Compute how much sample do we need
    # ng / (ng/uL) -> uL
    vol_sample = input_dna / dna_conc

    # If a sample didn't have enough concentration simple put the total of
    # the volume from the sample
    vol_sample[vol_sample > input_vol] = input_vol

    # Compute how much water do we need
    vol_water = input_vol - vol_sample

    # Transform both volumes to nanoliters
    vol_sample = vol_sample * 1000
    vol_water = vol_water * 1000

    return vol_sample, vol_water


def prepare_shotgun_libraries(plate_id, email, mosquito, kit, aliquot,
                              idx_tech):
    """
    Parameters
    ----------
    plate_id : int
        The shotgun plate ID
    idx_tech : str
        The index technology we want to use
    """
    minimum_sample_vol = 0.0001

    plate = db.read_normalized_shotgun_plate(plate_id)

    # Get the number of samples to get the indices
    samples_vol = plate['plate_normalization_sample']
    num_samples = (samples_vol > minimum_sample_vol).sum()

    indexes = db.generate_i5_i7_indexes(idx_tech, num_samples)
    rows, cols = samples_vol.shape
    barcode_layout = np.zeros((rows, cols), dtype=np.int)
    idx = 0
    for i in range(rows):
        for j in range(cols):
            if samples_vol[i, j] > minimum_sample_vol:
                barcode_layout[i, j] = indexes[idx]
                idx += 1

    db.prepare_shotgun_libraries(plate_id, email, mosquito, kit, aliquot,
                                 barcode_layout)

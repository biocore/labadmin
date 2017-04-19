# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from unittest import TestCase, main

import numpy as np
import numpy.testing as npt

from knimin.lib.shotgun import (compute_qpcr_concentration,
                                compute_shotgun_pooling_values_qpcr,
                                compute_shotgun_pooling_values_eqvol,
                                estimate_pool_conc_vol,
                                compute_shotgun_normalization_values)


class TestShotgun(TestCase):
    def setUp(self):
        self.cp_vals = np.array([[10.14, 7.89, 7.9, 15.48],
                                 [7.86, 8.07, 8.16, 9.64],
                                 [12.29, 7.64, 7.32, 13.74]])

        self.qpcr_conc = \
            np.array([[98.14626462, 487.8121413, 484.3480866, 2.183406934],
                      [498.3536649, 429.0839787, 402.4270321, 140.1601735],
                      [21.20533391, 582.9456031, 732.2655041, 7.545145988]])

    def test_compute_shotgun_normalization_values(self):
        input_vol = 3.5
        input_dna = 10
        plate_layout = []
        for i in range(4):
            row = []
            for j in range(4):
                row.append({'dna_concentration': 10,
                            'sample_id': "S%s.%s" % (i, j)})
            plate_layout.append(row)

        obs_sample, obs_water = compute_shotgun_normalization_values(
            plate_layout, input_vol, input_dna)

        exp_sample = np.zeros((4, 4), dtype=np.float)
        exp_water = np.zeros((4, 4), dtype=np.float)
        exp_sample.fill(1000)
        exp_water.fill(2500)

        npt.assert_almost_equal(obs_sample, exp_sample)
        npt.assert_almost_equal(obs_water, exp_water)

        # Make sure that we don't go above the limit
        plate_layout[1][1]['dna_concentration'] = 0.25
        obs_sample, obs_water = compute_shotgun_normalization_values(
            plate_layout, input_vol, input_dna)

        exp_sample[1][1] = 3500
        exp_water[1][1] = 0

        npt.assert_almost_equal(obs_sample, exp_sample)
        npt.assert_almost_equal(obs_water, exp_water)

    def test_compute_qpcr_concentration(self):
        obs = compute_qpcr_concentration(self.cp_vals)
        exp = self.qpcr_conc

        npt.assert_allclose(obs, exp)

    def test_compute_shotgun_pooling_values_eqvol(self):
        obs_sample_vols = \
            compute_shotgun_pooling_values_eqvol(self.qpcr_conc,
                                                 total_vol=60.0)

        exp_sample_vols = np.zeros([3, 4]) + 60.0/12*1000

        npt.assert_allclose(obs_sample_vols, exp_sample_vols)

    def test_compute_shotgun_pooling_values_eqvol_intvol(self):
        obs_sample_vols = \
            compute_shotgun_pooling_values_eqvol(self.qpcr_conc,
                                                 total_vol=60)

        exp_sample_vols = np.zeros([3, 4]) + 60.0/12*1000

        npt.assert_allclose(obs_sample_vols, exp_sample_vols)

    def test_compute_shotgun_pooling_values_qpcr(self):
        sample_concs = np.array([[1, 12, 400],
                                 [200, 40, 1]])

        exp_vols = np.array([[0, 50000, 6250],
                             [12500, 50000, 0]])

        obs_vols = compute_shotgun_pooling_values_qpcr(sample_concs)

        npt.assert_allclose(exp_vols, obs_vols)

    def test_estimate_pool_conc_vol(self):
        obs_sample_vols = compute_shotgun_pooling_values_eqvol(
                                        self.qpcr_conc, total_vol=60.0)

        obs_pool_conc, obs_pool_vol = estimate_pool_conc_vol(
                                        obs_sample_vols, self.qpcr_conc)

        exp_pool_conc = 323.873027979
        exp_pool_vol = 60000.0

        npt.assert_almost_equal(obs_pool_conc, exp_pool_conc)
        npt.assert_almost_equal(obs_pool_vol, exp_pool_vol)


if __name__ == '__main__':
    main()

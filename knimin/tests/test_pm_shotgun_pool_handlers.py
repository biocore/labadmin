# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------
import os

from unittest import main
from functools import partial
from random import choice
from tempfile import mkstemp

import numpy as np
import numpy.testing as npt

from knimin.tests.tornado_test_base import TestHandlerBase
from knimin import db


class TestPMShotgunPool(TestHandlerBase):
    def setUp(self):
        self.files_to_delete = []

        return super(TestPMShotgunPool, self).setUp()

    def tearDown(self):
        for f_del in self.files_to_delete:
            try:
                os.remove(f_del)
            except OSError:
                pass
        return super(TestPMShotgunPool, self).tearDown()

    # _create_test_echo and _create_test_shotgun_plate were copied from
    # test_data_access.py
    def _create_test_echo(self):
        echo_id = db.get_or_create_property_option_id('echo',
                                                      'a valid echo name')
        f = partial(db.delete_property_option, 'echo', echo_id)
        self._clean_up_funcs.append(f)

    def _create_test_shotgun_plate(self):
        # study creation
        db.create_study(9999, title='LabAdmin test project',
                        alias='LTP', jira_id='KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))

        # plates creation
        dna_plates = []
        exp_robot = db.get_property_options("extraction_robot")[0]
        exp_kit = db.get_property_options("extraction_kit_lot")[0]
        exp_tool = db.get_property_options("extraction_tool")[0]
        for i in range(4):
            pid = db.create_sample_plate('Test %s' % i, 2, 'test', [9999])
            self._clean_up_funcs.insert(
                0, partial(db.delete_sample_plate, pid))

            dp_pid = db.extract_sample_plates(
                [pid], 'test', exp_robot['name'], exp_kit['name'],
                exp_tool['name'])[0]
            self._clean_up_funcs.insert(
                0, partial(db.delete_dna_plate, dp_pid))
            dna_plates.append((dp_pid, i))

        email = 'test'
        name = "full plate"
        robot = 'HOWE_KF1'
        plate_type = 2L
        volume = 0.22
        cid = db.condense_dna_plates(dna_plates, name, email,
                                     robot, plate_type, volume)
        self._clean_up_funcs.insert(0, partial(db.delete_shotgun_plate, cid))
        return cid

    def _create_data(self):
        self._create_test_echo()
        cid = self._create_test_shotgun_plate()
        email = 'test'
        nid = db.normalize_shotgun_plate(cid, email, 'a valid echo name',
                                         np.arange(384).reshape(16, 24),
                                         np.arange(384).reshape(16, 24) * 10)

        db.read_normalized_shotgun_plate(nid)

        # tests for prepare_shotgun_libraries
        # the mosquito values are set 1: Mosquito1
        mosquito = 'Mosquito1'
        shotgun_library_prep_kit = 'new library_prep_kit'
        # as we need to insert a new index aliquot for testing, let's also
        # test the retrival
        shotgun_index_aliquot_id = db.add_shotgun_index_aliquot(
            'new index_aliquot_id', 'This is our newest index aliquot', 100)
        self._clean_up_funcs.append(
            partial(db.delete_shotgun_index_aliquot, shotgun_index_aliquot_id))
        db.read_shotgun_index_aliquot()

        _ids = range(1, 10)
        barcode_layout = [[choice(_ids) for c in range(24)] for r in range(16)]
        db.prepare_shotgun_libraries(
            nid, email, mosquito, shotgun_library_prep_kit,
            shotgun_index_aliquot_id, barcode_layout)

        qpcr = db.get_property_options("qpcr")[0]['name']
        qpcr_ladder = ''
        qpcr_cp_values = np.zeros((16, 24))
        qpcr_lib_concentration_values = np.zeros((16, 24))
        db.qpcr_shotgun(nid, email, qpcr, qpcr_ladder, qpcr_cp_values,
                        qpcr_lib_concentration_values)
        return nid

    def test_get_not_authed(self):
        response = self.get('/pm_shotgun_pool/?plate_id=1')
        self.assertEqual(response.code, 200)

    def test_get(self):
        nid = self._create_data()
        self.mock_login_admin()
        response = self.get("/pm_shotgun_pool/?plate_id=%s" % nid)
        self.assertEqual(response.code, 200)
        self.assertIn('<h3>Shotgun Pooling', response.body)

    def test_post_not_authed(self):
        # don't exactly know what data to test with
        data = {'qpcr-readout-fp': 'file contents'}
        args = ['minimum-concentration=1', 'floor-concentration=1',
                'total-quantity=10', 'plate-id=1', 'plate-name=Some%20Name',
                'qpcr-machine=bob']
        response = self.post('/pm_shotgun_pool/?%s' % '&'.join(args),
                             data=data)
        self.assertEqual(response.code, 403)

    def test_post(self):
        nid = self._create_data()
        self.mock_login_admin()

        fd, fp = mkstemp(suffix=".txt")
        os.close(fd)
        with open(fp, 'w') as f:
            f.write(QPCR_OBJECT)
        self.files_to_delete.append(fp)

        # don't exactly know what data to use here
        files = {'qpcr-readout-fp': fp}
        args = ['minimum-concentration=1', 'floor-concentration=1',
                'total-quantity=10', 'plate-id=%s' % nid,
                'plate-name=Some%20Name', 'qpcr-machine=bob']
        response = self.multipart_post('/pm_shotgun_pool/?%s' % '&'.join(args),
                                       data={}, files=files)

        self.assertEqual(response.code, 200)

        exp_cps = np.zeros((16, 24)) + np.nan
        exp_cps[0, :] = [10.73, 7.3, 6.77, 6.66, 7.44, 12.1, 6.63, 6.53, 9.32,
                         6.34, 6.05, 7.77, 11.47, 15.52, 12.6, 11.18, 21.37,
                         15.07, 11.45, 18.32, 12.68, 11.52, 11.34, 24.32]
        exp_cps[1, :] = [6.61, 6.27, 12.11, 7.15, 6.21, 7.31, 6.87, 5.98, 6.43,
                         6.59, 6.5, 8.07, 7.23, 7.82, 10.09, 15.68, np.nan,
                         np.nan, 14.78, 11.54, np.nan, np.nan, np.nan, np.nan]
        exp_cps[15, 19] = 11.54
        exp_conc = np.isnan(exp_cps)

        obs = db.read_normalized_shotgun_plate(nid)
        obs_cps = obs['plate_qpcr_cps']
        obs_conc = np.isnan(obs['plate_qpcr_concentrations'])
        npt.assert_equal(obs_cps, exp_cps)
        npt.assert_equal(obs_conc, exp_conc)

        self.assertEqual(obs['qpcr'], 'bob')


QPCR_OBJECT = """Experiment: Knight_kapa_qpcr  Selected Filter: \
SYBR Green I / HRM Dye (465-510),,,,,,,
Include,Color,Pos,Name,Cp,Concentration,Standard,Status
True,255,A1,Sample 1,10.73,,0,
True,255,A2,Sample 2,7.3,,0,
True,255,A3,Sample 3,6.77,,0,
True,255,A4,Sample 4,6.66,,0,
True,255,A5,Sample 5,7.44,,0,
True,255,A6,Sample 6,12.1,,0,
True,255,A7,Sample 7,6.63,,0,
True,255,A8,Sample 8,6.53,,0,
True,255,A9,Sample 9,9.32,,0,
True,255,A10,Sample 10,6.34,,0,
True,255,A11,Sample 11,6.05,,0,
True,255,A12,Sample 12,7.77,,0,
True,255,A13,Sample 13,11.47,,0,
True,255,A14,Sample 14,15.52,,0,
True,255,A15,Sample 15,12.6,,0,
True,255,A16,Sample 16,11.18,,0,
True,255,A17,Sample 17,21.37,,0,
True,255,A18,Sample 18,15.07,,0,
True,255,A19,Sample 19,11.45,,0,
True,255,A20,Sample 20,18.32,,0,
True,255,A21,Sample 21,12.68,,0,
True,255,A22,Sample 22,11.52,,0,
True,255,A23,Sample 23,11.34,,0,
True,255,A24,Sample 24,24.32,,0,
True,255,B1,Sample 25,6.61,,0,
True,255,B2,Sample 26,6.27,,0,
True,255,B3,Sample 27,12.11,,0,
True,255,B4,Sample 28,7.15,,0,
True,255,B5,Sample 29,6.21,,0,
True,255,B6,Sample 30,7.31,,0,
True,255,B7,Sample 31,6.87,,0,
True,255,B8,Sample 32,5.98,,0,
True,255,B9,Sample 33,6.43,,0,
True,255,B10,Sample 34,6.59,,0,
True,255,B11,Sample 35,6.5,,0,
True,255,B12,Sample 36,8.07,,0,
True,255,B13,Sample 37,7.23,,0,
True,255,B14,Sample 38,7.82,,0,
True,255,B15,Sample 39,10.09,,0,
True,255,B16,Sample 40,15.68,,0,
True,65280,B17,Sample 41,,,0,
True,65280,B18,Sample 42,,,0,
True,255,B19,Sample 43,14.78,,0,
True,255,B20,Sample 44,11.54,,0,
True,255,P20,Sample 45,11.54,,0,
"""


if __name__ == '__main__':
    main()

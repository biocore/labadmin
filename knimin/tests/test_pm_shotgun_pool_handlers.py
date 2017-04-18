# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------
from unittest import main

import numpy as np

from knimin.tests.tornado_test_base import TestHandlerBase
from knimin import db


class TestPMShotgunPool(TestHandlerBase):
    def setUp(self):
        self._clean_up_funcs = []

    def tearDown(self):
        for f in self._clean_up_funcs:
            try:
                f()
            except Exception as e:
                print("Database clean-up failed. Downstream tests might be "
                      "affected by this! Reason: %s" % format_exc(e))

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

        after = datetime.datetime.now()
        exp_sample = np.arange(384).reshape(16, 24)
        exp_water = np.arange(384).reshape(16, 24) * 10
        exp_qpcr_con = np.zeros((16, 24))
        exp_qpcr_cp = np.zeros((16, 24))
        exp_qpcr_con = None
        exp_qpcr_cp = None
        shotgun_i5_index = None
        shotgun_i7_index = None

        exp_rnsp = {'created_on': datetime.date.today(),
                    'email': email,
                    'echo': 'a valid echo name',
                    'lp_date': None,
                    'lp_email': None,
                    'mosquito': None,
                    'shotgun_plate_id': cid,
                    'shotgun_normalized_plate_id': nid,
                    'shotgun_library_prep_kit': None,
                    'shotgun_adapter_aliquot': None,
                    'qpcr_date': None,
                    'qpcr_email': None,
                    'qpcr_std_ladder': None,
                    'qpcr': None,
                    'shotgun_i5_index': shotgun_i5_index,
                    'shotgun_i7_index': shotgun_i7_index,
                    'discarded': False,
                    'plate_normalization_water': exp_water,
                    'plate_normalization_sample': exp_sample,
                    'plate_qpcr_concentrations': exp_qpcr_con,
                    'plate_qpcr_cps': exp_qpcr_cp}

        obs = db.read_normalized_shotgun_plate(nid)

        # tests for prepare_shotgun_libraries
        # the mosquito values are set 1: Mosquito1
        mosquito = 'Mosquito1'
        mosquito_id = 1
        shotgun_library_prep_kit = 'new library_prep_kit'
        # as we need to insert a new index aliquot for testing, let's also
        # test the retrival
        shotgun_index_aliquot_id = db.add_shotgun_index_aliquot(
            'new index_aliquot_id', 'This is our newest index aliquot', 100)
        self._clean_up_funcs.append(
            partial(db.delete_shotgun_index_aliquot, shotgun_index_aliquot_id))
        obs = db.read_shotgun_index_aliquot()
        exp = [{'notes': 'This is our newest index aliquot',
                'shotgun_index_aliquot_id': shotgun_index_aliquot_id,
                'name': 'new index_aliquot_id',
                'limit_freeze_thaw_cycles': 100L}]

        _ids = ['iTru5_24_G', 'iTru7_101_01', 'iTru7_101_02', 'NEXTflex78']
        i5_layout = [[choice(_ids) for c in range(24)] for r in range(16)]
        i7_layout = [[choice(_ids) for c in range(24)] for r in range(16)]
        db.prepare_shotgun_libraries(
            nid, email, mosquito, shotgun_library_prep_kit,
            shotgun_index_aliquot_id, i5_layout, i7_layout)

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
        response = self.post('/pm_shotgun_pool/' % '&'.join(args), data=data)
        self.assertEqual(response.code, 403)

    def test_post(self):
        nid = self._create_data()
        self.mock_login_admin()

        # don't exactly know what data to test with
        data = {'qpcr-readout-fp': 'file contents'}
        args = ['minimum-concentration=1', 'floor-concentration=1',
                'total-quantity=10', 'plate-id=1', 'plate-name=Some%20Name',
                'qpcr-machine=bob']
        response = self.post('/pm_shotgun_pool/' % '&'.join(args), data=data)
        self.assertEqual(response.code, 200)

        qpcr = db.get_property_options("qpcr")[0]['name']
        qpcr_ladder = ''
        qpcr_cp_values = np.zeros((16, 24))
        qpcr_lib_concentration_values = np.zeros((16, 24))
        # db.qpcr_shotgun(nid, email, qpcr, qpcr_ladder, qpcr_cp_values,
        #                 qpcr_lib_concentration_values)
        obs = db.read_normalized_shotgun_plate(nid)
        exp_rnsp['qpcr'] = qpcr
        exp_rnsp['qpcr_std_ladder'] = qpcr_ladder
        exp_rnsp['plate_qpcr_cps'] = qpcr_cp_values
        exp_rnsp['plate_qpcr_concentrations'] = qpcr_lib_concentration_values
        self._basic_test_steps_for_normalized_shotgun_plate(
            before, after, obs, exp_rnsp)

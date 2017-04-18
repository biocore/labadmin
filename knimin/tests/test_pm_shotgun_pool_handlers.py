# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------
from unittest import main
from functools import partial
from random import choice

import numpy as np

from knimin.tests.tornado_test_base import TestHandlerBase
from knimin import db


class TestPMShotgunPool(TestHandlerBase):

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

        _ids = ['iTru5_24_G', 'iTru7_101_01', 'iTru7_101_02', 'NEXTflex78']
        i5_layout = [[choice(_ids) for c in range(24)] for r in range(16)]
        i7_layout = [[choice(_ids) for c in range(24)] for r in range(16)]
        db.prepare_shotgun_libraries(
            nid, email, mosquito, shotgun_library_prep_kit,
            shotgun_index_aliquot_id, i5_layout, i7_layout)

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
        print response
        self.assertEqual(response.code, 403)

    def test_post(self):
        nid = self._create_data()
        self.mock_login_admin()

        # don't exactly know what data to use here
        data = {'qpcr-readout-fp': 'file contents'}
        args = ['minimum-concentration=1', 'floor-concentration=1',
                'total-quantity=10', 'plate-id=%s' % nid,
                'plate-name=Some%20Name', 'qpcr-machine=bob']
        response = self.post('/pm_shotgun_pool/?%s' % '&'.join(args),
                             data=data)

        self.assertEqual(response.code, 200)

        obs = db.read_normalized_shotgun_plate(nid)
        exp = {}
        self.assertEqual(obs, exp)

        # haven't tested this method properly so irregardless, this test should
        # fail
        self.fail()


if __name__ == '__main__':
    main()

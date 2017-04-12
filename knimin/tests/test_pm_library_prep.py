# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------
from unittest import main
from functools import partial
import re

from tornado.escape import json_encode

from knimin.tests.tornado_test_base import TestHandlerBase
from knimin import db


class TestPMTargetGeneLibraryPrepHandler(TestHandlerBase):
    def test_get_not_authed(self):
        response = self.get('/pm_library_prep/target_gene/')
        self.assertEqual(response.code, 200)
        self.assertTrue(response.effective_url.endswith(
            '?next=%2Fpm_library_prep%2Ftarget_gene%2F'))

    def test_get(self):
        self.mock_login_admin()
        response = self.get('/pm_library_prep/target_gene/')
        self.assertEqual(response.code, 200)
        self.assertIn(
            '<h3>Prepare a new Target Gene library</h3>', response.body)
        self.assertIn(
            "<option value='1'>ROBE</option>",
            response.body)

    def test_post_not_authed(self):
        data = {'plates': json_encode([{'dna_plate_id': 1,
                                        'barcode_plate_id': 1}]),
                'robot': 'ROBE', 'tm300': '208484Z', 'tm50': '108364Z',
                'master_mix': '14459', 'water': 'RNBD9959'}
        response = self.post('/pm_library_prep/target_gene/', data=data)
        self.assertEqual(response.code, 403)

    def test_post(self):
        # Create a study
        db.create_study(9999, title='LabAdmin test project', alias='LTP',
                        jira_id='KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))

        # Create some sample plates
        pt = db.get_plate_types()[0]
        plate_id = db.create_sample_plate('Test plate', pt['id'], 'test',
                                          [9999])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id))
        plate_id_2 = db.create_sample_plate('Test plate 2', pt['id'], 'test',
                                            [9999])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id_2))

        # Create DNA plates
        dna_plate_ids = db.extract_sample_plates(
            [plate_id, plate_id_2], 'test', 'HOWE_KF1', 'PM16B11', '108379Z')
        for p_id in dna_plate_ids:
            self._clean_up_funcs.insert(
                0, partial(db.delete_dna_plate, p_id))

        # Create the target gene plates
        plate_links = [
            {'dna_plate_id': dna_plate_ids[0], 'primer_plate_id': 1},
            {'dna_plate_id': dna_plate_ids[1], 'primer_plate_id': 2}]

        self.mock_login_admin()
        data = {'plates': json_encode(plate_links),
                'robot': 'ROBE', 'tm300': '208484Z', 'tm50': '108364Z',
                'master_mix': '14459', 'water': 'RNBD9959'}
        response = self.post('/pm_library_prep/target_gene/', data=data)

        plate_ids = []
        for match in re.findall("plate=[0-9]*", response.effective_url):
            plate_id = match.split('=')[1]
            self._clean_up_funcs.insert(
                0, partial(db.delete_targeted_plate, plate_id))
            plate_ids.append(plate_id)

        self.assertEqual(response.code, 200)
        self.assertEqual(len(plate_ids), 2)

        for plate_id in plate_ids:
            obs = db.read_targeted_plate(plate_id)
            self.assertIsNotNone(obs)


class TestPMMetagenomicsLibraryPrepHandler(TestHandlerBase):
    def test_get_not_authed(self):
        pass

    def test_get(self):
        pass


if __name__ == '__main__':
    main()

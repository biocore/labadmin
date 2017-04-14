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

from knimin.tests.tornado_test_base import TestHandlerBase
from knimin import db


class TestPMCondensePlatesHandler(TestHandlerBase):
    def test_get_not_authed(self):
        response = self.get('/pm_condense/')
        self.assertEqual(response.code, 200)
        self.assertTrue(response.effective_url.endswith(
            '?next=%2Fpm_condense%2F'))

    def test_get(self):
        self.mock_login_admin()
        response = self.get('/pm_condense/')
        self.assertEqual(response.code, 200)
        self.assertIn(
            '<h3>Condense DNA plates</h3>', response.body)
        self.assertIn(
            "<option value='ROBE'>ROBE</option>",
            response.body)

    def test_post_not_authed(self):
        data = {'plate-1': 1, 'plate-2': 2, 'plate-3': 3, 'plate-4': 4,
                'name': 'Test plate', 'robot': 'ROBE', 'volume': 1}
        response = self.post('/pm_condense/', data=data)
        self.assertEqual(response.code, 403)

    def test_post(self):
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
            dna_plates.append(dp_pid)

        data = {'plate-1': dna_plates[0], 'plate-2': dna_plates[1],
                'plate-3': dna_plates[2], 'plate-4': dna_plates[3],
                'name': 'Test plate', 'robot': 'ROBE', 'volume': 0.22}

        self.mock_login_admin()
        response = self.post('/pm_condense/', data=data)

        plate_ids = []
        for match in re.findall("plate=[0-9]*", response.effective_url):
            plate_id = match.split('=')[1]
            self._clean_up_funcs.insert(
                0, partial(db.delete_shotgun_plate, plate_id))
            plate_ids.append(plate_id)

        self.assertEqual(response.code, 200)
        self.assertEqual(len(plate_ids), 1)

        for plate_id in plate_ids:
            obs = db.read_shotgun_plate(plate_id)
            self.assertIsNotNone(obs)


if __name__ == '__main__':
    main()

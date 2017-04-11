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


class TestPMSequenceHandler(TestHandlerBase):
    def _create_data(self):
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

        # Plate some samples
        # Add samples to the study
        samples = ['9999.Sample_1', '9999.Sample_2', '9999.Sample_3',
                   '9999.Sample_3']
        db.set_study_samples(9999, samples)

        # Create the layout
        layout = []
        row = []
        for i in range(pt['rows']):
            for j in range(pt['cols']):
                row.append({'sample_id': None, 'name': None, 'notes': None})
            layout.append(row)
            row = []
        layout[0][0]['sample_id'] = samples[0]
        layout[0][1]['sample_id'] = samples[1]
        layout[0][2]['sample_id'] = samples[2]
        db.write_sample_plate_layout(plate_id, layout)
        layout[0][3]['sample_id'] = samples[3]
        db.write_sample_plate_layout(plate_id_2, layout)

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
        targeted_plate_ids = db.prepare_targeted_libraries(
            plate_links, 'test', 'ROBE', '208484Z', '108364Z', '14459',
            'RNBD9959')

        for p_id in targeted_plate_ids:
            self._clean_up_funcs.insert(
                0, partial(db.delete_targeted_plate, p_id))

        # Pool samples
        pools = [
            {'targeted_plate_id': targeted_plate_ids[0], 'volume': 240,
             'percentage': 50},
            {'targeted_plate_id': targeted_plate_ids[1], 'volume': 240,
             'percentage': 50}]
        pool_id = db.pool_plates(pools, 'LabAdmin test pool', 5)
        self._clean_up_funcs.insert(0, partial(db.delete_pool, pool_id))
        return pool_id

    def test_get_not_authed(self):
        response = self.get('/pm_sequence/?pool_id=1')
        self.assertEqual(response.code, 200)
        self.assertTrue(response.effective_url.endswith(
            '?next=%2Fpm_sequence%2F%3Fpool_id%3D1'))

    def test_get(self):
        pool_id = self._create_data()
        self.mock_login_admin()
        response = self.get("/pm_sequence/?pool_id=%s" % pool_id)
        self.assertEqual(response.code, 200)
        self.assertIn(
            '<h3>Prepare sequencing run for sample pool: LabAdmin test pool '
            '(ID: %s)</h3>' % pool_id, response.body)

    def test_post_not_authed(self):
        data = {'pool_id': 1, 'sequencer': 1,
                'reagent_kit_type': 'MiSeq v3 150 cycle',
                'reagent_kit_lot': 'MS1234'}
        response = self.post('/pm_sequence/', data=data)
        self.assertEqual(response.code, 403)

    def test_post(self):
        pool_id = self._create_data()
        data = {'pool_id': pool_id, 'sequencer': 1,
                'reagent_kit_type': 'MiSeq v3 150 cycle',
                'reagent_kit_lot': 'MS1234'}
        self.mock_login_admin()
        response = self.post('/pm_sequence/', data=data)

        run_ids = []
        for match in re.findall("ID [0-9]*", response.body):
            run_id = match.rsplit(' ', 1)[1]
            self._clean_up_funcs.insert(
                0, partial(db.delete_sequencing_run, run_id))
            run_ids.append(run_id)

        self.assertEqual(response.code, 200)
        self.assertEqual(len(run_ids), 1)

        self.assertIsNotNone(db.read_sequencing_run(run_ids[0]))


if __name__ == '__main__':
    main()

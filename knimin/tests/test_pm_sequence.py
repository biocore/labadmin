# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------
from unittest import main
from functools import partial
from tempfile import mkdtemp
from os.path import join
from tornado.escape import json_encode
import re

from knimin.tests.tornado_test_base import TestHandlerBase
from knimin import db, jira_handler, qiita_client
from knimin.lib.qiita_jira_util import (
    _create_kl_jira_project, sync_qiita_study_samples,
    create_sequencing_run)


class TestPMSequenceHandler(TestHandlerBase):
    def _create_data(self):
        # Create a study
        study_id = 1
        # Creating the Qiita test study in Jira and the DB
        _create_kl_jira_project('admin', 'Task management', study_id,
                                'LabAdmin test project')
        self._clean_up_funcs.append(
            partial(jira_handler.delete_project, 'TM%s' % study_id))

        db.create_study(
            study_id, 'Identification of the Microbiomes for Cannabis Soils',
            'alias', 'TM%s' % study_id)
        self._clean_up_funcs.append(partial(db.delete_study, study_id))

        # Create some plates
        pt = db.get_plate_types()[0]
        plate_id = db.create_sample_plate('Test plate', pt['id'], 'test',
                                          [study_id])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id))
        plate_id_2 = db.create_sample_plate('Test plate 2', pt['id'], 'test',
                                            [study_id])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id_2))

        # Plate some samples
        # Add samples to the study
        sync_qiita_study_samples(study_id)
        samples = db.get_study_samples(study_id)

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
        data = {'pool_id': pool_id,
                'reagent_type': 'MiSeq v3 150 cycle',
                'reagent_lot': 'MS1234',
                'platform': 'Illumina',
                'instrument_model': 'MiSeq',
                'assay': 'TrueSeq HT',
                'fwd_cycles': 151,
                'rev_cycles': 151}
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


class TestPMSequencingCompleteHandler(TestHandlerBase):
    def test_post_not_authed(self):
        data = {'run_id': 1, 'run_path': '/some/path/to/run/'}
        response = self.post('/pm_sequencing_complete/', data=data)
        self.assertEqual(response.code, 403)

    def test_post(self):
        # Create a study
        study_id = 1
        # Creating the Qiita test study in Jira and the DB
        _create_kl_jira_project('admin', 'Task management', study_id,
                                'LabAdmin test project')
        self._clean_up_funcs.append(
            partial(jira_handler.delete_project, 'TM%s' % study_id))

        db.create_study(
            study_id, 'Identification of the Microbiomes for Cannabis Soils',
            'alias', 'TM%s' % study_id)
        self._clean_up_funcs.append(partial(db.delete_study, study_id))

        # Create some plates
        pt = db.get_plate_types()[0]
        plate_id = db.create_sample_plate('Test plate', pt['id'], 'test',
                                          [study_id])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id))
        plate_id_2 = db.create_sample_plate('Test plate 2', pt['id'], 'test',
                                            [study_id])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id_2))

        # Plate some samples
        # Add samples to the study
        sync_qiita_study_samples(study_id)
        samples = db.get_study_samples(study_id)

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

        run, _ = create_sequencing_run(
            pool_id, 'test', 'MiSeq v3 150 cycle', 'MS1234',
            'Illumina', 'MiSeq', 'TrueSeq HT', 151, 151)
        self._clean_up_funcs.insert(
            0, partial(db.delete_sequencing_run, run))

        self._clean_up_funcs.append(
            partial(qiita_client.post, "/apitest/reset/"))

        tmp_dir = mkdtemp()
        with open(join(tmp_dir, 'LabAdmin_test_pool_R1.fastq.gz'), 'w') as f:
            f.write('\n')
        with open(join(tmp_dir, 'LabAdmin_test_pool_R2.fastq.gz'), 'w') as f:
            f.write('\n')
        with open(join(tmp_dir, 'LabAdmin_test_pool_I1.fastq.gz'), 'w') as f:
            f.write('\n')

        self.mock_login_admin()
        data = {'run_id': run, 'run_path': tmp_dir, 'exit_status': 1,
                'logs': json_encode(['/path/to/file.log',
                                     '/another/path.log'])}
        response = self.post('/pm_sequencing_complete/', data=data)
        self.assertEqual(response.code, 200)

        # We are just going to check one of the side effects of this call,
        # since everything else is executed in the same function and tested
        # somewhere else. Magic number 0 -> there is only one comment
        obs = jira_handler.comments('TM%s-5' % study_id)[0]
        exp = ("[CRITICAL]: FAILURE: Sequencing run LabAdmin test pool "
               "(ID: %s). Logs:\n - /path/to/file.log\n - /another/path.log"
               % run)
        self.assertEqual(obs.body, exp)
        obs.delete()

        data = {'run_id': run, 'run_path': tmp_dir, 'exit_status': 0}
        response = self.post('/pm_sequencing_complete/', data=data)
        self.assertEqual(response.code, 200)

        obs = jira_handler.comments('TM%s-5' % study_id)[0]
        self.assertEqual(
            obs.body, "Sequencing complete. Path to raw files: %s" % tmp_dir)


if __name__ == '__main__':
    main()

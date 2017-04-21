# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from unittest import TestCase, main
from traceback import format_exc
from functools import partial
from tempfile import mkdtemp
from shutil import rmtree
from os.path import join, exists
from os import remove
from copy import deepcopy

import pandas as pd
import numpy as np

from knimin import qiita_client, jira_handler, db, config
from knimin.lib.qiita_jira_util import (
    create_study, _create_kl_jira_project, _format_sample_id,
    _update_qiita_samples, sync_qiita_study_samples,
    prepare_targeted_libraries, create_sequencing_run,
    _copy_sequence_files_to_qiita, _assess_replicates,
    complete_sequencing_run)


class TestQiitaJiraUtil(TestCase):
    def setUp(self):
        self._clean_up_funcs = []

    def tearDown(self):
        for f in self._clean_up_funcs:
            try:
                f()
            except Exception as e:
                print("Database clean-up failed. Downstream tests might be "
                      "affected by this! Reason: %s" % format_exc(e))
        qiita_client.post("/apitest/reset/")

    def test_format_sample_id(self):
        self.assertEqual(_format_sample_id('9999.Sample.1', 100, 0, 0),
                         '9999.Sample.1.100.A1')
        self.assertEqual(_format_sample_id('9999.Sample.1', 100, 7, 11),
                         '9999.Sample.1.100.H12')
        self.assertEqual(_format_sample_id('9999.Sample.1', 100, 40, 11),
                         '9999.Sample.1.100.40.12')

    def _create_qiita_test_study(self):
        # Creating the Qiita test study in Jira and the DB
        _create_kl_jira_project('admin', 'Task management', 1,
                                'LabAdmin test project')
        self._clean_up_funcs.append(
            partial(jira_handler.delete_project, 'TM1'))

        db.create_study(
            1, 'Identification of the Microbiomes for Cannabis Soils',
            'alias', 'TM1')
        self._clean_up_funcs.append(partial(db.delete_study, 1))

    def test_update_qiita_samples(self):
        # Testing errors - success is being tested in create_sequencing_run
        # Study does not exist (triggers first error)
        with self.assertRaises(ValueError) as ctx:
            _update_qiita_samples(0, [], [])
        self.assertIn(
            "Can't retrieve study (0) metadata categories from Qiita",
            ctx.exception.message)

        # Study doesn't have metadata (triggers second error)
        study_id = create_study(
            'LabAdmin test project 2', 'Abstract', 'Description', 'Alias',
            'demo@microbio.me',
            {'name': 'LabDude', 'affiliation': 'knight lab'},
            {'name': 'LabDude', 'affiliation': 'knight lab'},
            'admin')

        obs = db.read_study(study_id)
        self._clean_up_funcs.append(partial(jira_handler.delete_project,
                                    obs['jira_id']))
        self._clean_up_funcs.append(partial(db.delete_study, study_id))
        with self.assertRaises(ValueError) as ctx:
            _update_qiita_samples(study_id, [], [])
        self.assertIn(
            "Study (%s) does not have any metadata categories" % study_id,
            ctx.exception.message)

    def test_create_kl_jira_project(self):
        obs = _create_kl_jira_project('admin', 'Task management', 1000,
                                      'LabAdmin test project')
        self._clean_up_funcs.append(
            partial(jira_handler.delete_project, 'TM1000'))

        self.assertEqual(obs['projectKey'], 'TM1000')

        # Check that the issues have been created
        issues = jira_handler.search_issues(
            'issuetype=Task AND project=TM1000')
        self.assertEqual(len(issues), 7)

    def test_create_study(self):
        study_id = create_study(
            'LabAdmin test project', 'Abstract', 'Description', 'Alias',
            'demo@microbio.me',
            {'name': 'LabDude', 'affiliation': 'knight lab'},
            {'name': 'FooName', 'affiliation': 'Bar Lab',
             'email': 'fooname@barlab.foobar'},
            'admin')

        obs = db.read_study(study_id)
        self._clean_up_funcs.append(partial(jira_handler.delete_project,
                                    obs['jira_id']))
        self._clean_up_funcs.append(partial(db.delete_study, study_id))

        exp = {'alias': 'Alias', 'jira_id': 'TM%d' % study_id,
               'study_id': study_id, 'title': 'LabAdmin test project'}
        self.assertEqual(obs, exp)

        # Check that the study has been created in Qiita
        _, obs = qiita_client.get('/api/v1/study/%d' % study_id)
        exp = {'title': 'LabAdmin test project',
               'contacts': {'principal_investigator': ['LabDude', 'knight lab',
                                                       'lab_dude@foo.bar'],
                            'lab_person': ['FooName', 'Bar Lab',
                                           'fooname@barlab.foobar']},
               'study_abstract': 'Abstract',
               'study_description': 'Description',
               'study_alias': 'Alias'}
        self.assertEqual(obs, exp)

        # Check the study has been created in JIRA
        obs = jira_handler.project('TM%d' % study_id)
        self.assertIsNotNone(obs)
        self.assertEqual(obs.name, 'LabAdmin test project')
        self.assertEqual(obs.lead.name, 'admin')

    def test_create_study_error_creating_person(self):
        with self.assertRaises(ValueError) as ctx:
            create_study(
                'LabAdmin test project', 'Abstract', 'Description', 'Alias',
                'demo@microbio.me',
                {'name': 'LabDude', 'affiliation': 'knight lab',
                 'email': 'lab_dude@foo.bar'},
                {'name': 'FooName', 'affiliation': 'Bar Lab',
                 'email': 'fooname@barlab.foobar'},
                'admin')
        self.assertIn('Error creating person "LabDude": ',
                      ctx.exception.message)

    def test_create_study_error_creating_study(self):
        with self.assertRaises(ValueError) as ctx:
            create_study(
                'Identification of the Microbiomes for Cannabis Soils',
                'Abstract', 'Description', 'Alias',
                'demo@microbio.me',
                {'name': 'LabDude', 'affiliation': 'knight lab'},
                {'name': 'FooName2', 'affiliation': 'Bar Lab 2',
                 'email': 'fooname2@barlab.foobar'},
                'admin')
        self.assertIn('Error creating Qiita study:',
                      ctx.exception.message)

    def test_sync_qiita_study_samples(self):
        self._create_qiita_test_study()
        self.assertItemsEqual(db.get_study_samples(1), [])
        sync_qiita_study_samples(1)
        self.assertNotEqual(db.get_study_samples(1), [])

    def test_prepare_targeted_libraries(self):
        study_id = create_study(
            'Test prepare targeted libraries', 'Abstract', 'Description',
            'Alias', 'demo@microbio.me',
            {'name': 'LabDude', 'affiliation': 'knight lab'},
            {'name': 'LabDude', 'affiliation': 'knight lab'},
            'admin')
        obs = db.read_study(study_id)
        jira_id = obs['jira_id']
        self._clean_up_funcs.append(
            partial(jira_handler.delete_project, jira_id))
        self._clean_up_funcs.append(partial(db.delete_study, study_id))

        # Create a plate
        pt = db.get_plate_types()[0]
        plate_id = db.create_sample_plate('TARGETEDTEST', pt['id'], 'test',
                                          [study_id])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id))
        plate_id_2 = db.create_sample_plate('TARGETEDTEST 2', pt['id'], 'test',
                                            [study_id])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id_2))
        layout = [[{}] * pt['cols']] * pt['rows']
        db.write_sample_plate_layout(plate_id, layout)
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
        obs_ids = prepare_targeted_libraries(
            plate_links, 'test', 'ROBE', '208484Z', '108364Z', '14459',
            'RNBD9959')
        for p_id in obs_ids:
            self._clean_up_funcs.insert(
                0, partial(db.delete_targeted_plate, p_id))

        # Check that the DB is not empty
        self.assertIsNotNone(db.read_targeted_plate(obs_ids[0]))

        # Check that JIRA has been updated
        obs = jira_handler.comments('%s-4' % jira_id)[0].body
        self.assertEqual(obs, 'Target gene libraries have been prepared')

    def test_create_sequencing_run(self):
        self._create_qiita_test_study()
        study_id = 1
        obs = db.read_study(study_id)
        jira_id = obs['jira_id']

        # Create a plate
        pt = db.get_plate_types()[0]
        plate_id = db.create_sample_plate('SEQTEST', pt['id'], 'test',
                                          [study_id])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id))

        # Add some samples to the studies
        sync_qiita_study_samples(study_id)
        samples1 = db.get_study_samples(study_id)

        # Create layouts
        well = {'sample_id': 'BLANK', 'name': None, 'notes': None}
        row = [deepcopy(well) for i in range(pt['cols'])]
        layout = [deepcopy(row) for i in range(pt['rows'])]
        for i in range(12):
            layout[0][i]['sample_id'] = samples1[i]
        db.write_sample_plate_layout(plate_id, layout)

        # Create DNA plates
        dna_plate_ids = db.extract_sample_plates(
            [plate_id], 'test', 'HOWE_KF1', 'PM16B11', '108379Z')
        for p_id in dna_plate_ids:
            self._clean_up_funcs.insert(
                0, partial(db.delete_dna_plate, p_id))

        # Create the target gene plates
        plate_links = [
            {'dna_plate_id': dna_plate_ids[0], 'primer_plate_id': 1}]
        targeted_plate_ids = prepare_targeted_libraries(
            plate_links, 'test', 'ROBE', '208484Z', '108364Z', '14459',
            'RNBD9959')
        for p_id in targeted_plate_ids:
            self._clean_up_funcs.insert(
                0, partial(db.delete_targeted_plate, p_id))

        # Create pool samples
        pools = [
            {'targeted_plate_id': targeted_plate_ids[0], 'volume': 240,
             'percentage': 100}]
        pool_id = db.pool_plates(pools, 'LabAdmin test pool', 5)
        self._clean_up_funcs.insert(0, partial(db.delete_pool, pool_id))

        run_id, jira_links = create_sequencing_run(
            pool_id, 'test', 'MiSeq v3 150 cycle', 'MS1234', 'Illumina',
            'MiSeq', 'TrueSeq HT', 151, 151)
        self._clean_up_funcs.insert(
            0, partial(db.delete_sequencing_run, run_id))

        # Check that the sample sheet has been added into JIRA
        obs = jira_handler.issue(
            '%s-4' % jira_id).raw['fields']['attachment'][0]['filename']
        self.assertEqual(obs, 'SampleSheet.LabAdmin_test_pool.TargetGene.csv')

        self.assertEqual(len(jira_links), 1)
        self.assertEqual(jira_links[0][0], 'LabAdmin test project')
        self.assertTrue(jira_links[0][1].endswith('%s-4' % jira_id))

        # Check that the DB is not empty
        self.assertIsNotNone(db.read_sequencing_run(run_id))

        # Check that JIRA has been updated
        obs = jira_handler.comments('%s-4' % jira_id)[0].body
        self.assertEqual(obs, 'Target gene libraries have been prepared')

    def test_assess_replicates(self):
        prep = pd.DataFrame.from_dict(
            {0: {'target_gene': '16S', 'study_id': 1, 'run_name': 'test_run',
                 'dna_plate_id': 1, 'row': 1, 'col': 1,
                 'sample_name': '1.Sample1'},
             1: {'target_gene': '16S', 'study_id': 1, 'run_name': 'test_run',
                 'dna_plate_id': 1, 'row': 1, 'col': 2,
                 'sample_name': '1.Sample2'},
             2: {'target_gene': '16S', 'study_id': 1, 'run_name': 'test_run',
                 'dna_plate_id': 1, 'row': 1, 'col': 3,
                 'sample_name': '1.BLANK'},
             3: {'target_gene': '16S', 'study_id': 1, 'run_name': 'test_run',
                 'dna_plate_id': 1, 'row': 1, 'col': 4,
                 'sample_name': '1.Sample1'},
             4: {'target_gene': '16S', 'study_id': 1, 'run_name': 'test_run',
                 'dna_plate_id': 1, 'row': 1, 'col': 5,
                 'sample_name': '1.Sample2'},
             5: {'target_gene': '16S', 'study_id': 1, 'run_name': 'test_run',
                 'dna_plate_id': 1, 'row': 1, 'col': 6,
                 'sample_name': '1.BLANK'},
             6: {'target_gene': '16S', 'study_id': 1, 'run_name': 'test_run',
                 'dna_plate_id': 1, 'row': 1, 'col': 7,
                 'sample_name': '1.Sample3'}}, orient='index')
        obs_prep, obs_repl = _assess_replicates(prep)
        self.assertItemsEqual(obs_repl, ['1.Sample1.1.A1', '1.Sample2.1.A2',
                                         '1.BLANK.1.A3', '1.Sample1.1.A4',
                                         '1.Sample2.1.A5', '1.BLANK.1.A6'])
        exp = pd.DataFrame.from_dict(
            {'1.Sample1.1.A1': {'target_gene': '16S', 'study_id': 1,
                                'run_name': 'test_run', 'dna_plate_id': 1,
                                'row': 1, 'col': 1,
                                'original_sample_name': '1.Sample1'},
             '1.Sample2.1.A2': {'target_gene': '16S', 'study_id': 1,
                                'run_name': 'test_run', 'dna_plate_id': 1,
                                'row': 1, 'col': 2,
                                'original_sample_name': '1.Sample2'},
             '1.BLANK.1.A3': {'target_gene': '16S', 'study_id': 1,
                              'run_name': 'test_run', 'dna_plate_id': 1,
                              'row': 1, 'col': 3,
                              'original_sample_name': '1.BLANK'},
             '1.Sample1.1.A4': {'target_gene': '16S', 'study_id': 1,
                                'run_name': 'test_run', 'dna_plate_id': 1,
                                'row': 1, 'col': 4,
                                'original_sample_name': '1.Sample1'},
             '1.Sample2.1.A5': {'target_gene': '16S', 'study_id': 1,
                                'run_name': 'test_run', 'dna_plate_id': 1,
                                'row': 1, 'col': 5,
                                'original_sample_name': '1.Sample2'},
             '1.BLANK.1.A6': {'target_gene': '16S', 'study_id': 1,
                              'run_name': 'test_run', 'dna_plate_id': 1,
                              'row': 1, 'col': 6,
                              'original_sample_name': '1.BLANK'},
             '1.Sample3': {'target_gene': '16S', 'study_id': 1,
                           'run_name': 'test_run', 'dna_plate_id': 1,
                           'row': 1, 'col': 7,
                           'original_sample_name': '1.Sample3'}},
            orient='index')
        obs_prep.sort_index(axis=0, inplace=True)
        obs_prep.sort_index(axis=1, inplace=True)
        exp.sort_index(axis=0, inplace=True)
        exp.sort_index(axis=1, inplace=True)
        exp.index.name = 'sample_name'
        pd.util.testing.assert_frame_equal(obs_prep, exp)

    def test_copy_sequence_files_to_qiita(self):
        prep = pd.DataFrame.from_dict(
            {'1.Sample1': {'target_gene': '16S', 'study_id': 1,
                           'run_name': 'test_run'},
             '1.Sample2': {'target_gene': '16S', 'study_id': 1,
                           'run_name': 'test_run'},
             '1.Sample3': {'target_gene': '16S', 'study_id': 1,
                           'run_name': 'test_run'}}, orient='index')
        # Mock a targeted run
        run_dp = mkdtemp()
        self._clean_up_funcs.append(partial(rmtree, run_dp))
        exp_fn = ['test_run_LANE_R1_001.fastq.gz',
                  'test_run_LANE_R2_001.fastq.gz',
                  'test_run_LANE_I1_001.fastq.gz']
        for fn in exp_fn:
            with open(join(run_dp, fn), 'w') as f:
                f.write('\n')
        qiita_fps = [join(config.qiita_uploads_dir, '1', bn) for bn in exp_fn]
        exp_fps = [('test_run_LANE_R1_001.fastq.gz', 'raw_forward_seqs'),
                   ('test_run_LANE_R2_001.fastq.gz', 'raw_reverse_seqs'),
                   ('test_run_LANE_I1_001.fastq.gz', 'raw_barcodes')]
        obs_atype, obs_fps = _copy_sequence_files_to_qiita(prep, run_dp)
        self.assertEqual(obs_atype, "FASTQ")
        self.assertItemsEqual(obs_fps, exp_fps)
        for fp in qiita_fps:
            self.assertTrue(exists(fp))
            self._clean_up_funcs.append(partial(remove, fp))

        # Mock a shotgun run
        del prep['target_gene']
        run_dp = mkdtemp()
        self._clean_up_funcs.append(partial(rmtree, run_dp))
        exp_fn = []
        for s in ['1_Sample1', '1_Sample2', '1_Sample3']:
            for ext in ['%s_LANE_R1_001.fastq.gz', '%s_LANE_R2_001.fastq.gz']:
                fn = ext % s
                exp_fn.append(fn)
                with open(join(run_dp, fn), 'w') as f:
                    f.write('\n')
        qiita_fps = [join(config.qiita_uploads_dir, '1', bn) for bn in exp_fn]
        exp_fps = [('1_Sample1_LANE_R1_001.fastq.gz', 'raw_forward_seqs'),
                   ('1_Sample1_LANE_R2_001.fastq.gz', 'raw_reverse_seqs'),
                   ('1_Sample2_LANE_R1_001.fastq.gz', 'raw_forward_seqs'),
                   ('1_Sample2_LANE_R2_001.fastq.gz', 'raw_reverse_seqs'),
                   ('1_Sample3_LANE_R1_001.fastq.gz', 'raw_forward_seqs'),
                   ('1_Sample3_LANE_R2_001.fastq.gz', 'raw_reverse_seqs')]
        obs_atype, obs_fps = _copy_sequence_files_to_qiita(prep, run_dp)
        self.assertEqual(obs_atype, "per_sample_FASTQ")
        self.assertItemsEqual(obs_fps, exp_fps)
        for fp in qiita_fps:
            self.assertTrue(exists(fp))
            self._clean_up_funcs.append(partial(remove, fp))

    def test_complete_sequencing_run(self):
        self._create_qiita_test_study()

        # Create some plates
        p_id = db.create_sample_plate('Plate 1', 1, 'test', [1])
        self._clean_up_funcs.insert(0, partial(db.delete_sample_plate, p_id))

        sync_qiita_study_samples(1)
        samples1 = db.get_study_samples(1)

        # Create layouts
        well = {'sample_id': 'BLANK', 'name': None, 'notes': None}
        row = [deepcopy(well) for i in range(12)]
        layout = [deepcopy(row) for i in range(8)]
        layout2 = deepcopy(layout)
        for i in range(12):
            layout[0][i]['sample_id'] = samples1[i]
        for i in range(8):
            layout2[i][0]['sample_id'] = samples1[i]
        db.write_sample_plate_layout(p_id, layout)

        # Create DNA plates
        dna_plate_ids = db.extract_sample_plates(
            [p_id], 'test', 'HOWE_KF1', 'PM16B11', '108379ZZ')
        for i in dna_plate_ids:
            self._clean_up_funcs.insert(0, partial(db.delete_dna_plate, i))

        # Create the target gene plates
        plate_links = [
            {'dna_plate_id': dna_plate_ids[0], 'primer_plate_id': 1}]
        targeted_ids = db.prepare_targeted_libraries(
            plate_links, 'test', 'ROBE', '208484Z', '108364Z', '14459',
            'RNBD9959')
        for i in targeted_ids:
            self._clean_up_funcs.insert(
                0, partial(db.delete_targeted_plate, i))

        # Quantify the plate
        db.quantify_targeted_plate(
            targeted_ids[0], 'raw_concentration',
            np.random.uniform(125, 175, size=(8, 12)))
        db.quantify_targeted_plate(
            targeted_ids[0], 'mod_concentration',
            np.random.uniform(4, 6, size=(8, 12)))

        # Prepare the pools
        pools = [
            {'targeted_plate_id': targeted_ids[0], 'volume': 240,
             'percentage': 100}]
        pool_id = db.pool_plates(pools, 'TestPool', 5)
        self._clean_up_funcs.insert(0, partial(db.delete_pool, pool_id))

        # Create the sequencing run
        run_id, _ = create_sequencing_run(
            pool_id, 'test', 'MiSeq v3 150 cycle', 'MS1234',
            'Illumina', 'MiSeq', 'TrueSeq HT', 151, 151)
        self._clean_up_funcs.insert(
            0, partial(db.delete_sequencing_run, run_id))

        tmp_dir = mkdtemp()
        with open(join(tmp_dir, 'TestPool_LANE_R1_001.fastq.gz'), 'w') as f:
            f.write('\n')
        with open(join(tmp_dir, 'TestPool_LANE_R2_001.fastq.gz'), 'w') as f:
            f.write('\n')
        with open(join(tmp_dir, 'TestPool_LANE_I1_001.fastq.gz'), 'w') as f:
            f.write('\n')

        complete_sequencing_run(False, run_id, tmp_dir, ['/path/to/file.log',
                                                         '/another/path.log'])
        obs = jira_handler.comments('TM1-5')[0]
        exp = ("[CRITICAL]: FAILURE: Sequencing run TestPool "
               "(ID: %s). Logs:\n - /path/to/file.log\n - /another/path.log"
               % run_id)
        self.assertEqual(obs.body, exp)
        obs.delete()

        complete_sequencing_run(True, run_id, tmp_dir, [])
        obs = jira_handler.comments('TM1-5')[0]
        exp = ("Sequencing complete. Path to raw files: %s"
               % tmp_dir)


if __name__ == '__main__':
    main()

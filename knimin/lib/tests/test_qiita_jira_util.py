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

from knimin import qiita_client, jira_handler, db
from knimin.lib.qiita_jira_util import (
    create_study, _create_kl_jira_project, _format_sample_id,
    _update_qiita_samples, sync_qiita_study_samples,
    extract_sample_plates, prepare_targeted_libraries,
    create_sequencing_run)


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

    @classmethod
    def tearDownClass(cls):
        # Reset the qiita DB to make tests independent
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
        # Testing errors - success is being tested in extract_sample_plates
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
            "Can't retrieve study (%s) metadata from Qiita" % study_id,
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

    def test_extract_sample_plates(self):
        self._create_qiita_test_study()
        sync_qiita_study_samples(1)

        # Create some plates
        pt = db.get_plate_types()[0]
        plate_id = db.create_sample_plate('Test plate', pt['id'], 'test', [1])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id))

        samples = db.get_study_samples(1)
        layout = []
        row = []
        for i in range(pt['rows']):
            for j in range(pt['cols']):
                row.append({'sample_id': None, 'name': None, 'notes': None})
            layout.append(row)
            row = []
        for i in range(10):
            layout[0][i]['sample_id'] = samples[i]
        # Add some blanks
        layout[1][0]['sample_id'] = 'BLANK'
        layout[2][0]['sample_id'] = 'BLANK'
        layout[3][0]['sample_id'] = 'BLANK'
        # Add some replicates
        layout[1][1]['sample_id'] = samples[0]
        layout[2][1]['sample_id'] = samples[1]
        layout[3][1]['sample_id'] = samples[2]
        db.write_sample_plate_layout(plate_id, layout)

        dna_plates = extract_sample_plates(
            [plate_id], 'test', 'HOWE_KF1', 'PM16B11', '108379Z')
        self._clean_up_funcs.insert(
            0, partial(db.delete_dna_plate, dna_plates[0]))

        # Check the DB info is not empty
        self.assertIsNotNone(db.read_dna_plate(dna_plates[0]))

        # Check Qiita has been updated correctly
        sc, obs = qiita_client.get('/api/v1/study/1/samples')
        exp = ['1.BLANK.%s.B1' % dna_plates[0],
               '1.BLANK.%s.C1' % dna_plates[0],
               '1.BLANK.%s.D1' % dna_plates[0],
               '%s.%s.A1' % (samples[0], dna_plates[0]),
               '%s.%s.A2' % (samples[1], dna_plates[0]),
               '%s.%s.A3' % (samples[2], dna_plates[0]),
               '%s.%s.B2' % (samples[0], dna_plates[0]),
               '%s.%s.C2' % (samples[1], dna_plates[0]),
               '%s.%s.D2' % (samples[2], dna_plates[0])]
        exp.extend(samples)
        self.assertItemsEqual(obs, exp)

        # Check Jira has been updated correctly
        # Magic number 0 -> there is only 1 comment
        obs = jira_handler.comments('TM1-4')[0].body
        self.assertEqual(obs, 'Samples have been plated')

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

        # Crate a plate
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
        # create_sequencing_run()
        pass


if __name__ == '__main__':
    main()

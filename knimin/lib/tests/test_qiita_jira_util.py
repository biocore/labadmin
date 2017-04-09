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
from knimin.lib.qiita_jira_util import create_study


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


if __name__ == '__main__':
    main()

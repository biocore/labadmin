from unittest import TestCase, main

from knimin.lib.qiita_jira_util import create_project
from knimin import jira_handler


class TestQiitaJiraUtil(TestCase):
    def tearDown(self):
        jira_handler.delete_project('TM10001')

    def test_create_project(self):
        pj_name = 'My New Project'

        # check success
        pj, message = create_project(pj_name)
        self.assertEqual(message, '')
        self.assertEqual(pj['projectName'], pj_name)
        self.assertEqual(pj['projectKey'], 'TM10001')

        # check failure
        pj, message = create_project(pj_name)
        self.assertIsNone(pj)
        exp_msg = ("A project with that name already exists., Project "
                   "'%s' uses this project key." % pj_name)
        self.assertEqual(message, exp_msg)


if __name__ == '__main__':
    main()

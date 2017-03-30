from unittest import TestCase, main

from knimin.lib.qiita_jira_util import create_project


class TestQiitaJiraUtil(TestCase):
    def test_create_project(self):
        pj_name = 'My New Project'

        # check success
        pj, message = create_project(pj_name)
        self.assertEqual(pj.name, pj_name)
        self.assertEqual(pj.key, 'TM10001)
        self.assertEqual(message, '')

        # check failure
        pj, message = create_project(pj_name)
        self.assertIsNone(pj)
        self.assertEqual(message, 'A project with that name already exists.')


if __name__ == '__main__':
    main()

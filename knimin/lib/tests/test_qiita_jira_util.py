from unittest import TestCase, main

from knimin.lib.qiita_jira_util import create_project


class TestQiitaJiraUtil(TestCase):
    def test_create_project(self):
        print create_project('My New Project')

if __name__ == '__main__':
    main()

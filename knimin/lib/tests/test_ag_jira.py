from unittest import TestCase, main

from knimin.lib.ag_jira import jira_connect, get_projects
from jira.resources import Project
from jira.client import JIRA


class TestJira(TestCase):
    def test_jira_connect_error(self):
        with self.assertRaises(ValueError):
            jira_connect(user=None)

    def test_get_projects(self):
        projects = get_projects()
        for p in projects:
            self.assertTrue(isinstance(p, Project))

    def test_jira_connect(self):
        jc = jira_connect(user=None, password=None)
        self.assertTrue(isinstance(jc, JIRA))


if __name__ == '__main__':
    main()

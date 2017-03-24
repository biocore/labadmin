from unittest import TestCase, main

from knimin.lib.ag_jira import jira_connect, get_projects
from jira.resources import Project

class TestJira(TestCase):
    def test_get_projects(self):
        projects = get_projects()
        for p in projects:
            self.assertTrue(isinstance(p, Project))


if __name__ == '__main__':
    main()

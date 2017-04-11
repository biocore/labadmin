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
from knimin import db, qiita_client, jira_handler


class TestPMCreatePlateHandler(TestHandlerBase):
    def test_get_not_authed(self):
        response = self.get('/pm_create_study/')
        self.assertEqual(response.code, 200)
        self.assertTrue(
            response.effective_url.endswith('?next=%2Fpm_create_study%2F'))

    def test_get(self):
        self.mock_login_admin()
        response = self.get('/pm_create_study/')
        self.assertEqual(response.code, 200)
        self.assertIn('<h3>Create new project</h3>', response.body)
        self.assertIn('LabDude (knight lab)</option>', response.body)

    def test_post_not_authed(self):
        data = {'qiita-user': 'demo@microbio.me',
                'jira-user': 'admin',
                'study-title': 'LabAdmin test project',
                'study-description': 'Description',
                'study-abstract': 'Abstract',
                'study-alias': 'Alias',
                'qiita-pi': '{"affiliation": "Wash U", "name": "PIDude"}',
                'qiita-lp': '{"affiliation": "Wash U", "name": "PIDude"}'}
        response = self.post('/pm_create_study/', data=data)
        self.assertEqual(response.code, 403)

    def test_post(self):
        self.mock_login_admin()
        data = {'qiita-user': 'demo@microbio.me',
                'jira-user': 'admin',
                'study-title': 'LabAdmin test project',
                'study-description': 'Description',
                'study-abstract': 'Abstract',
                'study-alias': 'Alias',
                'qiita-pi': '{"affiliation": "Wash U", "name": "PIDude"}',
                'qiita-lp': '{"affiliation": "Wash U", "name": "PIDude"}'}
        response = self.post('/pm_create_study/', data=data)

        self._clean_up_funcs.append(
            partial(qiita_client.post, '/apitest/reset/'))
        projects = [p for p in jira_handler.projects()
                    if p.name == 'LabAdmin test project']
        study_id = re.search('\d+', projects[0].key).group(0)
        self._clean_up_funcs.append(partial(projects[0].delete))
        self._clean_up_funcs.append(partial(db.delete_study, study_id))

        self.assertEqual(response.code, 200)
        exp = ('<h3>Study "LabAdmin test project" successfully created with '
               'ID %s</h3>' % study_id)
        self.assertIn(exp, response.body)

        response = self.post('/pm_create_study/', data=data)
        self.assertEqual(response.code, 500)


if __name__ == '__main__':
    main()

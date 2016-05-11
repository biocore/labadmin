from unittest import main
from os.path import dirname, realpath, join
from string import ascii_letters
from random import choice

from knimin import db
from knimin.tests.tornado_test_base import TestHandlerBase


class TestThirdPartyData(TestHandlerBase):
    ext_survey_fp = join(dirname(realpath(__file__)), 'data',
                         'external_survey_data.csv')

    def setUp(self):
        # Make sure vioscreen survey exists in DB
        try:
            db.add_external_survey('Vioscreen', 'FFQ', 'http://vioscreen.com')
        except ValueError:
            pass
        super(TestThirdPartyData, self).setUp()

    def test_get_not_logged_in(self):
        db.alter_access_levels('test', [4])
        response = self.get('/ag_third_party/data/')
        self.assertEqual(response.code, 200)
        self.assertTrue(response.effective_url.endswith(
            '?next=%2Fag_third_party%2Fdata%2F'))

    def test_get_not_authed(self):
        self.mock_login()
        response = self.get('/ag_third_party/data/')
        self.assertEqual(response.code, 403)

    def test_get(self):
        self.mock_login()
        db.alter_access_levels('test', [4])
        response = self.get('/ag_third_party/data/')
        self.assertEqual(response.code, 200)
        self.assertIn('File seperator', response.body)
        self.assertIn('Vioscreen', response.body)

    def test_post_not_authed(self):
        self.mock_login()
        response = self.post('/ag_third_party/data/',
                             data={'survey': '', 'seperator': 'comma',
                                   'survey_id': '', 'trim': ''})
        self.assertEqual(response.code, 403)

    def test_post_not_logged_in(self):
        db.alter_access_levels('test', [4])
        data = {'survey': 'Vioscreen', 'seperator': 'comma',
                'survey_id': 'SubjectId', 'trim': '-160'}
        files = {'file_in': self.ext_survey_fp}
        response = self.post('/ag_third_party/data/', data, files)
        self.assertEqual(response.code, 403)

    def test_post_data(self):
        self.mock_login()
        db.alter_access_levels('test', [4])
        data = {'survey': 'Vioscreen', 'seperator': 'comma',
                'survey_id': 'SubjectId', 'trim': '-160'}
        files = {'file_in': self.ext_survey_fp}

        response = self.multipart_post('/ag_third_party/data/', data, files)
        self.assertEqual(response.code, 200)
        self.assertIn("3 surveys added to 'Vioscreen' successfully",
                      response.body)

        # Grab one of the inserted surveys for testing
        obs = db.get_external_survey('Vioscreen', ['14f508185c954721'])
        self.assertTrue(len(obs['14f508185c954721']) == 274)
        self.assertIn('HEI2010_Greens_Beans', obs['14f508185c954721'].keys())
        db._clear_table('external_survey_answers', 'ag')

    def test_post_missing_data(self):
        self.mock_login()
        db.alter_access_levels('test', [4])
        data = {'seperator': 'comma', 'survey_id': 'SubjectId', 'trim': ''}
        files = {'file_in': self.ext_survey_fp}

        response = self.multipart_post('/ag_third_party/data/', data, files)
        self.assertEqual(response.code, 200)
        self.assertIn('Third Party survey</label>\n\n<ul class="errors">'
                      '<li>Not a valid choice', response.body)
        db._clear_table('external_survey_answers', 'ag')


class TestNewThirdParty(TestHandlerBase):
    def setUp(self):
        # Make sure vioscreen survey exists in DB
        try:
            db.add_external_survey('Vioscreen', 'FFQ', 'http://vioscreen.com')
        except ValueError:
            pass
        super(TestNewThirdParty, self).setUp()

    def test_get_not_authed(self):
        response = self.get('/ag_third_party/add/')
        self.assertEqual(response.code, 200)
        self.assertTrue(response.effective_url.endswith(
            '?next=%2Fag_third_party%2Fadd%2F'))

    def test_get(self):
        self.mock_login()
        db.alter_access_levels('test', [4])
        response = self.get('/ag_third_party/add/')
        self.assertEqual(response.code, 200)
        self.assertIn('<label for="description">Description</label>',
                      response.body)

    def test_post_not_authed(self):
        name = ''.join([choice(ascii_letters) for x in range(15)])
        response = self.post('/ag_third_party/add/',
                             data={'name': name, 'description': 'TEST',
                                   'url': 'test.fake'})
        self.assertEqual(response.code, 403)

    def test_post_data(self):
        self.mock_login()
        db.alter_access_levels('test', [4])
        name = ''.join([choice(ascii_letters) for x in range(15)])
        response = self.post('/ag_third_party/add/',
                             data={'name': name, 'description': 'TEST',
                                   'url': 'test.fake'})
        self.assertEqual(response.code, 200)
        self.assertIn("Added '%s' successfully" % name, response.body)

    def test_post_missing_data(self):
        self.mock_login()
        db.alter_access_levels('test', [4])
        name = ''.join([choice(ascii_letters) for x in range(15)])
        data = {'name': name, 'description': 'TEST', 'url': ''}

        response = self.post('/ag_third_party/add/', data)
        self.assertEqual(response.code, 200)
        self.assertIn('Survey URL</label>\n\n<ul class="errors"><li>'
                      'Required field', response.body)
        db._clear_table('external_survey_answers', 'ag')

    def test_post_existing_survey(self):
        self.mock_login()
        db.alter_access_levels('test', [4])
        data = {'name': 'Vioscreen', 'description': 'TEST', 'url': 'test.fake'}

        response = self.post('/ag_third_party/add/', data)
        self.assertEqual(response.code, 200)
        self.assertIn("Survey 'Vioscreen' already exists", response.body)
        db._clear_table('external_survey_answers', 'ag')

if __name__ == "__main__":
    main()

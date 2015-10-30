from unittest import main
from os.path import dirname, realpath, join

from knimin import db
from knimin.tests.tornado_test_base import TestHandlerBase


class TestThirdPartyData(TestHandlerBase):
    ext_survey_fp = join(dirname(realpath(__file__)), 'data',
                         'external_survey_data.csv')

    def test_get_not_authed(self):
        response = self.get('/ag_third_party/data/')
        self.assertEqual(response.code, 200)
        self.assertTrue(response.effective_url.endswith(
            '?next=%2Fag_third_party%2Fdata%2F'))

    def test_get(self):
        self.mock_login()
        response = self.get('/ag_third_party/data/')
        self.assertEqual(response.code, 200)
        self.assertIn('File seperator', response.body)

    def test_post_not_authed(self):
        response = self.post('/ag_third_party/data/',
                             data={'survey': '', 'seperator': 'comma',
                                   'survey_id': '', 'trim': ''})
        self.assertEqual(response.code, 403)

    def test_post_data(self):
        self.mock_login()
        data = {'survey': 'Vioscreen', 'seperator': 'comma',
                'survey_id': 'SubjectId', 'trim': '-160'}
        files = {'file_in': self.ext_survey_fp}

        response = self.multipart_post('/ag_third_party/data/', data, files)
        self.assertEqual(response.code, 200)
        self.assertIn("3 surveys added to 'Vioscreen' successfully",
                      response.body)
        db._clear_table('external_survey_answers', 'ag')

    def test_post_missing_data(self):
        self.mock_login()
        data = {'seperator': 'comma', 'survey_id': 'SubjectId', 'trim': ''}
        files = {'file_in': self.ext_survey_fp}

        response = self.multipart_post('/ag_third_party/data/', data, files)
        self.assertEqual(response.code, 200)
        self.assertIn('Third Party survey</label>\n\n<ul class="errors">'
                      '<li>Not a valid choice', response.body)
        db._clear_table('external_survey_answers', 'ag')


if __name__ == "__main__":
    main()

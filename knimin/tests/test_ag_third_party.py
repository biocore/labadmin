from unittest import main
import os
from os.path import dirname, realpath, join
from random import choice
from string import ascii_letters

from tornado.escape import url_escape

from knimin.tests.tornado_test_base import TestHandlerBase
from knimin import db
from knimin.handlers.ag_third_party import ThirdPartyData, NewThirdParty


class AGThirdPartyHandler(TestHandlerBase):
    ext_survey_fp = join(dirname(realpath(__file__)), 'data',
                         'external_survey_data.csv')

    def setUp(self):
        # Make sure vioscreen survey exists in DB
        try:
            db.add_external_survey('Vioscreen', 'FFQ', 'http://vioscreen.com')
        except ValueError:
            pass
        super(AGThirdPartyHandler, self).setUp()

    def test_get_not_authed(self):
        response = self.get('/ag_third_party/data/')
        self.assertEqual(response.code, 200)
        port = self.get_http_port()
        self.assertEqual(response.effective_url,
                         'http://localhost:%d/login/?next=%s' %
                         (port, url_escape('/ag_third_party/data/')))
        self.mock_login()
        response = self.get('/ag_third_party/data/')
        self.assertEqual(response.code, 403)

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

    def test_get(self):
        self.mock_login_admin()
        tpsurveys = db.list_external_surveys()
        form = ThirdPartyData()
        # make sure that at least this third party survey exist in the DB
        if len(tpsurveys) == 0:
            response = self.post('/ag_third_party/add/',
                                 {'name': 'newTPsurvey',
                                  'description': 'akSJdghcakscmakld  fh',
                                  'url': 'www.google.com'})

        response = self.get('/ag_third_party/data/')
        self.assertEqual(response.code, 200)
        # test that all fields are present in the HTML side.
        for key, element in form.__dict__['_fields'].items():
            self.assertIn(str(element.label), response.body)
        for survey in tpsurveys:
            self.assertIn('<option value="%s">%s</option>' % (survey, survey),
                          response.body)

    def test_post_data(self):
        self.mock_login_admin()
        data = {'survey': 'Vioscreen', 'seperator': 'comma',
                'survey_id': 'SubjectId', 'trim': '-160'}
        files = {'file_in': self.ext_survey_fp}

        response = self.multipart_post('/ag_third_party/data/', data, files)
        self.assertEqual(response.code, 200)
        self.assertIn("3 surveys added to 'Vioscreen' successfully",
                      response.body)

        # Grab one of the inserted surveys for testing
        id = '14f508185c954721'
        obs = db.get_external_survey('Vioscreen', [id])
        self.assertTrue(len(obs[id]) == 274)
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

    def test_post_wrong_arguments(self):
        self.mock_login_admin()
        data = {'survey': 'NotInDB',
                'seperator': 'comma',
                'survey_id': 'SubjectId',
                'trim': '-160'}
        files = {'file_in': self.ext_survey_fp}
        response = self.multipart_post('/ag_third_party/data/', data, files)
        self.assertIn('<ul class="errors"><li>Not a valid choice</li></ul>',
                      response.body)
        self.assertEqual(response.code, 200)

        data = {'survey': 'Vioscreen',
                'seperator': 'blub',
                'survey_id': 'SubjectId',
                'trim': '-160'}
        files = {'file_in': self.ext_survey_fp}
        response = self.multipart_post('/ag_third_party/data/', data, files)
        response = self.multipart_post('/ag_third_party/data/', data, files)
        self.assertIn('<ul class="errors"><li>Not a valid choice</li></ul>',
                      response.body)
        self.assertEqual(response.code, 200)

        data = {'survey': 'Vioscreen',
                'seperator': 'comma',
                'survey_id': 'Subject__Id',
                'trim': '-160'}
        files = {'file_in': self.ext_survey_fp}
        response = self.multipart_post('/ag_third_party/data/', data, files)
        self.assertIn('Header column not found', response.body)

        # test reporting error messages
        data = {'survey': 'NotInDB',
                'seperator': 'comma',
                'survey_id': 'Subject__Id',
                'trim': '-160'}
        files = {'file_in': self.ext_survey_fp}
        response = self.multipart_post('/ag_third_party/data/', data, files)
        self.assertIn('<ul class="errors"><li>Not a valid choice</li></ul>',
                      response.body)


class AGNewThirdPartyHandler(TestHandlerBase):
    def setUp(self):
        # Make sure vioscreen survey exists in DB
        try:
            db.add_external_survey('Vioscreen', 'FFQ', 'http://vioscreen.com')
        except ValueError:
            pass
        super(AGNewThirdPartyHandler, self).setUp()

    def test_post_not_authed(self):
        name = ''.join([choice(ascii_letters) for x in range(15)])
        response = self.post('/ag_third_party/add/',
                             data={'name': name, 'description': 'TEST',
                                   'url': 'test.fake'})
        self.assertEqual(response.code, 403)

    def test_get_not_authed(self):
        response = self.get('/ag_third_party/add/')
        self.assertEqual(response.code, 200)
        port = self.get_http_port()
        self.assertEqual(response.effective_url,
                         'http://localhost:%d/login/?next=%s' %
                         (port, url_escape('/ag_third_party/add/')))

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

    def test_get(self):
        self.mock_login_admin()
        response = self.get('/ag_third_party/add/')
        self.assertEqual(response.code, 200)
        form = NewThirdParty()
        # test that all fields are present in the HTML side.
        for key, element in form.__dict__['_fields'].items():
            self.assertIn(str(element.label), response.body)

    def test_post(self):
        self.mock_login_admin()
        name = 'testNewTPSurvey_' + str(os.getpid())

        # add a new Survey
        response = self.post('/ag_third_party/add/',
                             {'name': name,
                              'description': 'akSJdghcakscmakld  fh',
                              'url': 'www.google.com'})
        self.assertEqual(response.code, 200)
        self.assertIn("<div style='color:red;'>Added '%s' successfully</div>"
                      % name, response.body)

        # check that existing surveys cannot be added
        response = self.post('/ag_third_party/add/',
                             {'name': name,
                              'description': 'akSJdghcakscmakld  fh',
                              'url': 'www.google.com'})
        self.assertEqual(response.code, 200)
        self.assertIn(("<div style='color:red;'>Survey '%s' already "
                       "exists</div>") % name, response.body)

        # check for missing fields
        response = self.post('/ag_third_party/add/',
                             {'name': 'new',
                              'url': 'www.google.com'})
        self.assertEqual(response.code, 200)
        self.assertIn('<ul class="errors"><li>Required field</li></ul>',
                      response.body)
        response = self.post('/ag_third_party/add/',
                             {'name': 'new',
                              'description': 'akSJdghcakscmakld  fh'})
        self.assertEqual(response.code, 200)
        self.assertIn('<ul class="errors"><li>Required field</li></ul>',
                      response.body)


if __name__ == "__main__":
    main()

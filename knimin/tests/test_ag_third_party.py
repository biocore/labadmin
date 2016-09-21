from unittest import main
import os

from tornado.escape import url_escape

from knimin.tests.tornado_test_base import TestHandlerBase
from knimin import db
from knimin.handlers.ag_third_party import ThirdPartyData, NewThirdParty


class AGThirdPartyHandler(TestHandlerBase):
    def test_get_not_authed(self):
        response = self.get('/ag_third_party/data/')
        self.assertEqual(response.code, 200)
        port = self.get_http_port()
        self.assertEqual(response.effective_url,
                         'http://localhost:%d/login/?next=%s' %
                         (port, url_escape('/ag_third_party/data/')))

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

    # def test_post(self):
    #     self.mock_login_admin()
    #     form = ThirdPartyData()
    #     tpsurveys = db.list_external_surveys()
    #     response = self.post('/ag_third_party/data/',
    #                          {'survey': tpsurveys[0],
    #                           'file_in': ,
    #                           'seperator': ',',
    #                           'survey_id': 'SRVID',
    #                           'trim': ''})
    #     print("post")


class AGNewThirdPartyHandler(TestHandlerBase):
    def test_get_not_authed(self):
        response = self.get('/ag_third_party/add/')
        self.assertEqual(response.code, 200)
        port = self.get_http_port()
        self.assertEqual(response.effective_url,
                         'http://localhost:%d/login/?next=%s' %
                         (port, url_escape('/ag_third_party/add/')))

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
        # form = NewThirdParty()
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

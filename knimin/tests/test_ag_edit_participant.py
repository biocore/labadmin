from unittest import main

from tornado.escape import url_escape, xhtml_escape

from knimin.tests.tornado_test_base import TestHandlerBase
from knimin import db


class testAGEditParticipantHandler(TestHandlerBase):
    def test_get_not_authed(self):
        response = self.get('/ag_edit_participant/')
        self.assertEqual(response.code, 200)
        port = self.get_http_port()
        self.assertEqual(response.effective_url,
                         'http://localhost:%d/login/?next=%s' %
                         (port, url_escape('/ag_edit_participant/')))

    def test_get(self):
        ag_login_id = '0077c686-b0ad-11f8-e050-8a800c5d1877'
        self.mock_login_admin()
        email = db.get_login_info(ag_login_id)[0]['email']
        response = self.get('/ag_edit_participant/', {'email': email})
        self.assertEqual(response.code, 200)

        # check that all relevant user information is rendered on HTML side
        login = db.get_login_by_email(email)
        for key, value in login.items():
            if not isinstance(key, unicode):
                key = key.decode('utf-8')
            if key == 'zip':
                key = u'zipcode'
            elif key == 'ag_login_id':
                continue
            if not isinstance(value, unicode):
                value = value.decode('utf-8')
            key = xhtml_escape(key.encode('utf-8'))
            value = xhtml_escape(value.encode('utf-8'))
            self.assertIn(('</td><td><input type="text" name="%s" id="%s" '
                           'value="%s"></td></tr>') % (key, key, value),
                          response.body)

        # check what happens if user with email does not exist.
        # TODO: we should create a better error message in the handler to be
        # displayed, see issue: #115
        response = self.get('/ag_edit_participant/?email=notInDB')
        self.assertIn('AN ERROR HAS OCCURED!', response.body)
        self.assertEqual(response.code, 500)

        # TODO: similarly if no email, i.e. user, is given. Issue: #115
        response = self.get('/ag_edit_participant/?email=')
        self.assertIn('AN ERROR HAS OCCURED!', response.body)
        self.assertEqual(response.code, 500)

    def test_post(self):
        self.mock_login_admin()

        name = u'TESTDUDE'
        address = u'123 fake test street'
        city = u'testcity'
        state = u'\xc3\x8ele-de-France'
        zipcode = u'1L2 2G3'
        country = 'United Kingdom'
        ag_login_id = '0023cc03-3332-eec6-e050-8a800c5d3c04'
        email = db.get_login_info(ag_login_id)[0]['email']

        # check a regular update
        response = self.post('/ag_edit_participant/',
                             {'email': email,
                              'name': name,
                              'address': address,
                              'city': city,
                              'state': state,
                              'zipcode': zipcode,
                              'country': country,
                              'ag_login_id': ag_login_id})
        self.assertEqual(response.code, 200)
        self.assertIn('Participant was updated successfully', response.body)

        # pull it back out and verify
        response = self.get('/ag_edit_participant/', {'email': email})
        self.assertEqual(response.code, 200)
        # check that all relevant user information is rendered on HTML side
        login = db.get_login_by_email(email)
        for key, value in login.items():
            if key == 'zip':
                key = 'zipcode'
            elif key == 'ag_login_id':
                continue
            value = value.decode('utf-8')
            self.assertIn('</td><td><input type="text" name="%s" id="%s" '
                          'value="%s"></td></tr>'
                          % (key, key, xhtml_escape(value)),
                          response.body.decode('utf-8'))

        # wrong ag_login_id
        response = self.post('/ag_edit_participant/',
                             {'email': email,
                              'name': name,
                              'address': address,
                              'city': city,
                              'state': state,
                              'zipcode': zipcode,
                              'country': country,
                              'ag_login_id': 'wrongID'})
        self.assertEqual(response.code, 200)
        self.assertIn('Error Updating Particpant Info', response.body)

        # check missing arguments
        response = self.post('/ag_edit_participant/',
                             {'email': email,
                              'name': name,
                              'city': city,
                              'state': state,
                              'zipcode': zipcode,
                              'country': country,
                              'ag_login_id': ag_login_id})
        self.assertEqual(response.code, 400)
        self.assertIn(('MissingArgumentError: HTTP 400: Bad Request '
                       '(Missing argument address)'), response.body)


if __name__ == "__main__":
    main()

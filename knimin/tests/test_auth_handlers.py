from unittest import main

from tornado.escape import url_escape

from knimin.tests.tornado_test_base import TestHandlerBase


class TestAuthLoginHandler(TestHandlerBase):
    def test_get(self):
        response = self.get('/auth/login/')
        self.assertEqual(response.code, 200)
        # make sure redirect happened properly
        port = self.get_http_port()
        self.assertEqual(response.effective_url, 'http://localhost:%d/' % port)

    def test_post(self):
        # check if unkown users are recognized
        response = self.post('/auth/login/',
                             {'email': 'idontexist',
                              'password': 'password',
                              })
        self.assertIn('>Unknown user<', response.body)

        # check if incorrect password is recognized
        response = self.post('/auth/login/',
                             {'email': 'test',
                              'password': 'wrong',
                              })
        self.assertIn('>Incorrect password<', response.body)

        # check if login with correct credentials is possible
        response = self.post('/auth/login/',
                             {'email': 'test',
                              'password': 'password',
                              })
        port = self.get_http_port()
        self.assertEqual(
            'http://localhost:%d/login/?next=%s' %
            (port, url_escape('/logged_in_index/')),
            response.effective_url
        )

    def test_set_current_user(self):
        # test if new cookie will be set
        response = self.get('/auth/login/')
        self.assertIn('Set-Cookie', response.headers.keys())

        # test that cookie is re-used
        self.mock_login()
        response = self.get('/auth/login/')
        self.assertNotIn('Set-Cookie', response.headers.keys())


class TestAuthLogoutHandler(TestHandlerBase):
    def test_get(self):
        response = self.get('/auth/login/')
        self.assertEqual(response.code, 200)
        # make sure redirect happened properly
        port = self.get_http_port()
        self.assertEqual(response.effective_url, 'http://localhost:%d/' % port)

        # TODO: how can I check that the cookie has been cleared? Or don't I
        # have to, because it's something tornado guarantees or its unit tests?

if __name__ == "__main__":
    main()

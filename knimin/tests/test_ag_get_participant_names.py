from unittest import main

from tornado.escape import url_escape

from knimin.tests.tornado_test_base import TestHandlerBase


class TestAGNamesHandler(TestHandlerBase):
    def test_get_not_authed(self):
        response = self.get('/ag_participant_names/')
        self.assertEqual(response.code, 200)
        port = self.get_http_port()
        self.assertEqual(response.effective_url,
                         'http://localhost:%d/login/?next=%s' %
                         (port, url_escape('/ag_participant_names/')))

    def test_get(self):
        # test if side shows up when properly logged in
        self.mock_login_admin()
        response = self.get('/ag_participant_names/')
        self.assertEqual(response.code, 200)
        port = self.get_http_port()
        self.assertEqual(response.effective_url,
                         'http://localhost:%d/ag_participant_names/' % port)

    def test_post(self):
        self.mock_login_admin()
        response = self.post('/ag_participant_names/', {})
        self.assertEqual(response.code, 200)
        port = self.get_http_port()
        self.assertEqual(response.effective_url,
                         'http://localhost:%d/ag_participant_names/' % port)


class TestAGNamesDLHandler(TestHandlerBase):
    def test_post(self):
        self.mock_login_admin()
        response = self.post('/ag_participant_names/download/', {})
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers['Content-Disposition'],
                         'attachment; filename=participants.zip')


if __name__ == "__main__":
    main()

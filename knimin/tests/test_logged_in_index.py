from unittest import main

from knimin.tests.tornado_test_base import TestHandlerBase


class TestLoggedInIndex(TestHandlerBase):

    def test_get_not_authed(self):
        response = self.get('/logged_in_index/')
        self.assertEqual(response.code, 200)
        self.assertTrue(
            response.effective_url.endswith('?next=%2Flogged_in_index%2F'))

    def test_post_not_authed(self):
        response = self.post('/logged_in_index/', {'foo': 'bar'})
        self.assertEqual(response.code, 403)

    def test_post(self):
        self.mock_login_admin()
        response = self.post('/logged_in_index/', {})
        self.assertEqual(response.code, 200)

    def test_get(self):
        self.mock_login_admin()
        response = self.get('/logged_in_index/')
        self.assertEqual(response.code, 200)
        port = self.get_http_port()
        self.assertEqual(
            'http://localhost:%d/%s' %
            (port, 'logged_in_index/'),
            response.effective_url
        )


if __name__ == '__main__':
    main()

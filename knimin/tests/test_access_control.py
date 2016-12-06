from unittest import main

from tornado.web import HTTPError

from knimin.tests.tornado_test_base import TestHandlerBase
from knimin import db


class TestAccessControlHandler(TestHandlerBase):
    def test_get_not_authed(self):
        response = self.get('/admin/edit/')
        self.assertEqual(response.code, 200)
        self.assertTrue(
            response.effective_url.endswith('?next=%2Fadmin%2Fedit%2F'))

    def test_get(self):
        self.mock_login_admin()
        response = self.get('/admin/edit/')
        self.assertEqual(response.code, 200)
        self.assertIn('Edit User Groups', response.body)

        # test if user is None
        user = 'test'
        response = self.get('/admin/edit/', {'user': user})
        self.assertEqual(response.code, 200)
        all_levels = db.get_access_levels()
        user_levels = db.get_access_levels_user(user)
        for level in all_levels:
            if level in user_levels:
                self.assertIn(('<input type=\'checkbox\' name=\'levels\' value'
                               '="%s" checked> %s<br/>')
                              % (level[0], level[1]), response.body)
            else:
                self.assertIn(('<input type=\'checkbox\' name=\'levels\' value'
                               '="%s" > %s<br/>')
                              % (level[0], level[1]), response.body)

    def test_post_not_authed(self):
        response = self.post('/admin/edit/', {'foo': 'bar'})
        self.assertEqual(response.code, 403)

    def test_post(self):
        self.mock_login_admin()
        response = self.post('/admin/edit/', {'user': 'test',
                                              'levels': [6, 7]})
        self.assertEqual(response.code, 200)
        self.assertIn('Update groups', response.body)

        obs = db.get_access_levels_user('test')
        self.assertEqual(sorted(obs), [[6, 'Search'], [7, 'Admin']])

        # test raising exception
        user = 'notindb'
        db.alter_access_levels('test', [4])
        response = self.post('/admin/edit/', {'user': user,
                                              'levels': [7]})
        self.assertEqual(response.code, 403)
        self.assertRaises(HTTPError)
        self.assertIn(('HTTPError: HTTP 403: Forbidden (User %s does not have '
                       'access level Admin)') % 'test', response.body)


if __name__ == '__main__':
    main()

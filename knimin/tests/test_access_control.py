from unittest import main
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


if __name__ == '__main__':
    main()

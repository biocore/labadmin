from unittest import main

from knimin.tests.tornado_test_base import TestHandlerBase


class TestPMPlateListHandler(TestHandlerBase):
    def test_get_not_authed(self):
        response = self.get(
            '/pm_plate_list/')
        self.assertEqual(response.code, 200)
        self.assertTrue(
            response.effective_url.endswith('?next=%2Fpm_plate_list%2F'))

    def test_get(self):
        # Check that the page renders correctly when no plates are present
        # in the system
        self.mock_login_admin()
        response = self.get('/pm_plate_list/')
        self.assertEqual(response.code, 200)
        # Most of the page is generated on javascript - simply check that is
        # not failing
        self.assertIn('Plate List', response.body)


if __name__ == '__main__':
    main()

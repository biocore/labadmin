from unittest import main

from knimin import db
from knimin.tests.tornado_test_base import TestHandlerBase


class TestAGUpdateGeocodeHandler(TestHandlerBase):
    def test_get_not_authed(self):
        response = self.get('/ag_update_geocode/')
        self.assertEqual(response.code, 200)
        self.assertTrue(response.effective_url.endswith(
            '/login/?next=%2Fag_update_geocode%2F'))

    def test_get(self):
        self.mock_login()
        response = self.get('/ag_update_geocode/')
        self.assertEqual(response.code, 200)

        # check that correct information is printed on HTML page.
        result = db.getGeocodeStats()
        for i in range(len(result)):
            self.assertIn('<td>%s</td><td>%s</td>'
                          % (result[i][0], result[i][1]), response.body)


if __name__ == '__main__':
    main()

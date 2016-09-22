from unittest import main

from knimin import db
from knimin.tests.tornado_test_base import TestHandlerBase


class TestProjectsSummaryHandler(TestHandlerBase):
    def test_get_not_authed(self):
        response = self.get('/projects/summary/')
        self.assertEqual(response.code, 200)
        self.assertTrue(response.effective_url.endswith(
            '/login/?next=%2Fprojects%2Fsummary%2F'))

    def test_get(self):
        self.mock_login()
        response = self.get('/projects/summary/')
        self.assertEqual(response.code, 200)

        # check that correct information is printed on HTML page.
        for project_name in db.getProjectNames():
            num_barcodes = len(db.get_barcodes_for_projects([project_name]))
            self.assertIn('<tr><td>%s</td>' % project_name, response.body)
            self.assertIn('<td>%s</td></tr>' % num_barcodes, response.body)


if __name__ == '__main__':
    main()

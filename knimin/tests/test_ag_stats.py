from unittest import main
from knimin.tests.tornado_test_base import TestHandlerBase


class TestAGStatsHandler(TestHandlerBase):
    def test_get_not_authed(self):
        response = self.get(
            '/ag_stats/')
        self.assertEqual(response.code, 200)
        self.assertTrue(
            response.effective_url.endswith('?next=%2Fag_stats%2F'))

    def test_stats_page(self):
        self.mock_login()
        response = self.get('/ag_stats/')
        self.assertEqual(response.code, 200)
        self.assertIn(
            'Total handout kits</td><td>3609', response.body)
        self.assertIn(
            'Total handout barcodes</td><td>11205', response.body)
        self.assertIn(
            'Total consented participants</td><td>6125', response.body)
        self.assertIn(
            'Total registered kits</td><td>7480', response.body)
        self.assertIn(
            'Total registered barcodes</td><td>', response.body)
        self.assertIn(
            'Total barcodes with results</td><td>4546', response.body)
        self.assertIn(
            'Average age of participants</td><td>48 years', response.body)
        self.assertIn(
            'Total male participants</td><td>2577', response.body)
        self.assertIn(
            'Total female participants</td><td>3107', response.body)

if __name__ == '__main__':
    main()

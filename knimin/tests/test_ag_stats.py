from unittest import main

from knimin.tests.tornado_test_base import TestHandlerBase
from knimin import db


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
        stats = db.getAGStats()
        for item, stat in stats:
            stat = '' if stat is None else stat
            self.assertIn('%s</td><td>%s' % (item, stat), response.body)

if __name__ == '__main__':
    main()

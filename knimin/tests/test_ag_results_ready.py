from unittest import main

from knimin.tests.tornado_test_base import TestHandlerBase
from knimin import db


class TestAGResultsReadyHandler(TestHandlerBase):
    def setUp(self):
        super(TestAGResultsReadyHandler, self).setUp()
        with db._con.cursor() as cur:
            cur.execute("""UPDATE ag.ag_kit_barcodes
                           SET results_ready='N'
                           WHERE barcode='000023299'""")

    def test_post_noauth(self):
        self.mock_login()
        response = self.post('/update_ready/', {})
        self.assertEqual(response.code, 403)
        # it doesn't redirect but i believe that's because this is a POST

    def test_post(self):
        self.mock_login_admin()
        response = self.post('/update_ready/', {})
        self.assertEqual(response.code, 200)
        msg = 'Successfully updated barcodes to results ready status.'
        self.assertIn(msg, response.body)

        with db._con.cursor() as cur:
            cur.execute("""SELECT results_ready
                           FROM ag.ag_kit_barcodes
                           WHERE barcode='000023299'""")
            result = cur.fetchone()[0]
            self.assertEqual(result, 'Y')


if __name__ == '__main__':
    main()

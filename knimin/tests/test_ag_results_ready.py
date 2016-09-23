import tempfile
import os
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

        os.environ["ASYNC_TEST_TIMEOUT"] = "30"
        with db._con.cursor() as cur:
            cur.execute("""SELECT results_ready
                           FROM ag.ag_kit_barcodes
                           WHERE barcode='000023299'""")
            result = cur.fetchone()[0]
            self.assertEqual(result, 'Y')

        # test that error is raised if pdf directory does not exist
        # TODO: refactor for clear message to the user, see issue: #126
        db.config.base_data_dir = 'phantasy_path'
        response = self.post('/update_ready/', {})
        self.assertEqual(response.code, 500)
        self.assertIn('<p>Unknown folder', response.body)
        self.assertRaises(IOError)
        self.assertRaises(Exception)

        # test what happens if no barcode PDFs are available in the system dir
        fakeDir = tempfile.mkdtemp()
        os.makedirs(fakeDir + "/pdfs/")
        db.config.base_data_dir = fakeDir
        response = self.post('/update_ready/', {})
        self.assertEqual(response.code, 200)
        self.assertIn('ERROR: No barcode results available', response.body)

if __name__ == '__main__':
    main()

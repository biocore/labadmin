from unittest import main
from knimin.tests.tornado_test_base import TestHandlerBase
from knimin import db


class AgAddBarcodeKitHandler(TestHandlerBase):
    def test_get_not_authed(self):
        response = self.get('/ag_add_barcode_kit/')
        self.assertEqual(response.code, 200)
        self.assertTrue(
            response.effective_url.endswith('?next=%2Fag_add_barcode_kit%2F'))

    def test_get(self):
        self.mock_login_admin()
        response = self.get('/ag_add_barcode_kit/')
        self.assertEqual(response.code, 200)
        self.assertIn('Add barcode to existing AG kit', response.body)
        self.assertIn('tst_vBKrP', response.body)  # some test kit id

    def test_post_not_authed(self):
        response = self.post('/ag_add_barcode_kit/', {'foo': 'bar'})
        self.assertEqual(response.code, 403)

    def test_post(self):
        self.mock_login_admin()

        kit_id = 'tst_vBKrP'
        # this is the kit uuid for tst_vBKrP
        kit_uuid = 'd8592c74-83f6-2135-e040-8a80115d6401'
        n_barcodes = len(db.get_barcode_info_by_kit_id(kit_uuid))

        response = self.post('/ag_add_barcode_kit/', {'kit_id': kit_id,
                                                      'num_barcodes': 1})
        self.assertEqual(response.code, 200)
        obs_n_barcodes = len(db.get_barcode_info_by_kit_id(kit_uuid))
        self.assertEqual(n_barcodes + 1, obs_n_barcodes)


if __name__ == '__main__':
    main()

from unittest import main
from knimin.tests.tornado_test_base import TestHandlerBase
from knimin import db


class AgAddBarcodeKitHandler(TestHandlerBase):
    def delete_kit(self, ag_kit_id):
        sql = """SELECT barcode
                 FROM ag.ag_kit_barcodes
                 JOIN ag.ag_kit USING (ag_kit_id)
                 WHERE supplied_kit_id = %s"""
        barcodes = db._con.execute_fetchall(sql, [ag_kit_id])

        if barcodes != []:
            barcodes = [x[0] for x in barcodes]
            sql = """DELETE FROM barcodes.project_barcode
                     WHERE barcode IN %s"""
            db._con.execute(sql, [tuple(barcodes)])
            sql = """DELETE FROM ag.ag_kit_barcodes WHERE barcode IN %s"""
            db._con.execute(sql, [tuple(barcodes)])

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
        kit_id = db.ut_get_supplied_kit_id(
            'd8592c74-83f5-2135-e040-8a80115d6401')
        self.assertIn(kit_id, response.body)  # some test kit id

    def test_post_not_authed(self):
        response = self.post('/ag_add_barcode_kit/', {'foo': 'bar'})
        self.assertEqual(response.code, 403)

    def test_post(self):
        self.mock_login_admin()
        ag_login_id = 'd8592c74-83f5-2135-e040-8a80115d6401'
        kit_id = db.ut_get_supplied_kit_id(ag_login_id)

        # this is the kit uuid for tst_vBKrP
        kit_uuid = 'd8592c74-83f6-2135-e040-8a80115d6401'
        n_barcodes = len(db.get_barcode_info_by_kit_id(kit_uuid))

        response = self.post('/ag_add_barcode_kit/', {'kit_id': kit_id,
                                                      'num_barcodes': 1})
        obs_n_barcodes = len(db.get_barcode_info_by_kit_id(kit_uuid))
        self.delete_kit(kit_id)
        self.assertEqual(n_barcodes + 1, obs_n_barcodes)
        self.assertEqual(response.code, 200)


if __name__ == '__main__':
    main()

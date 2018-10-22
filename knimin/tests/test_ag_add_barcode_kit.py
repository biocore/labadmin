from unittest import main
from knimin.tests.tornado_test_base import TestHandlerBase
from knimin import db


class AgAddBarcodeKitHandler(TestHandlerBase):
    def get_assigned_barcodes(self, supplied_kit_id):
        sql = """SELECT barcode
                 FROM ag.ag_kit
                 JOIN ag.ag_kit_barcodes USING (ag_kit_id)
                 WHERE supplied_kit_id = %s"""
        barcodes = db._con.execute_fetchall(sql, [supplied_kit_id])
        if barcodes:
            barcodes = [x[0] for x in barcodes]
        return barcodes

    def revert_add_barcode_kit(self, supplied_kit_id, old_barcodes):
        sql = """SELECT barcode
                 FROM ag.ag_kit
                 JOIN ag.ag_kit_barcodes USING (ag_kit_id)
                 WHERE supplied_kit_id = %s AND barcode NOT IN %s"""
        barcodes = db._con.execute_fetchall(sql, [supplied_kit_id,
                                                  tuple(old_barcodes)])
        if barcodes:
            barcodes = [x[0] for x in barcodes]
            sql = """DELETE FROM barcodes.project_barcode
                     WHERE barcode IN %s"""
            db._con.execute(sql, [tuple(barcodes)])

            sql = """DELETE FROM ag.ag_kit_barcodes
                     WHERE barcode IN %s"""
            db._con.execute(sql, [tuple(barcodes)]),

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
        supplied_kit_id = 'bg_anpbv'
        num_barcodes = 2
        old_barcodes = self.get_assigned_barcodes(supplied_kit_id)
        response = self.post('/ag_add_barcode_kit/',
                             {'kit_id': supplied_kit_id,
                              'num_barcodes': num_barcodes})
        new_barcodes = self.get_assigned_barcodes(supplied_kit_id)
        self.revert_add_barcode_kit(supplied_kit_id, old_barcodes)
        self.assertEqual(len(new_barcodes) - num_barcodes, len(old_barcodes))
        self.assertEqual(response.code, 200)


if __name__ == '__main__':
    main()

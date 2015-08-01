from __future__ import division

from unittest import TestCase, main

from knimin import db
from amgut.lib.util import ag_test_checker


@ag_test_checker()
class DataAccessTests(TestCase):
    def test_get_barcode_metadata(self):
        obs = db.get_barcode_metadata(set(['000000001']))

        self.assertEqual(obs[1]['000000001']['uuid thingy'], 'Unspecified')
        self.assertEqual(obs[1]['000000001']['uuid thingy2'], 'Yes')

        headers = obs[1].values()[0]
        del headers['uuid thingy']
        del headers['uuid thingy2']

        for header in headers:
            self.assertEqual(obs[1]['000000001'][header], 'NA')

    def test_get_used_kit_ids(self):
        obs = db.get_used_kit_ids()
        exp = {'test', 'test_ha', '1111'}
        self.assertEqual(obs, exp)

    def test_create_project(self):
        with self.assertRaises(ValueError):
            db.create_project("American Gut Project")
        with self.assertRaises(ValueError):
            db.create_project("    ")

        db.create_project("New Test Project")
        obs = db._con.execute_fetchall("SELECT * from project")
        exp = [[1, "American Gut Project"], [2, "New Test Project"]]
        self.assertEqual(obs, exp)

    def test_get_unassigned_barcodes(self):
        with self.assertRaises(ValueError):
            db.get_unassigned_barcodes(999999999)

        obs = db.get_unassigned_barcodes()
        self.assertEqual(obs, [])
        barcodes = db.create_barcodes(3)
        obs = db.get_unassigned_barcodes()
        self.assertEqual(obs, barcodes)
        obs = db.get_unassigned_barcodes(1)
        self.assertEqual(obs, [barcodes[0]])


    def test_create_barcodes(self):
        con = db._con
        sql_bc = "SELECT barcode FROM barcode"
        bc = [['000000001'], ['000000002'], ['000000003'], ['000000004'],
              ['000006616'], ['000010860']]

        barcodes = db.create_barcodes(3)
        self.assertEqual(barcodes, ['000010861', '000010862', '000010863'])

        bc.extend([['000010861'], ['000010862'], ['000010863']])
        obs = con.execute_fetchall(sql_bc)
        self.assertItemsEqual(obs, bc)

    def test_create_ag_kits(self):
        with self.assertRaises(ValueError):
            db.create_ag_kits([(1, 9999999999)])
        db.create_barcodes(15)
        kits = db.create_ag_kits([(1, 2), (5, 2)])

        obs = db._con.execute_fetchall("SELECT * from ag.ag_handout_kits")
        self.assertEqual(len(obs), 5)

        obs = db._con.execute_fetchall("SELECT * from ag.ag_handout_barcodes")
        self.assertEqual(len(obs), 15)

    def test_remaining_barcodes(self):
        with self.assertRaises(ValueError):
            db.remaining_barcodes(999999999999)

        barcodes = db.remaining_barcodes()
        exp = []
        self.assertEqual(barcodes, exp)

        db.create_barcodes(5)

        barcodes = db.remaining_barcodes()
        exp = ['000010861', '000010862', '000010863', '000010864', '000010865']
        self.assertEqual(barcodes, exp)

        barcodes = db.remaining_barcodes(2)
        self.assertEqual(barcodes, ['000010861', '000010862'])


if __name__ == '__main__':
    main()

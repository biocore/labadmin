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

        db.create_project("New Test Project")
        obs = db._con.execute_fetchall("SELECT * from project")
        exp = [[1, "American Gut Project"], [2, "New Test Project"]]
        self.assertEqual(obs, exp)

    def test_create_barcodes(self):
        with self.assertRaises(ValueError):
            db.create_barcodes(29)
        with self.assertRaises(ValueError):
            db.create_barcodes(29, ["NOTINDB"])

        db.create_project("New Test Project")
        con = db._con
        sql_bc = "SELECT barcode FROM barcode"
        bc = [['000000001'], ['000000002'], ['000000003'], ['000000004'],
              ['000006616'], ['000010860']]
        sql_bc_proj = "SELECT * FROM project_barcode"
        bc_proj = [[1, '000000001'], [1, '000006616'], [1, '000010860']]
        db.create_barcodes(3, ["American Gut Project", "New Test Project"])
        bc.extend([['000010861'], ['000010862'], ['000010863']])
        obs = con.execute_fetchall(sql_bc)
        self.assertItemsEqual(obs, bc)
        bc_proj.extend([[1, '000010861'], [1, '000010862'], [1, '000010863'],
                        [2, '000010861'], [2, '000010862'], [2, '000010863']])
        obs = con.execute_fetchall(sql_bc_proj)
        self.assertItemsEqual(obs, bc_proj)


if __name__ == '__main__':
    main()

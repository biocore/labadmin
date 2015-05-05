from __future__ import division

from unittest import TestCase, main

from knimin import db


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


if __name__ == '__main__':
    main()

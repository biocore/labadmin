from unittest import TestCase, main
from knimin.lib.geocoder import Location, geocode
import random
from knimin.lib.configuration import config
import string


class TestGeocode(TestCase):
    def test_geocode_nonmock(self):
        obs = geocode('9500 Gilman Dr, La Jolla, CA')
        exp = Location('9500 Gilman Dr, La Jolla, CA', 32.8794239,
                       -117.2369135, 105, 'San Diego', 'California',
                       '92093', 'USA')
        self.assertEqual(obs.input, exp.input)
        if not config.attempt_geocode:
            # if we're not attempting to geocode then skip this
            return

        self.assertAlmostEqual(obs.lat, exp.lat, delta=0.1)
        self.assertAlmostEqual(obs.long, exp.long, delta=0.1)
        # self.assertIsInstance(obs.elev, int)
        self.assertEqual(obs.city, exp.city)
        self.assertEqual(obs.state, exp.state)
        self.assertEqual(obs.postcode, exp.postcode)
        self.assertEqual(obs.country, exp.country)

        # Test for unicode
        obs = geocode('Erlangengatan 12, Sweden')
        exp = Location('Erlangengatan 12, Sweden', 59.36121550000001,
                       16.4908829, 38.21769714355469, 'Eskilstuna',
                       u'S\xf6dermanland County', '63227', 'Sweden')
        self.assertAlmostEqual(obs.lat, exp.lat, delta=0.1)
        self.assertAlmostEqual(obs.long, exp.long, delta=0.1)
        self.assertEqual(obs.city, exp.city)
        self.assertEqual(obs.state, exp.state)
        self.assertEqual(obs.postcode, exp.postcode)
        self.assertEqual(obs.country, exp.country)

    def test_geocode_bad_address(self):
        # do something random to avoid a timeout
        loc_name = ''.join([random.choice(string.ascii_letters + " ,")
                            for i in range(50)])
        obs = geocode(loc_name)
        exp = Location(loc_name, None, None, None, None, None, None, None)
        self.assertEqual(obs, exp)


if __name__ == '__main__':
    main()

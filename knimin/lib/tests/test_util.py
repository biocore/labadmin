from unittest import TestCase, main
from StringIO import StringIO
from random import seed
from socket import gaierror

from knimin.lib.util import (combine_barcodes, categorize_age, categorize_etoh,
                             categorize_bmi, correct_bmi, correct_age,
                             make_valid_kit_ids, get_printout_data, fetch_url)


__author__ = "Adam Robbins-Pianka"
__copyright__ = "Copyright 2009-2015, QIIME Web Analysis"
__credits__ = ["Adam Robbins-Pianka"]
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = ["Adam Robbins-Pianka"]
__email__ = "adam.robbinspianka@colorado.edu"
__status__ = "Development"


class UtilTests(TestCase):
    def test_combine_barcodes_inputfile_only(self):
        infile = StringIO("123\n"
                          "456\n"
                          "789")
        exp = {"123", "456", "789"}
        obs = combine_barcodes(input_file=infile)
        self.assertEqual(obs, exp)

    def test_combine_barcodes_cli_only(self):
        barcodes = ("123", "456", "789")
        obs = combine_barcodes(cli_barcodes=barcodes)
        exp = {"123", "456", "789"}
        self.assertEqual(obs, exp)

    def test_combine_barcodes_cli_and_inputfile(self):
        cli_barcodes = ("123", "456", "789")
        infile = StringIO("123\n"
                          "456\n"
                          "101112")
        exp = {"123", "456", "789", "101112"}
        obs = combine_barcodes(cli_barcodes=cli_barcodes, input_file=infile)
        self.assertEqual(obs, exp)

    def test_combine_barcodes_cli_and_inputfile_none(self):
        exp = set()
        obs = combine_barcodes()
        self.assertEqual(obs, exp)

    def test_categorize_age(self):
        self.assertEqual('Unspecified', categorize_age(-2))
        self.assertEqual('baby', categorize_age(0))
        self.assertEqual('baby', categorize_age(2.9))
        self.assertEqual('child', categorize_age(3))
        self.assertEqual('child', categorize_age(12.9))
        self.assertEqual('teen', categorize_age(13))
        self.assertEqual('teen', categorize_age(19.9))
        self.assertEqual('20s', categorize_age(20))
        self.assertEqual('20s', categorize_age(29.9))
        self.assertEqual('30s', categorize_age(30))
        self.assertEqual('30s', categorize_age(39.9))
        self.assertEqual('40s', categorize_age(40))
        self.assertEqual('40s', categorize_age(49.9))
        self.assertEqual('50s', categorize_age(50))
        self.assertEqual('50s', categorize_age(59.9))
        self.assertEqual('60s', categorize_age(60))
        self.assertEqual('60s', categorize_age(69.9))
        self.assertEqual('70+', categorize_age(70))
        self.assertEqual('70+', categorize_age(122))
        self.assertEqual('Unspecified', categorize_age(123))
        self.assertEqual('Unspecified', categorize_age(123564))
        self.assertEqual('Unspecified', categorize_age('Unspecified'))

    def test_categorize_etoh(self):
        with self.assertRaises(TypeError):
            categorize_etoh(12)

        self.assertEqual('No', categorize_etoh('Never'))
        self.assertEqual('Yes', categorize_etoh('Every day'))
        self.assertEqual('Yes', categorize_etoh('Rarely (once a month)'))
        self.assertEqual('Unspecified', categorize_etoh('Unspecified'))

    def test_correct_bmi(self):
        self.assertEqual('Unspecified', correct_bmi(-2))
        self.assertEqual('Unspecified', correct_bmi(7))
        self.assertEqual('Unspecified', correct_bmi(80))
        self.assertEqual('Unspecified', correct_bmi(200))
        self.assertEqual('8.00', correct_bmi(8))
        self.assertEqual('79.00', correct_bmi(79))
        self.assertEqual('Unspecified', correct_bmi('Unspecified'))

    def test_categorize_bmi(self):
        self.assertEqual('Unspecified', categorize_bmi(-2))
        self.assertEqual('Unspecified', categorize_bmi(7.9))
        self.assertEqual('Underweight', categorize_bmi(8))
        self.assertEqual('Underweight', categorize_bmi(18.4))
        self.assertEqual('Normal', categorize_bmi(18.5))
        self.assertEqual('Normal', categorize_bmi(24.9))
        self.assertEqual('Overweight', categorize_bmi(25))
        self.assertEqual('Overweight', categorize_bmi(29.9))
        self.assertEqual('Obese', categorize_bmi(30))
        self.assertEqual('Obese', categorize_bmi(79.9))
        self.assertEqual('Unspecified', categorize_bmi(80))
        self.assertEqual('Unspecified', categorize_bmi(210))
        self.assertEqual('Unspecified', categorize_bmi('Unspecified'))

    def test_correct_age(self):
        self.assertEqual('Unspecified', correct_age('Unspecified', 56, 5.36,
                                                    'Every day'))
        self.assertEqual('Unspecified', correct_age(18, 'Unspecified', 5.36,
                                                    'Every day'))
        self.assertEqual('Unspecified', correct_age(18, 56, 'Unspecified',
                                                    'Every day'))
        self.assertEqual('Unspecified', correct_age(18, 56, 5.36,
                                                    'Unspecified'))
        self.assertEqual('Unspecified', correct_age('Unspecified',
                                                    'Unspecified',
                                                    5.36,
                                                    'Every day'))
        self.assertEqual('Unspecified', correct_age('Unspecified',
                                                    56,
                                                    'Unspecified',
                                                    'Every day'))
        self.assertEqual('Unspecified', correct_age('Unspecified',
                                                    56,
                                                    5.36,
                                                    'Unspecified'))
        self.assertEqual('Unspecified', correct_age('Unspecified',
                                                    'Unspecified',
                                                    'Unspecified',
                                                    'Unspecified'))
        self.assertEqual('Unspecified', correct_age(-2, 56, 5.36, 'Every day'))
        self.assertEqual('Unspecified', correct_age(123, 56, 5.36,
                                                    'Every day'))
        self.assertEqual('Unspecified', correct_age(2, 92.0, 5.36,
                                                    'Every day'))
        self.assertEqual('Unspecified', correct_age(2, 56, 17, 'Every day'))
        self.assertEqual('Unspecified', correct_age(2, 56, 5.36, 'Ever'))
        self.assertEqual(2.0, correct_age(2, 56, 5.36, 'Never'))

    def test_make_valid_kit_ids(self):
        # fix random seed
        seed(7)
        existing_kit_ids = set(['knut_fxwz', 'knut_sjwg', 'knut_xuee'])

        # positive test
        result = make_valid_kit_ids(3, existing_kit_ids, 5, 'knut')
        self.assertEqual(result, ['knut_hdrb', 'knut_pjbn', 'knut_akbc'])

        # test exceptions
        self.assertRaisesRegexp(ValueError,
                                "Tag must be 4 or less characters",
                                make_valid_kit_ids, 3, existing_kit_ids, 5,
                                'toolongtag')
        self.assertRaisesRegexp(ValueError,
                                "More kits requested than possible kit ID com",
                                make_valid_kit_ids, 23**8, existing_kit_ids, 5,
                                'knut')

        # test exclusion of already existing ids
        existing_id = 'knut_kwcf'
        result = make_valid_kit_ids(3, set([existing_id]), 5, 'knut')
        self.assertEqual(result, ['knut_ryqk', 'knut_zbwg', 'knut_dchv'])
        self.assertNotIn(existing_id, result)

    def test_get_printout_data(self):
        kitinfo = [["xxx_pggwy", "96812490", "23577",
                    ["000033914", "000033915"]],
                   ["xxx_drcrv", "33422033", "56486",
                    ["000033916", "000033917"]]]
        result = get_printout_data(kitinfo)
        for kit in kitinfo:
            self.assertIn("Sample Barcodes:\t%s" % ', '.join(kit[3]), result)
            self.assertIn("Kit ID:\t\t%s" % kit[0], result)
            self.assertIn("Password:\t\t%s" % kit[1], result)
        self.assertIn('http://www.microbio.me/AmericanGut', result)

        # test proper line break for lengthy barcode lists
        kitinfo = [["xxx_pggwy", "96812490", "23577",
                    ["000033914", "000033915", "000033916", "000033917",
                     "100033914", "100033915", "100033916", "100033917"]]]
        result = get_printout_data(kitinfo)
        for kit in kitinfo:
            self.assertIn("Sample Barcodes:\t%s" % ', '.join(kit[3][:5]),
                          result)
            self.assertIn("\t\t\t%s" % ', '.join(kit[3][5:]), result)

    def test_fetch_url(self):
        # test unknown address
        self.assertRaisesRegexp(gaierror,
                                'Name or service not known',
                                fetch_url,
                                'http://askdfjhSKJDF.com')

        # test positive result
        self.assertTrue(isinstance(fetch_url('http://www.google.com'),
                                   StringIO))

if __name__ == '__main__':
    main()

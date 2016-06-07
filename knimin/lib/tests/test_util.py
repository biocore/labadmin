from unittest import TestCase, main
from StringIO import StringIO

from knimin.lib.util import (combine_barcodes, categorize_age, categorize_etoh,
                             categorize_bmi, correct_bmi)


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


if __name__ == '__main__':
    main()

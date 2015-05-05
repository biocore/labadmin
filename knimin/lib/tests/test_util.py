from unittest import TestCase, main
from StringIO import StringIO

from knimin.lib.util import combine_barcodes


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


if __name__ == '__main__':
    main()

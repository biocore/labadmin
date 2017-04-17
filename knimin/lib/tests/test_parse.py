import unittest
import os

from knimin.lib.parse import parse_echo


class EchoParserTests(unittest.TestCase):
    def setUp(self):
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        self.real = os.path.join(base, 'echo.csv')
        self.noheader = os.path.join(base, 'noheader.csv')
        self.noexceptions = os.path.join(base, 'noexceptions.csv')
        self.nodetails = os.path.join(base, 'nodetails.csv')

    def test_missing_header(self):
        with open(self.noheader) as fp:
            data = fp.read()
            with self.assertRaisesRegexp(ValueError, 'header'):
                parse_echo(data)

    def test_missing_exceptions(self):
        with open(self.noexceptions) as fp:
            data = fp.read()
            with self.assertRaisesRegexp(ValueError, '[EXCEPTIONS]'):
                parse_echo(data)

    def test_missing_details(self):
        with open(self.nodetails) as fp:
            data = fp.read()
            with self.assertRaisesRegexp(ValueError, '[DETAILS]'):
                parse_echo(data)


if __name__ == '__main__':
    unittest.main()

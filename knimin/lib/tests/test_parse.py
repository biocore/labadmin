import unittest
import os

import pandas as pd
import pandas.util.testing as pdt

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

    def test_valid(self):
        exp_exceptions = pd.DataFrame([['gDNA[2]', None, '384PP_AQ_BP2_HT',
                                        'G10', 'Normalized DNA Destination[1]',
                                        None, 'Greiner_384PS_781096','G10','0',
                                        '0', None, None, '802.5', '0',
                                        '60.717', '-0.126', 'Percent',
                                        'Glycerol',
                                        'MM0201004: Inconsistent fluid level']],  # noqa
                                      columns=['Source Plate Name',
                                               'Source Plate Barcode',
                                               'Source Plate Type',
                                               'Source Well',
                                               'Destination Plate Name',
                                               'Destination Plate Barcode',
                                               'Destination Plate Type',
                                               'Destination Well',
                                               'Destination Well X Offset',
                                               'Destination Well Y Offset',
                                               'Sample ID',
                                               'Sample Name',
                                               'Transfer Volume',
                                               'Actual Volume',
                                               'Current Fluid Volume',
                                               'Fluid Composition',
                                               'Fluid Units',
                                               'Fluid Type',
                                               'Transfer Status'])

        # just using the "head"
        exp_details = pd.DataFrame([('PP Water[1]', None, '384PP_AQ_BP2_HT',
                                     'B13', 'Normalized DNA Destination[1]',
                                     None, 'Greiner_384PS_781096', 'B13', '0',
                                     '0', None, None, '3337.5', '3337.5',
                                     '44.776', '-0.126', 'Percent', 'Glycerol',
                                     None),
                                    ('PP Water[1]', None, '384PP_AQ_BP2_HT',
                                     'A13', 'Normalized DNA Destination[1]',
                                     None, 'Greiner_384PS_781096', 'A13', '0',
                                     '0', None, None, '3415', '3415', '45.637',
                                     '-0.126', 'Percent', 'Glycerol', None),
                                    ('PP Water[1]', None, '384PP_AQ_BP2_HT',
                                     'C13', 'Normalized DNA Destination[1]',
                                     None, 'Greiner_384PS_781096', 'C13', '0',
                                     '0', None, None, '3045', '3045', '45.92',
                                     '-0.126', 'Percent', 'Glycerol', None),
                                    ('PP Water[1]', None, '384PP_AQ_BP2_HT',
                                     'D13', 'Normalized DNA Destination[1]',
                                     None, 'Greiner_384PS_781096', 'D13', '0',
                                     '0', None, None, '3265', '3265', '45.728',
                                     '-0.126', 'Percent', 'Glycerol', None),
                                    ('PP Water[1]', None, '384PP_AQ_BP2_HT',
                                     'E13', 'Normalized DNA Destination[1]',
                                     None, 'Greiner_384PS_781096', 'E13', '0',
                                     '0', None, None, '3237.5', '3237.5',
                                     '45.658', '-0.126', 'Percent', 'Glycerol',
                                     None)],
                                   columns=['Source Plate Name',
                                            'Source Plate Barcode',
                                            'Source Plate Type',
                                            'Source Well',
                                            'Destination Plate Name',
                                            'Destination Plate Barcode',
                                            'Destination Plate Type',
                                            'Destination Well',
                                            'Destination Well X Offset',
                                            'Destination Well Y Offset',
                                            'Sample ID',
                                            'Sample Name',
                                            'Transfer Volume',
                                            'Actual Volume',
                                            'Current Fluid Volume',
                                            'Fluid Composition',
                                            'Fluid Units',
                                            'Fluid Type',
                                            'Transfer Status'])
        with open(self.real) as fp:
            data = fp.read()
            obs_exceptions, obs_details = parse_echo(data)

        pdt.assert_frame_equal(obs_exceptions, exp_exceptions)
        pdt.assert_frame_equal(obs_details.head(5), exp_details)


if __name__ == '__main__':
    unittest.main()

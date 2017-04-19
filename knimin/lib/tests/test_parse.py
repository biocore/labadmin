# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from unittest import TestCase, main
import os

import numpy as np
import numpy.testing as npt
import pandas as pd
import pandas.util.testing as pdt

from knimin.lib.parse import (parse_qpcr_object, parse_plate_reader_output,
                              parse_echo, parse_plate_reader_output_multiple)


class TestParse(TestCase):
    def test_parse_plate_reader_output(self):
        obs = parse_plate_reader_output(PLATE_READER_EXAMPLE)
        exp = np.asarray(
            [[0.154, 0.680, 0.440, 0.789, 0.778, 3.246, 1.729, 0.436, 0.152,
              2.971, 3.280, 0.062, 5.396, 0.068, 0.632, 2.467, 1.718, 0.285,
              1.950, 2.507, 1.386, 2.492, 7.016, 0.083],
             [0.064, 15.243, 0.156, 2.325, 13.411, 0.480, 15.444, 3.464,
              15.465, 1.597, 1.569, 1.810, 3.870, 1.156, 5.219, 0.038, 0.987,
              7.321, 0.061, 2.347, 3.436, 2.494, 0.991, 1.560],
             [0.070, 0.335, 1.160, 0.052, 0.511, 0.087, 0.746, 0.035, 0.070,
              0.395, 2.708, 0.035, 1.060, 0.041, 1.061, 0.836, 0.876, 1.456,
              0.876, 2.330, 1.773, 0.433, 2.047, 0.071],
             [0.058, 3.684, 0.426, 0.957, 1.564, 1.935, 2.930, 1.175, 45.111,
              5.490, 4.659, 16.602, 2.911, 4.096, 2.892, 0.084, 2.534, 1.820,
              1.132, 0.500, 2.071, 0.761, 0.824, 1.364],
             [0.045, 0.231, 0.246, 2.600, 0.658, 5.007, 1.093, 1.410, 0.089,
              1.810, 0.251, 0.034, 2.126, 0.065, 0.893, 2.682, 1.226, 0.980,
              4.734, 2.122, 1.469, 1.213, 0.057, 0.052],
             [0.051, 1.091, 0.117, 0.454, 4.189, 2.823, 1.128, 0.219, 9.575,
              1.829, 3.506, 7.271, 7.841, 0.504, 1.467, 0.130, 27.226, 3.093,
              2.747, 1.087, 4.533, 16.917, 1.588, 6.551],
             [0.037, 0.067, 0.770, 0.490, 0.711, 0.565, 0.922, 0.063, 0.841,
              0.115, 0.046, 0.044, 6.361, 0.051, 0.330, 1.742, 0.105, 0.756,
              0.320, 3.696, 5.029, 5.671, 0.056, 0.060],
             [0.050, 0.234, 3.427, 14.636, 1.814, 5.541, 3.395, 6.570, 3.094,
              5.384, 2.031, 5.400, 16.724, 0.207, 1.038, 0.072, 0.964, 4.050,
              4.767, 7.891, 0.340, 1.730, 12.827, 1.946],
             [0.064, 0.137, 0.843, 0.633, 0.119, 2.592, 5.804, 0.999, 0.511,
              0.304, 0.353, 0.053, 2.645, 0.070, 0.071, 0.991, 0.286, 3.576,
              1.993, 6.539, 8.736, 6.910, 0.070, 0.064],
             [0.079, 1.160, 1.053, 3.178, 7.796, 2.323, 0.992, 0.760, 2.181,
              2.739, 3.232, 1.166, 3.257, 0.680, 1.955, 0.088, 0.586, 7.026,
              0.306, 8.078, 2.375, 10.286, 8.571, 0.528],
             [0.081, 1.718, 2.069, 0.863, 0.197, 3.352, 0.132, 0.124, 0.145,
              0.628, 0.060, 0.060, 2.612, 0.072, 0.177, 0.170, 1.261, 0.464,
              4.059, 2.724, 3.449, 0.252, 0.073, 0.073],
             [0.080, 1.128, 3.536, 38.352, 1.361, 1.293, 0.803, 0.456, 9.873,
              6.525, 24.843, 1.052, 0.084, 1.034, 1.392, 0.066, 0.598, 3.002,
              1.785, 8.376, 0.882, 0.272, 4.079, 11.586],
             [0.086, 0.548, 0.625, 0.557, 0.601, 0.481, 0.449, 0.643, 52.291,
              1.978, 0.068, 0.209, 11.138, 0.070, 0.324, 0.492, 5.913, 0.963,
              0.843, 8.087, 0.647, 0.664, 0.080, 0.090],
             [0.099, 8.458, 3.391, 17.942, 7.709, 3.955, 2.891, 7.681, 0.262,
              3.994, 1.309, 6.377, 1.272, 0.638, 5.323, 5.794, 0.868, 1.021,
              1.523, 0.662, 3.279, 1.980, 4.208, 1.794],
             [0.763, 0.615, 0.352, 0.745, 1.383, 0.546, 0.247, 0.504, 5.138,
              0.116, 0.167, 0.062, 0.573, 0.096, 0.227, 3.399, 7.361, 2.376,
              3.790, 3.389, 0.906, 6.238, 0.112, 0.098],
             [0.105, 0.505, 4.985, 0.450, 5.264, 15.071, 6.145, 10.357, 1.128,
              4.151, 9.280, 8.581, 1.343, 2.416, 0.671, 9.347, 0.836, 5.312,
              0.719, 0.622, 4.342, 4.166, 0.633, 11.101]])
        npt.assert_almost_equal(obs, exp)

    def test_parse_qpcr_object(self):
        obs = parse_qpcr_object(QPCR_OBJECT)
        exp = [
            [10.73, 7.3, 6.77, 6.66, 7.44, 12.1, 6.63, 6.53, 9.32, 6.34, 6.05,
             7.77, 11.47, 15.52, 12.6, 11.18, 21.37, 15.07, 11.45, 18.32,
             12.68, 11.52, 11.34, 24.32],
            [6.61, 6.27, 12.11, 7.15, 6.21, 7.31, 6.87, 5.98, 6.43, 6.59, 6.5,
             8.07, 7.23, 7.82, 10.09, 15.68, np.nan, np.nan, 14.78, 11.54,
             np.nan, np.nan, np.nan, np.nan]]
        npt.assert_almost_equal(obs, exp)

        # errrors

        with self.assertRaises(ValueError) as ctx:
            parse_qpcr_object(QPCR_OBJECT_ERROR1)
        self.assertEqual(
            ctx.exception.message, "The 'Cp' and 'Pos' headers "
            "are required. The ones present are: [u'Include' u'Color' u'Pos' "
            "u'Name' u'CpError' u'Concentration' u'Standard'\n u'Status']")

        with self.assertRaises(ValueError) as ctx:
            parse_qpcr_object(QPCR_OBJECT_ERROR2)
        self.assertEqual(
            ctx.exception.message, "The 'Cp' and 'Pos' headers "
            "are required. The ones present are: [u'Include' u'Color' "
            "u'PosError' u'Name' u'Cp' u'Concentration' u'Standard'\n "
            "u'Status']")


class EchoParserTests(TestCase):
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
                                        None, 'Greiner_384PS_781096', 'G10',
                                        '0', '0', None, None, '802.5', '0',
                                        '60.717', '-0.126', 'Percent',
                                        'Glycerol',
                                        'MM0201004: Inconsistent fluid level']], # noqa
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


class QubitParserTests(TestCase):
    def setUp(self):
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        self.real = os.path.join(base, 'qubit.txt')
        self.error1 = os.path.join(base, 'qubit-error1.txt')
        self.error2 = os.path.join(base, 'qubit-error2.txt')

    def test_parse_plate_reader_output_multiple(self):
        with open(self.real) as fp:
            data = fp.read()
        obs = parse_plate_reader_output_multiple(data)
        exp = [
            np.array([
                [145.598, 150.047, 144.486, 192.314, 185.64, 66.627,
                 193.426, 97.215, 166.731, 123.909, 194.538, 175.63],
                [141.149, 204.549, 186.752, 192.314, 120.016, 115.567,
                 124.465, 195.094, 177.298, 147.823, 165.063, 193.426],
                [215.671, 212.891, 182.303, 208.998, 130.583, 184.528,
                 130.027, 110.006, 187.865, 189.533, 246.259, 187.865],
                [157.277, 203.992, 142.818, 168.956, 166.731, 138.369,
                 132.251, 121.685, 97.215, 172.849, 146.155, 108.337],
                [117.792, 168.956, 158.946, 157.277, 190.645, 186.196,
                 178.41, 162.839, 165.063, 180.635, 151.16, 182.859],
                [162.839, 210.11, 219.008, 117.236, 79.418, 125.578,
                 171.737, 190.645, 139.481, 210.11, 196.763, 149.491],
                [175.073, 196.763, 63.847, 208.998, 176.742, 204.549,
                 170.624, 185.084, 192.314, 198.987, 122.797, 96.102],
                [183.972, 202.88, 101.664, 129.471, 200.656, 133.92,
                 125.578, 206.773, 191.201, 199.543, 17.131, 28.254]]),
            np.array([
                [145.042, 78.306, 177.854, 88.317, 173.961, 120.572,
                 174.517, 176.186, 124.465, 76.082, 156.165, 78.862],
                [7.121, 177.854, 195.65, 190.645, 168.956, 139.481,
                 119.46, 83.311, 139.481, 219.564, 169.512, 166.175],
                [202.324, 102.22, 187.865, 154.497, 150.604, 220.12,
                 202.88, 101.108, 64.403, 147.267, 167.844, 133.92],
                [163.395, 119.46, 164.507, 166.175, 152.828, 105.557,
                 180.635, 138.925, 52.168, 153.384, 61.622, 66.627],
                [198.987, 160.614, 46.05, 118.904, 76.082, 150.604,
                 120.016, 168.956, 171.737, 146.711, 133.92, 128.358],
                [84.424, 104.444, 111.118, 192.87, 178.966, 118.348,
                 58.285, 77.194, 141.149, 63.291, 176.742, 43.826],
                [92.21, 89.429, 84.98, 110.562, 61.622, 85.536,
                 81.087, 146.155, 103.332, 153.384, 137.256, 72.745],
                [133.92, 116.679, 163.395, 101.664, 124.465, 89.429,
                 95.546, 196.207, 17.688, 10.458, 32.147, 37.152]]),
            np.array([
                [3.228, 11.014, 11.014, 44.382, 28.254, 33.815,
                 10.458, 43.27, 37.708, 4.897, 5.453, 7.677],
                [8.233, 18.8, 8.789, 23.249, 13.239, 26.03,
                 11.57, 7.121, 120.572, 6.009, 9.902, 32.147],
                [7.121, 7.677, 19.356, 82.755, 1.56, 8.789,
                 20.468, 10.458, 71.633, 22.693, 12.126, 9.346],
                [6.009, 26.586, 15.463, 87.76, 22.137, 18.244,
                 13.239, 111.118, 38.265, 14.907, 22.693, 6.565],
                [9.346, 7.677, 8.789, 70.52, 8.789, 61.622,
                 8.233, 129.471, 32.703, 10.458, 9.902, 9.902],
                [9.902, 12.682, 19.912, 82.199, 24.917, 11.57,
                 17.131, 68.852, 70.52, 24.917, 11.57, 9.902],
                [11.014, 66.627, 61.622, 62.178, 73.301, 26.03,
                 57.729, 75.526, 37.708, 7.121, 13.239, 8.789],
                [18.8, 98.883, 47.163, 84.424, 69.408, 41.601,
                 100.552, 56.061, 10.458, 14.351, 12.682, 15.463]])]
        npt.assert_array_equal(obs, exp)

        # testing errors
        with open(self.error1) as fp:
            data = fp.read()
        with self.assertRaises(ValueError) as ctx:
            parse_plate_reader_output_multiple(data)
        self.assertEqual(
            ctx.exception.message, "We expect 14 columns in all lines but "
            "line 4 of frame 2 only has 12: ['D', '39.377', '76.638', "
            "'129.471', '168.956', '175.630', '115.011', '185.640', "
            "'161.726', '77.194', '198.431', '93.878']")

        with open(self.error2) as fp:
            data = fp.read()
        with self.assertRaises(ValueError) as ctx:
            parse_plate_reader_output_multiple(data)
        self.assertEqual(
            ctx.exception.message, "Wrong row value: G, it should be: B, "
            "on line 2, of frame 1")


QPCR_OBJECT_ERROR1 = """Experiment: Knight_kapa_qpcr  Selected Filter: \
SYBR Green I / HRM Dye (465-510),,,,,,,
Include,Color,Pos,Name,CpError,Concentration,Standard,Status
True,255,A1,Sample 1,10.73,,0,
"""

QPCR_OBJECT_ERROR2 = """Experiment: Knight_kapa_qpcr  Selected Filter: \
SYBR Green I / HRM Dye (465-510),,,,,,,
Include,Color,PosError,Name,Cp,Concentration,Standard,Status
True,255,A1,Sample 1,10.73,,0,
"""

QPCR_OBJECT = """Experiment: Knight_kapa_qpcr  Selected Filter: \
SYBR Green I / HRM Dye (465-510),,,,,,,
Include,Color,Pos,Name,Cp,Concentration,Standard,Status
True,255,A1,Sample 1,10.73,,0,
True,255,A2,Sample 2,7.3,,0,
True,255,A3,Sample 3,6.77,,0,
True,255,A4,Sample 4,6.66,,0,
True,255,A5,Sample 5,7.44,,0,
True,255,A6,Sample 6,12.1,,0,
True,255,A7,Sample 7,6.63,,0,
True,255,A8,Sample 8,6.53,,0,
True,255,A9,Sample 9,9.32,,0,
True,255,A10,Sample 10,6.34,,0,
True,255,A11,Sample 11,6.05,,0,
True,255,A12,Sample 12,7.77,,0,
True,255,A13,Sample 13,11.47,,0,
True,255,A14,Sample 14,15.52,,0,
True,255,A15,Sample 15,12.6,,0,
True,255,A16,Sample 16,11.18,,0,
True,255,A17,Sample 17,21.37,,0,
True,255,A18,Sample 18,15.07,,0,
True,255,A19,Sample 19,11.45,,0,
True,255,A20,Sample 20,18.32,,0,
True,255,A21,Sample 21,12.68,,0,
True,255,A22,Sample 22,11.52,,0,
True,255,A23,Sample 23,11.34,,0,
True,255,A24,Sample 24,24.32,,0,
True,255,B1,Sample 25,6.61,,0,
True,255,B2,Sample 26,6.27,,0,
True,255,B3,Sample 27,12.11,,0,
True,255,B4,Sample 28,7.15,,0,
True,255,B5,Sample 29,6.21,,0,
True,255,B6,Sample 30,7.31,,0,
True,255,B7,Sample 31,6.87,,0,
True,255,B8,Sample 32,5.98,,0,
True,255,B9,Sample 33,6.43,,0,
True,255,B10,Sample 34,6.59,,0,
True,255,B11,Sample 35,6.5,,0,
True,255,B12,Sample 36,8.07,,0,
True,255,B13,Sample 37,7.23,,0,
True,255,B14,Sample 38,7.82,,0,
True,255,B15,Sample 39,10.09,,0,
True,255,B16,Sample 40,15.68,,0,
True,65280,B17,Sample 41,,,0,
True,65280,B18,Sample 42,,,0,
True,255,B19,Sample 43,14.78,,0,
True,255,B20,Sample 44,11.54,,0,
"""

PLATE_READER_EXAMPLE = """Curve0.5\tY=A*X+B\t1.15E+003\t99.8\t0.773\t?????\n
0.154\t0.680\t0.440\t0.789\t0.778\t3.246\t1.729\t0.436\t0.152\t2.971\t3.280\t\
0.062\t5.396\t0.068\t0.632\t2.467\t1.718\t0.285\t1.950\t2.507\t1.386\t2.492\t\
7.016\t0.083\n
0.064\t15.243\t0.156\t2.325\t13.411\t0.480\t15.444\t3.464\t15.465\t1.597\t\
1.569\t1.810\t3.870\t1.156\t5.219\t0.038\t0.987\t7.321\t0.061\t2.347\t3.436\t\
2.494\t0.991\t1.560\n
0.070\t0.335\t1.160\t0.052\t0.511\t0.087\t0.746\t0.035\t0.070\t0.395\t2.708\t\
0.035\t1.060\t0.041\t1.061\t0.836\t0.876\t1.456\t0.876\t2.330\t1.773\t0.433\t\
2.047\t0.071\n
0.058\t3.684\t0.426\t0.957\t1.564\t1.935\t2.930\t1.175\t45.111\t5.490\t4.659\t\
16.602\t2.911\t4.096\t2.892\t0.084\t2.534\t1.820\t1.132\t0.500\t2.071\t0.761\t\
0.824\t1.364\n
0.045\t0.231\t0.246\t2.600\t0.658\t5.007\t1.093\t1.410\t0.089\t1.810\t0.251\t\
0.034\t2.126\t0.065\t0.893\t2.682\t1.226\t0.980\t4.734\t2.122\t1.469\t1.213\t\
0.057\t0.052\n
0.051\t1.091\t0.117\t0.454\t4.189\t2.823\t1.128\t0.219\t9.575\t1.829\t3.506\t\
7.271\t7.841\t0.504\t1.467\t0.130\t27.226\t3.093\t2.747\t1.087\t4.533\t\
16.917\t1.588\t6.551\n
0.037\t0.067\t0.770\t0.490\t0.711\t0.565\t0.922\t0.063\t0.841\t0.115\t0.046\t\
0.044\t6.361\t0.051\t0.330\t1.742\t0.105\t0.756\t0.320\t3.696\t5.029\t5.671\t\
0.056\t0.060\n
0.050\t0.234\t3.427\t14.636\t1.814\t5.541\t3.395\t6.570\t3.094\t5.384\t2.031\t\
5.400\t16.724\t0.207\t1.038\t0.072\t0.964\t4.050\t4.767\t7.891\t0.340\t1.730\t\
12.827\t1.946\n
0.064\t0.137\t0.843\t0.633\t0.119\t2.592\t5.804\t0.999\t0.511\t0.304\t0.353\t\
0.053\t2.645\t0.070\t0.071\t0.991\t0.286\t3.576\t1.993\t6.539\t8.736\t6.910\t\
0.070\t0.064\n
0.079\t1.160\t1.053\t3.178\t7.796\t2.323\t0.992\t0.760\t2.181\t2.739\t3.232\t\
1.166\t3.257\t0.680\t1.955\t0.088\t0.586\t7.026\t0.306\t8.078\t2.375\t10.286\t\
8.571\t0.528\n
0.081\t1.718\t2.069\t0.863\t0.197\t3.352\t0.132\t0.124\t0.145\t0.628\t0.060\t\
0.060\t2.612\t0.072\t0.177\t0.170\t1.261\t0.464\t4.059\t2.724\t3.449\t0.252\t\
0.073\t0.073\n
0.080\t1.128\t3.536\t38.352\t1.361\t1.293\t0.803\t0.456\t9.873\t6.525\t\
24.843\t1.052\t0.084\t1.034\t1.392\t0.066\t0.598\t3.002\t1.785\t8.376\t\
0.882\t0.272\t4.079\t11.586\n
0.086\t0.548\t0.625\t0.557\t0.601\t0.481\t0.449\t0.643\t52.291\t1.978\t\
0.068\t0.209\t11.138\t0.070\t0.324\t0.492\t5.913\t0.963\t0.843\t8.087\t\
0.647\t0.664\t0.080\t0.090\n
0.099\t8.458\t3.391\t17.942\t7.709\t3.955\t2.891\t7.681\t0.262\t3.994\t\
1.309\t6.377\t1.272\t0.638\t5.323\t5.794\t0.868\t1.021\t1.523\t0.662\t\
3.279\t1.980\t4.208\t1.794\n
0.763\t0.615\t0.352\t0.745\t1.383\t0.546\t0.247\t0.504\t5.138\t0.116\t\
0.167\t0.062\t0.573\t0.096\t0.227\t3.399\t7.361\t2.376\t3.790\t3.389\t\
0.906\t6.238\t0.112\t0.098\n
0.105\t0.505\t4.985\t0.450\t5.264\t15.071\t6.145\t10.357\t1.128\t4.151\t\
9.280\t8.581\t1.343\t2.416\t0.671\t9.347\t0.836\t5.312\t0.719\t0.622\t\
4.342\t4.166\t0.633\t11.101\n
"""


if __name__ == '__main__':
    main()

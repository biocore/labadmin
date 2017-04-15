from unittest import TestCase, main

import numpy as np
import numpy.testing as npt

from knimin.lib.parse import parse_qpcr_object


class TestParse(TestCase):
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


QPCR_OBJECT_ERROR1 = """
Include	Color	Pos	Name	CpError	Concentration	Standard	Status
TRUE	255	A1	Sample 1	10.73		0
"""

QPCR_OBJECT_ERROR2 = """
Include	Color	PosError	Name	Cp	Concentration	Standard	Status
TRUE	255	A1	Sample 1	10.73		0
"""

QPCR_OBJECT = """
Include	Color	Pos	Name	Cp	Concentration	Standard	Status
TRUE	255	A1	Sample 1	10.73		0
TRUE	255	A2	Sample 2	7.3		0
TRUE	255	A3	Sample 3	6.77		0
TRUE	255	A4	Sample 4	6.66		0
TRUE	255	A5	Sample 5	7.44		0
TRUE	255	A6	Sample 6	12.1		0
TRUE	255	A7	Sample 7	6.63		0
TRUE	255	A8	Sample 8	6.53		0
TRUE	255	A9	Sample 9	9.32		0
TRUE	255	A10	Sample 10	6.34		0
TRUE	255	A11	Sample 11	6.05		0
TRUE	255	A12	Sample 12	7.77		0
TRUE	255	A13	Sample 13	11.47		0
TRUE	255	A14	Sample 14	15.52		0
TRUE	255	A15	Sample 15	12.6		0
TRUE	255	A16	Sample 16	11.18		0
TRUE	255	A17	Sample 17	21.37		0
TRUE	255	A18	Sample 18	15.07		0
TRUE	255	A19	Sample 19	11.45		0
TRUE	255	A20	Sample 20	18.32		0
TRUE	255	A21	Sample 21	12.68		0
TRUE	255	A22	Sample 22	11.52		0
TRUE	255	A23	Sample 23	11.34		0
TRUE	255	A24	Sample 24	24.32		0
TRUE	255	B1	Sample 25	6.61		0
TRUE	255	B2	Sample 26	6.27		0
TRUE	255	B3	Sample 27	12.11		0
TRUE	255	B4	Sample 28	7.15		0
TRUE	255	B5	Sample 29	6.21		0
TRUE	255	B6	Sample 30	7.31		0
TRUE	255	B7	Sample 31	6.87		0
TRUE	255	B8	Sample 32	5.98		0
TRUE	255	B9	Sample 33	6.43		0
FALSE	255	B10	Sample 34	6.59		0
TRUE	255	B11	Sample 35	6.5		0
TRUE	255	B12	Sample 36	8.07		0
TRUE	255	B13	Sample 37	7.23		0
TRUE	255	B14	Sample 38	7.82		0
TRUE	255	B15	Sample 39	10.09		0
TRUE	255	B16	Sample 40	15.68		0
TRUE	65280	B17	Sample 41			0
TRUE	65280	B18	Sample 42			0
TRUE	255	B19	Sample 43	14.78		0
TRUE	255	B20	Sample 44	11.54		0
"""


if __name__ == '__main__':
    main()

from unittest import TestCase, main
from os.path import join, dirname, realpath
from os import mkdir, path
import random

from knimin.lib.code128 import code128_image
import knimin.lib.squash_barcodes as m


class SquashBarcodesTests(TestCase):
    def test_build_barcodes_pdf(self):
        self.assertIn('%PDF-1.4\n%', m.build_barcodes_pdf(['000000011']))

        old_get_image = m.get_image

        # replace get_image method to change behaviour.
        def mock_get_image1(barcodes):
            font = join(dirname(realpath(__file__)), '../', 'FreeSans.ttf')
            for b in barcodes:
                yield code128_image(b, height=150, width=300, font=font,
                                    thickness=2, show_text=True,
                                    quiet_zone=False)
        m.get_image = mock_get_image1
        self.assertIn('%PDF-1.4\n%', m.build_barcodes_pdf(['000000011']))

        # replace get_image method to change behaviour
        def mock_get_image2(barcodes):
            font = join(dirname(realpath(__file__)), '../', 'FreeSans.ttf')
            for b in barcodes:
                yield code128_image(b, height=150, width=303, font=font,
                                    thickness=2, show_text=True,
                                    quiet_zone=False)
        m.get_image = mock_get_image2
        self.assertRaisesRegexp(AttributeError,
                                "shape",
                                m.build_barcodes_pdf,
                                ['000000011'])
        # reset function
        m.get_image = old_get_image

    def test_tmpdir(self):
        # test that a temporary directory cannot collide with an existing one
        random.seed(7)
        fake_tmp_dir = 'tmp_IDQBN'
        if not path.exists(fake_tmp_dir):
            mkdir(fake_tmp_dir)
        self.assertTrue(m.build_barcodes_pdf(['000000011']))

    def test_get_image(self):
        barcodes = ['008675309', '314159265']
        counts = 0

        for b in m.get_image(barcodes):
            self.assertEqual(b.getbbox(), (0, 0, 202, 100))
            counts += 1

        self.assertEqual(counts, 2)

    def test_build_barcodes_pdf_one_page(self):
        pdf = m.build_barcodes_pdf(['000000011'] * 36)

        self.assertTrue(ONE_PAGE_HEADER in pdf)

    def test_build_barcodes_pdf_two_pages(self):
        pdf = m.build_barcodes_pdf(['000000011'] * 72)

        self.assertTrue(TWO_PAGES_HEADER in pdf)


ONE_PAGE_HEADER = """<</Type/Page/MediaBox [0 0 1275 1650]
/Parent 3 0 R
/Resources<</ProcSet[/PDF /ImageC]
/ExtGState 9 0 R
/XObject 10 0 R
>>
/Contents 5 0 R
>>
endobj
3 0 obj
"""

TWO_PAGES_HEADER = """<</Type/Page/MediaBox [0 0 1275 1650]
/Parent 3 0 R
/Resources<</ProcSet[/PDF /ImageC]
/ExtGState 9 0 R
/XObject 10 0 R
>>
/Contents 5 0 R
>>
endobj
11 0 obj
<</Type/Page/MediaBox [0 0 1275 1650]
/Parent 3 0 R
/Resources<</ProcSet[/PDF /ImageC]
/ExtGState 14 0 R
/XObject 15 0 R
>>
/Contents 12 0 R
>>
endobj
3 0 obj"""


if __name__ == '__main__':
    main()

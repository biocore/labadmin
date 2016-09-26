
from unittest import TestCase, main

from knimin.lib.squash_barcodes import get_image, build_barcodes_pdf


class SquashBarcodesTests(TestCase):

    def test_get_image(self):
        barcodes = ['008675309', '314159265']
        counts = 0

        for b in get_image(barcodes):
            self.assertEqual(b.getbbox(), (0, 0, 202, 100))
            counts += 1

        self.assertEqual(counts, 2)

    def test_build_barcodes_pdf_one_page(self):
        pdf = build_barcodes_pdf(['000000011'] * 36)

        self.assertTrue(ONE_PAGE_HEADER in pdf)

    def test_build_barcodes_pdf_two_pages(self):
        pdf = build_barcodes_pdf(['000000011'] * 72)

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

from unittest import TestCase, main
from os.path import join, dirname, realpath

import knimin.lib
from knimin.lib.code128 import code128_format, code128_image


class Code128Tests(TestCase):
    def test_code128_format(self):
        # https://en.wikipedia.org/wiki/Code_128#Check_digit_calculation
        # result differs slightly, notably using Start Code B, and we include
        # the stop block. The use of Start Code B increments the checksum by
        # 1 as well.
        wikipedia_example = 'PJJ123C'
        exp = [104, 48, 42, 42, 17, 18, 19, 35, 55, 106]
        obs = code128_format(wikipedia_example)
        self.assertEqual(obs, exp)

    def test_code128_image(self):
        # use the same font etc as is in use with squash_barcodes
        font = join(dirname(realpath(knimin.lib.__file__)), 'FreeSans.ttf')
        im = code128_image('000001234', height=100, width=202,
                           thickness=2, show_text=True, quiet_zone=False,
                           font=font)
        self.assertEqual(im.height, 100)
        self.assertEqual(im.width, 202)


if __name__ == '__main__':
    main()

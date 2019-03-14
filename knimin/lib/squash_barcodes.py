#!/usr/bin/env python

"""take barcodes and dump to a single multipage pdf

requires GPL Ghostscript 9.05
"""

from PIL import Image
from os import path, mkdir
from os.path import join, dirname, realpath
from math import ceil
from random import choice
from shutil import rmtree
from subprocess import Popen, PIPE
from shlex import split as cmd_split

from knimin.lib.code128 import code128_image


def get_image(barcodes):
    font = join(dirname(realpath(__file__)), 'FreeSans.ttf')
    for b in barcodes:
        yield code128_image(b, height=100, width=202, font=font, thickness=2,
                            show_text=True, quiet_zone=False)


def build_barcodes_pdf(barcodes):
    # 36 barcodes per page
    pages = int(ceil(len(barcodes) / 36.0))

    # assuming N * 8.5in x 11in
    PAGE_WIDTH = 1275
    PAGE_HEIGHT = 1650

    # create blank pdfs
    blanks = [Image.new('RGB', (PAGE_WIDTH, PAGE_HEIGHT), (255, 255, 255))
              for i in range(pages)]

    # padding set empirically for
    # Electronic Imaging Materials
    # Part #80402
    START_LEFT = 18
    START_UPPER = 59
    HORIZ_GAP = 23
    VERT_GAP = 17
    BOX_WIDTH = 300
    BOX_HEIGHT = 150

    # center barcode, assuming barcode images are 300x150px
    # will adjust per image if 202x100px
    SHIFT_RIGHT = 0
    SHIFT_DOWN = 0

    # set starting points
    cur_left = START_LEFT
    cur_upper = START_UPPER
    page = -1
    idx = 0
    for i in get_image(barcodes):
        # if we have 36 barcodes we have filled a page
        if idx % 36 == 0:
            page += 1
            cur_upper = START_UPPER
            cur_left = START_LEFT

        # verify the barcode is the expected size, shift accordingly
        width, height = i.size
        if i.size == (202, 100):
            SHIFT_RIGHT = 49
            SHIFT_DOWN = 25
        elif i.size == (300, 150):
            SHIFT_RIGHT = 0
            SHIFT_DOWN = 0
        else:
            tmp = "image %s is an unsupported size"
            raise AttributeError(tmp % i.shape)

        # shift to new row
        if cur_left + width > PAGE_WIDTH:
            cur_left = START_LEFT
            cur_upper = cur_upper + HORIZ_GAP + BOX_HEIGHT

        # paste into the image
        blanks[page].paste(i, (cur_left + SHIFT_RIGHT, cur_upper + SHIFT_DOWN))

        # shift right
        cur_left += BOX_WIDTH + VERT_GAP

        idx += 1

    # write out each page
    tmpdir = "tmp_%s" % ''.join([choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
                                 for i in range(5)])
    # TODO: leverage python's tempfile module to replace this home brew
    # mechanism here. See issue: #147.
    while path.exists(tmpdir):
        tmpdir = "tmp_%s" % ''.join([choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
                                     for i in range(5)])
    mkdir(tmpdir)

    temp_pages = "squash_barcode_page_%d.pdf"
    for page, blank in enumerate(blanks):
        blank.save(path.join(tmpdir, temp_pages % page), quality=100)

    match_pages = ' '.join([path.join(tmpdir, "squash_barcode_page_%d.pdf" % i)
                            for i in range(len(blanks))])

    # magically squash all the pages
    cmd = cmd_split('gs -r150 -q -sPAPERSIZE=a4 -dNOPAUSE -dBATCH' +  # noqa
                    ' -sDEVICE=pdfwrite -sOutputFile=- %s' % match_pages)
    p = Popen(cmd, stdout=PIPE)
    output, _ = p.communicate()
    rmtree(tmpdir)
    # return PDF text
    return output

#!/usr/bin/env python
from knimin.handlers.base import BaseHandler

from amgut.util import AG_DATA_ACCESS


class AGNewBarcodeHandler(BaseHandler):
    def get(self):
        next_barcode, text_barcode = AG_DATA_ACCESS.getNextAGBarcode()
        self.render("ag_new_barcode.html", kitid=None, barcode=next_barcode,
                    t_barcode=text_barcode, response=None,
                    loginerror='')

    def post(self):
        num_barcodes = len(self.request.arguments)
        kit_id = self.get_argument('kitid')
        kitinfo = AG_DATA_ACCESS.getAGKitDetails(kit_id)
        if 'supplied_kit_id' not in kitinfo:
            next_barcode, text_barcode = AG_DATA_ACCESS.getNextAGBarcode()
            self.render("ag_new_barcode.html", kitid=kit_id,
                        barcode=next_barcode,
                        t_barcode=text_barcode, response='Bad Kit',
                        loginerror='')
            return

        try:
            for x in range(1, num_barcodes):
                field = 'barcode_%s' % x
                print field
                barcode = self.get_argument(field)
                AG_DATA_ACCESS.addAGBarcode(kitinfo['ag_kit_id'], barcode)

            self.render("ag_new_barcode.html", response='Good',
                        kitid=None, barcode=None, t_barcode=None,
                        loginerror='')
        except:
            self.render("ag_new_barcode.html", response='Bad',
                        kitid=None, barcode=None, t_barcode=None,
                        loginerror='')

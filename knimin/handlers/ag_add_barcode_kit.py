from tornado.web import authenticated
from knimin.handlers.base import BaseHandler

from knimin import db


class AGAddBarcodeKitHandler(BaseHandler):
    @authenticated
    def get(self):
        self.render("ag_add_barcode_kit.html", currentuser=self.current_user,
                    kit_ids=db.get_used_kit_ids())

    @authenticated
    def post(self):
        kit_id = self.get_argument('kit_id')
        num_barcodes = int(self.get_argument('num_barcodes'))
        db.add_barcodes_to_kit(kit_id, num_barcodes)
        self.render("ag_add_barcode_kit.html", currentuser=self.current_user,
                    kit_ids=db.get_used_kit_ids())
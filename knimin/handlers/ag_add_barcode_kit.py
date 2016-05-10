from tornado.web import authenticated
from knimin.handlers.base import BaseHandler
from knimin.handlers.access_decorators import set_access

from knimin import db


@set_access(['AG kits'])
class AGAddBarcodeKitHandler(BaseHandler):
    @authenticated
    def get(self):
        self.render("ag_add_barcode_kit.html", currentuser=self.current_user,
                    kit_ids=db.get_used_kit_ids(), skid='', barcodes='')

    @authenticated
    def post(self):
        supplied_kit_id = self.get_argument('kit_id')
        num_barcodes = int(self.get_argument('num_barcodes'))

        ag_kit_id = db.getAGKitDetails(supplied_kit_id)['ag_kit_id']
        barcodes = db.add_barcodes_to_kit(ag_kit_id, num_barcodes)

        self.render("ag_add_barcode_kit.html", currentuser=self.current_user,
                    kit_ids=db.get_used_kit_ids(), skid=supplied_kit_id,
                    barcodes=', '.join(barcodes))

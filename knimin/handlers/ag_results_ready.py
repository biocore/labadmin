from tornado.web import authenticated

from knimin.handlers.base import BaseHandler
from knimin import db
from knimin.handlers.access_decorators import set_access


@set_access(['Metadata Pulldown'])
class AGResultsReadyHandler(BaseHandler):
    @authenticated
    def post(self):
        barcodes = db.get_barcodes_with_results()
        if len(barcodes) == 0:
            self.write('ERROR: No barcode results available')
            return

        msg = 'Sucessfully updated barcodes to results ready status.'
        try:
            db.mark_results_ready(barcodes)
        except Exception as e:
            msg = 'ERROR: ' + str(e)
        self.write(msg)

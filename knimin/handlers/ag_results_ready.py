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

        msg = 'Successfully updated barcodes to results ready status.'
        try:
            db.mark_results_ready(barcodes)
        except Exception as e:
            # TODO: refactor for clear message to the user, see issue: #126
            msg = 'ERROR: ' + str(e)
        self.write(msg)

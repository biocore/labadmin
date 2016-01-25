from knimin.handlers.base import BaseHandler
from knimin import db


class AGConsentCheckHandler(BaseHandler):
    def get(self):
        self.render('consent_check.html', consents=[], failures={})

    def post(self):
        barcodes = [b.strip() for b in
                    self.get_argument('barcodes').split('\n')]
        consents, failures = db.check_consent(barcodes)
        self.render('consent_check.html', consents=sorted(consents),
                    failures=failures)

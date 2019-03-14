#!/usr/bin/env python
from tornado.web import authenticated
from knimin.handlers.base import BaseHandler
from knimin.handlers.access_decorators import set_access

from knimin import db


@set_access(['Search'])
class AGEditBarcodeHandler(BaseHandler):
    @authenticated
    def get(self):
        barcode = self.get_argument('barcode', None)
        if barcode is not None:
            details = db.getAGBarcodeDetails(barcode)
            ag_login_id = db.search_kits(details['ag_kit_id'])[0]
            site_sampled = db.human_sites
            environment_sampled = db.general_sites
            participants = db.getHumanParticipants(ag_login_id) + \
                db.getAnimalParticipants(ag_login_id)
            self.render("ag_edit_barcode.html", response=None, barcode=barcode,
                        sites_sampled=site_sampled, details=details,
                        environments_sampled=environment_sampled,
                        participants=participants,
                        currentuser=self.current_user)
        else:
            self.set_status(400)

    @authenticated
    def post(self):
        barcode = self.get_argument('barcode')
        ag_kit_id = self.get_argument('ag_kit_id')
        site_sampled = self.get_argument('site_sampled')
        environment_sampled = self.get_argument('environment_sampled')
        sample_date = self.get_argument('sample_date')
        sample_time = self.get_argument('sample_time')
        participant_name = self.get_argument('participant_name')
        notes = self.get_argument('notes')
        refunded = self.get_argument('refunded')
        withdrawn = self.get_argument('withdrawn')

        try:
            db.updateAGBarcode(barcode, ag_kit_id, site_sampled,
                               environment_sampled, sample_date,
                               sample_time, participant_name,
                               notes, refunded, withdrawn)
            self.render("ag_edit_barcode.html", response='Good', barcode=None,
                        sites_sampled=None, details=None,
                        environments_sampled=None,
                        participants=[], currentuser=self.current_user)
        except:  # noqa
            self.render("ag_edit_barcode.html", response='Bad', barcode=None,
                        sites_sampled=None, details=None,
                        environments_sampled=None,
                        participants=[], currentuser=self.current_user)

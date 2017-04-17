#!/usr/bin/env python
from tornado.web import authenticated
from knimin.handlers.base import BaseHandler
from knimin.handlers.access_decorators import set_access

from knimin import db


@set_access(['Search'])
class AGSearchHandler(BaseHandler):
    @authenticated
    def get(self):
        self.render("ag_search.html", results=None, handouts=None,
                    currentuser=self.current_user)

    @authenticated
    def post(self):
        term = self.get_argument('search_term')
        results = {}
        # search participant info
        logins = db.search_participant_info(term)
        results = set(logins)
        # search kit info and add to resluts
        logins = db.search_kits(term)
        results = results | set(logins)
        #  search barcode and add to results
        logins = db.search_barcodes(term)
        results = results | set(logins)
        # search handout kits
        handouts = db.search_handout_kits(term)

        # now take the ag_login_ids and collect the information to display
        display_results = []  # list of dictionatries
        for login in results:
            login_display = {}
            login_display['login_info'] = db.get_login_info(login)
            login_display['humans'] = db.getHumanParticipants(
                login)
            login_display['animals'] = db.getAnimalParticipants(
                login)
            login_display['kit'] = db.get_kit_info_by_login(login)
            for kit in login_display['kit']:
                barcode_info = {}
                ag_barcodes = db.get_barcode_info_by_kit_id(
                    kit['ag_kit_id'])
                barcode_info = {}
                for ag_barcode in ag_barcodes:
                    barcode_info[ag_barcode['barcode']] = {}
                    barcode_info[ag_barcode['barcode']]['ag_info'] = ag_barcode
                    lab_barcode_info = db.get_barcode_details(
                        ag_barcode['barcode'])
                    barcode_info[ag_barcode['barcode']]['barcode_info'] = \
                        lab_barcode_info
                kit['barcode_info'] = barcode_info
            display_results.append(login_display)

        # now render the page
        self.render("ag_search.html",
                    results=display_results,
                    handouts=handouts,
                    currentuser=self.current_user)

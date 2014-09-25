#!/usr/bin/env pythonget_barcode_info_by_kit_id
from knimin.handlers.base import BaseHandler
from urllib import unquote


from amgut.util import AG_DATA_ACCESS


class AGSearchHandler(BaseHandler):
    def get(self):
        self.render("ag_search.html", results=None, handouts=None,
                    loginerror='')

    def post(self):
        term = self.get_argument('search_term')
        results = {}
        # search participant info
        logins = AG_DATA_ACCESS.search_participant_info(term)
        results = set(logins)
        # search kit info and add to resluts
        logins = AG_DATA_ACCESS.search_kits(term)
        results = results | set(logins)
        #  search barcode and add to results
        logins = AG_DATA_ACCESS.search_barcodes(term)
        results = results | set(logins)
        # search handout kits
        handouts = AG_DATA_ACCESS.search_handout_kits(term)

        #now take the ag_login_ids and collect the information to display
        display_results = []  # list of dictionatries
        for login in results:
            login_display = {}
            login_display['login_info'] = AG_DATA_ACCESS.get_login_info(login)
            login_display['humans'] = AG_DATA_ACCESS.getHumanParticipants(
                login)
            login_display['animals'] = AG_DATA_ACCESS.getAnimalParticipants(
                login)
            login_display['kit'] = AG_DATA_ACCESS.get_kit_info_by_login(login)
            for kit in login_display['kit']:
                barcode_info = {}
                ag_barcodes = AG_DATA_ACCESS.get_barcode_info_by_kit_id(
                    kit['ag_kit_id'])
                barcode_info = {}
                for ag_barcode in ag_barcodes:
                    barcode_info[ag_barcode['barcode']] = {}
                    barcode_info[ag_barcode['barcode']]['ag_info'] = ag_barcode
                    lab_barcode_info = AG_DATA_ACCESS.get_barcode_details(
                        ag_barcode['barcode'])
                    plate = AG_DATA_ACCESS.get_plate_for_barcode(
                        ag_barcode['barcode'])
                    barcode_info[ag_barcode['barcode']]['barcode_info'] = \
                        lab_barcode_info
                    barcode_info[ag_barcode['barcode']]['plate'] = plate
                kit['barcode_info'] = barcode_info
            display_results.append(login_display)

        #now render the page
        self.render("ag_search.html", results=display_results,
                    handouts=handouts, loginerror='')

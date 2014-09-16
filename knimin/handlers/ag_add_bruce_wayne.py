#!/usr/bin/env python
from knimin.handlers.base import BaseHandler

from amgut.util import AG_DATA_ACCESS


class AGAddBruceWayne(BaseHandler):
    def get(self):
        self.render("ag_add_bruce_wayne.html", response="", loginerror="")

    def post(self):
        wayne = self.get_argument("wayne")
        participant = self.get_argument("ag_login_id")
        login = AG_DATA_ACCESS.get_login_by_email(participant)
        if 'login_id' not in login:
            self.render("ag_add_bruce_wayne.html", response='Bad Email',
                        loginerror='')
            return
        AG_DATA_ACCESS.addBruceWayne(participant, wayne)
        self.render("ag_add_bruce_wayne.html", response='Added Successfully',
                    loginerror='')

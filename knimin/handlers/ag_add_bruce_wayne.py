#!/usr/bin/env python
from tornado.web import authenticated
from knimin.handlers.base import BaseHandler

from amgut.util import AG_DATA_ACCESS


class AGAddBruceWayne(BaseHandler):
    @authenticated
    def get(self):
        self.render("ag_add_bruce_wayne.html", response="",
                    currentuser=self.current_user)

    @authenticated
    def post(self):
        wayne = self.get_argument("wayne")
        participant = self.get_argument("ag_login_id")
        login = AG_DATA_ACCESS.get_login_by_email(participant)
        if 'ag_login_id' not in login:
            self.render("ag_add_bruce_wayne.html", response='Bad Email',
                        currentuser=self.current_user)
            return
        AG_DATA_ACCESS.addParticipantException(login['ag_login_id'], wayne)
        self.render("ag_add_bruce_wayne.html", response='Added Successfully',
                    currentuser=self.current_user)

#!/usr/bin/env python
from knimin.handlers.base import BaseHandler

from amgut.util import AG_DATA_ACCESS


class AGNewParticipantHandler(BaseHandler):
    def get(self):
        self.render("ag_new_participant.html", response=None, loginerror='')

    def post(self):
        email = self.get_argument('email')
        name = self.get_argument('name')
        address = self.get_argument('address')
        city = self.get_argument('city')
        state = self.get_argument('state')
        zipcode = self.get_argument('zipcode')
        country = self.get_argument('country')
        try:
            AG_DATA_ACCESS.addAGLogin(email, name, address, city, state,
                                      zipcode, country)
            self.render("ag_new_participant.html", response='Good',
                        loginerror='')
        except:
            self.render("ag_new_participant.html", response='Bad',
                        loginerror='')

#!/usr/bin/env python
from tornado.web import authenticated
from knimin.handlers.base import BaseHandler

from amgut.connections import ag_data


class AGNewParticipantHandler(BaseHandler):
    @authenticated
    def get(self):
        self.render("ag_new_participant.html", response=None,
                    currentuser=self.current_user)

    @authenticated
    def post(self):
        email = self.get_argument('email')
        name = self.get_argument('name')
        address = self.get_argument('address')
        city = self.get_argument('city')
        state = self.get_argument('state')
        zipcode = self.get_argument('zipcode')
        country = self.get_argument('country')
        try:
            ag_data.addAGLogin(email, name, address, city, state,
                                      zipcode, country)
            self.render("ag_new_participant.html", response='Good',
                        currentuser=self.current_user)
        except:
            self.render("ag_new_participant.html", response='Bad',
                        currentuser=self.current_user)

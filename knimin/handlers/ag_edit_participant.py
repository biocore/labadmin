#!/usr/bin/env python
from knimin.handlers.base import BaseHandler
from urllib import unquote


from amgut.util import AG_DATA_ACCESS


class AGEditParticipantHandler(BaseHandler):
    def get(self):
        email = self.get_argument('email', None)
        if email is not None:
            email = unquote(email)
            login = AG_DATA_ACCESS.get_login_by_email(email)
            print login
            self.render("ag_edit_participant.html", response=None,
                        login=login, loginerror='')

    def post(self):
        email = self.get_argument('email')
        name = self.get_argument('name')
        address = self.get_argument('address')
        city = self.get_argument('city')
        state = self.get_argument('state')
        zipcode = self.get_argument('zipcode')
        country = self.get_argument('country')
        ag_login_id = self.get_argument('ag_login_id')
        try:
            AG_DATA_ACCESS.updateAGLogin(ag_login_id, email, name, address,
                                         city, state, zipcode, country)
            self.render("ag_edit_participant.html", response='Good',
                        login=None,
                        loginerror='')
        except:
            self.render("ag_edit_participant.html", response='Bad',
                        login=None, loginerror='')

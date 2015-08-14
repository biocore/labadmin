#!/usr/bin/env python
from tornado.web import authenticated
from knimin.handlers.base import BaseHandler
from urllib import unquote

from knimin import db


class AGEditParticipantHandler(BaseHandler):
    @authenticated
    def get(self):
        email = self.get_argument('email', None)
        if email is not None:
            email = unquote(email)
            login = db.get_login_by_email(email)
            self.render("ag_edit_participant.html", response=None,
                        login=login, currentuser=self.current_user)

    @authenticated
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
            db.updateAGLogin(ag_login_id, email, name, address,
                             city, state, zipcode, country)
            self.render("ag_edit_participant.html", response='Good',
                        login=None,
                        currentuser=self.current_user)
        except:
            self.render("ag_edit_participant.html", response='Bad',
                        login=None, currentuser=self.current_user)

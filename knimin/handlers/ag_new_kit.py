#!/usr/bin/env python
from tornado.web import authenticated
from knimin.handlers.base import BaseHandler

from amgut.util import AG_DATA_ACCESS


class AGNewKitHandler(BaseHandler):
    @authenticated
    def get(self):
        kit_id = AG_DATA_ACCESS.getNewAGKitId()
        passwd = AG_DATA_ACCESS.getAGCode(8, 'numeric')
        vercode = AG_DATA_ACCESS.getAGCode(8, 'numeric')
        self.render("ag_new_kit.html", email=None, kitid=kit_id,
                    password=passwd,
                    vercode=vercode, response=None,
                    currentuser=self.current_user)

    @authenticated
    def post(self):
        email = self.get_argument('email')
        kit_id = self.get_argument('kit_id')
        passwd = self.get_argument('kit_password')
        swabs_per_kit = self.get_argument('swabs_per_kit')
        vercode = self.get_argument('kit_verification_code')
        login = AG_DATA_ACCESS.get_login_by_email(email)
        if 'ag_login_id' not in login:
            self.render("ag_new_kit.html", email=email, kitid=kit_id,
                        password=passwd,
                        vercode=vercode, response='Bad Email',
                        currentuser=self.current_user)
            return
        try:
            AG_DATA_ACCESS.addAGKit(login['ag_login_id'], kit_id, passwd,
                                    swabs_per_kit, vercode)
            self.render("ag_new_kit.html", response='Good', email=None,
                        kitid=None, password=None, vercode=None,
                        currentuser=self.current_user)
        except:
            self.render("ag_new_kit.html", response='Bad', email=None,
                        kitid=None, password=None, vercode=None,
                        currentuser=self.current_user)

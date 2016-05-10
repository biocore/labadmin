#!/usr/bin/env python
from tornado.web import authenticated
from knimin.handlers.base import BaseHandler
from knimin.handlers.access_decorators import set_access

from knimin import db


@set_access(['Search', 'AG kits'])
class AGEditKitHandler(BaseHandler):
    @authenticated
    def get(self):
        kitid = self.get_argument('kitid', None)
        if kitid is not None:
            kitdetails = db.getAGKitDetails(kitid)
            email = db.get_user_info(kitid)['email']
            self.render("ag_edit_kit.html", response=None, email=email,
                        kitinfo=kitdetails, currentuser=self.current_user)

    @authenticated
    def post(self):
        ag_kit_id = self.get_argument('ag_kit_id')
        kit_id = self.get_argument('kitid')
        passwd = self.get_argument('kit_password')
        swabs_per_kit = self.get_argument('swabs_per_kit')
        vercode = self.get_argument('kit_verification_code')
        try:
            db.updateAGKit(ag_kit_id, kit_id, passwd,
                           swabs_per_kit, vercode)
            self.render("ag_edit_kit.html", response='Good', email=None,
                        kitinfo=None, currentuser=self.current_user)
        except:
            self.redner("ag_edit_kit.html", response='Bad', email=None,
                        kitinfo=None, currentuser=self.current_user)

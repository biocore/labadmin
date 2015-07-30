#!/usr/bin/env python
from json import dumps, loads
from tornado.web import authenticated
from tornado.escape import urlencode
from knimin.handlers.base import BaseHandler
from knimin import db
from knimin.lib.mem_zip import InMemoryZip
from knimin.lib.util import get_printout_data
from amgut.connections import ag_data


class AGNewKitDLHandler(BaseHandler):
    @authenticated
    def get(self):
        kitinfo = loads(self.get_argument('kitinfo'))
        kit_zip = InMemoryZip()
        kit_zip.append('kit_printouts.txt', get_printout_data(kitinfo))

class AGNewKitHandler(BaseHandler):
    @authenticated
    def get(self):
        project_names = ag_data.getProjectNames()
        self.render("ag_new_kit.html", projects=project_names,
                    currentuser=self.current_user, msg="")

    @authenticated
    def post(self):
        tag = self.get_argument("tag")
        projects = self.get_arguments("projects")
        num_swabs = map(int, self.get_arguments("swabs"))
        num_kits = map(int, self.get_arguments("kits"))
        try:
            kits = db.create_ag_kits(zip(num_swabs, num_kits), tag, projects)
        except Exception as e:
            msg = "ERROR: %s" % str(e)
        else:
            msg = "Kits created! Please wait for downloads."

        project_names = ag_data.getProjectNames()
        self.render("ag_new_kit.html", projects=project_names,
                    currentuser=self.current_user, msg=msg,
                    kitinfo=urlencode(dumps(kits)))

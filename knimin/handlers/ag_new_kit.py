#!/usr/bin/env python
from tornado.web import authenticated
from knimin.handlers.base import BaseHandler
from knimin import db
from amgut.connections import ag_data


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
            db.create_ag_kits(zip(num_swabs, num_kits), tag, projects)
        except Exception as e:
            msg = "ERROR: %s" % str(e)
        else:
            msg = "Kits created! Please wait for downloads."

        project_names = ag_data.getProjectNames()
        self.render("ag_new_kit.html", projects=project_names,
                    currentuser=self.current_user, msg=msg)

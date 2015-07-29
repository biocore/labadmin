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
                    currentuser=self.current_user)

    @authenticated
    def post(self):
        tag = self.get_argument("tag")
        projects = self.get_arguments("projects")
        num_swabs = map(int, self.get_arguments("swabs"))
        num_kits = map(int, self.get_arguments("kits"))

        db.create_ag_kits(zip(num_swabs, num_kits))

        project_names = ag_data.getProjectNames()
        self.render("ag_new_kit.html", projects=project_names,
                    currentuser=self.current_user)

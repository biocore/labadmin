#!/usr/bin/env python
from tornado.web import authenticated
from knimin.handlers.base import BaseHandler

from amgut.connections import ag_data
from knimin import db


class AGNewBarcodeHandler(BaseHandler):
    @authenticated
    def get(self):
        project_names = ag_data.getProjectNames()
        self.render("ag_new_barcode.html", currentuser=self.current_user,
                    projects=project_names, barcodes=[], msg="")

    @authenticated
    def post(self):
        action = self.get_argument('action')
        barcodes_info = []
        msg=""
        if action == 'create':
            projects = self.get_arguments('projects')
            new_project = self.get_argument('newproject').strip()
            num_barcodes = int(self.get_argument('numbarcodes'))
            if new_project:
                db.create_project(new_project)
                projects.append(new_project)
            new_barcodes = db.create_barcodes(num_barcodes, projects)
            barcodes_info = db.view_barcodes_info(new_barcodes)
            msg = "%d Barcodes created!" % num_barcodes
        elif action == 'view':
            projects = self.get_arguments('projects')
            limit = int(self.get_argument('limit'))
            if limit == 0:
                limit = None
            barcodes_info = db.view_barcodes_for_projects(projects, limit)
        else:
            raise RuntimeError("Unknown action for AGNewBarcdeHandler: %s" %
                               action)

        project_names = ag_data.getProjectNames()
        self.render("ag_new_barcode.html", currentuser=self.current_user,
                    projects=project_names, barcodes=barcodes_info, msg=msg)

#!/usr/bin/env python
from tornado.web import authenticated, HTTPError
from knimin.handlers.base import BaseHandler

from amgut.connections import ag_data


class AGNewBarcodeHandler(BaseHandler):
    @authenticated
    def get(self):
        project_names = ag_data.getProjectNames()
        self.render("ag_new_barcode.html", currentuser=self.current_user,
                    projects=project_names, barcodes=[])

    @authenticated
    def post(self):
        barcodes = []
        action = self.get_argument('action')
        if action == 'create':
            projects = self.get_arguments('projects', [])
            new_project = self.get_argument('newproject').strip()
            num_barcodes = self.get_argument('numbarcodes')
            if new_project:
                ag_data.createProject(new_project)
                projects.append(new_project)
            

        elif action == 'view':

        else:
            raise HTTPError(400, 'Unexpected action: %s' % action)
        project_names = ag_data.getProjectNames()
        self.render("ag_new_barcode.html", currentuser=self.current_user,
                    projects=project_names, barcodes=barcodes)

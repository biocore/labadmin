#!/usr/bin/env python
from tornado.web import authenticated
from knimin.handlers.base import BaseHandler

from amgut.connections import ag_data
from knimin.lib.squash_barcodes import build_barcodes_pdf
from knimin import db


class AGBarcodePrintoutHandler(BaseHandler):
    @authenticated
    def post(self):
        barcodes = self.get_argument('barcodes').split(",")
        pdf = build_barcodes_pdf(barcodes)
        self.add_header('Content-type',  'application/pdf')
        self.add_header('Content-Transfer-Encoding', 'binary')
        self.add_header('Accept-Ranges', 'bytes')
        self.add_header('Content-Encoding', 'none')
        self.add_header('Content-Disposition', 'attachment; filename=barcodes.pdf')
        self.write(pdf)
        self.flush()
        self.finish()


class AGNewBarcodeHandler(BaseHandler):
    @authenticated
    def get(self):
        project_names = ag_data.getProjectNames()
        remaining = len(db.get_unassigned_barcodes())
        self.render("ag_new_barcode.html", currentuser=self.current_user,
                    projects=project_names, barcodes=[], remaining=remaining,
                    msg="", newbc=[])

    @authenticated
    def put(self):
        # assign barcodes to projects
        projects = self.get_arguments('projects')
        new_project = self.get_argument('newproject').strip()
        num_barcodes = int(self.get_argument('numbarcodes'))
        try:
            if new_project:
                db.create_project(new_project)
                projects.append(new_project)
            db.assign_barcodes(num_barcodes, projects)
        except ValueError as e:
            msg = "ERROR! %s" % str(e)
        else:
            msg = "%d barcodes assigned to %s" % (num_barcodes,
                                                  ", ".join(projects))

        project_names = ag_data.getProjectNames()
        remaining = len(db.get_unassigned_barcodes())
        self.render("ag_new_barcode.html", currentuser=self.current_user,
                    projects=project_names, remaining=remaining, msg=msg,
                    newbc=[])

    @authenticated
    def post(self):
        # create barcodes
        msg=""
        num_barcodes = int(self.get_argument('numbarcodes'))
        newbc = db.create_barcodes(num_barcodes)
        msg = "%d Barcodes created! Please wait for barcode download" % num_barcodes

        project_names = ag_data.getProjectNames()
        remaining = len(db.get_unassigned_barcodes())
        self.render("ag_new_barcode.html", currentuser=self.current_user,
                    projects=project_names, remaining=remaining, msg=msg,
                    newbc=newbc)

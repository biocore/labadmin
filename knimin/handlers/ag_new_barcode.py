#!/usr/bin/env python
from tornado.web import authenticated, HTTPError
from tornado.escape import url_unescape
from knimin.handlers.base import BaseHandler
from knimin.handlers.access_decorators import set_access

from knimin.lib.squash_barcodes import build_barcodes_pdf
from knimin import db


@set_access(['Barcodes'])
class AGBarcodePrintoutHandler(BaseHandler):
    @authenticated
    def post(self):
        barcodes = self.get_argument('barcodes').split(",")
        pdf = build_barcodes_pdf(barcodes)
        self.add_header('Content-type', 'application/pdf')
        self.add_header('Content-Transfer-Encoding', 'binary')
        self.add_header('Accept-Ranges', 'bytes')
        self.add_header('Content-Encoding', 'none')
        self.add_header('Content-Disposition',
                        'attachment; filename=barcodes.pdf')
        self.write(pdf)
        self.flush()
        self.finish()


class AGBarcodeAssignedHandler(BaseHandler):
    @authenticated
    def post(self):
        barcodes = self.get_arguments('barcodes')
        projects = self.get_arguments('projects')
        text = "".join(["%s\t%s\n" % (b, ",".join(projects))
                        for b in barcodes])
        self.add_header('Content-type', 'plain/text')
        self.add_header('Content-Transfer-Encoding', 'binary')
        self.add_header('Accept-Ranges', 'bytes')
        self.add_header('Content-Encoding', 'none')
        self.add_header('Content-Disposition',
                        'attachment; filename=barcodes_assigned.txt')
        self.write(text)
        self.flush()
        self.finish()


@set_access(['Barcodes'])
class AGNewBarcodeHandler(BaseHandler):
    @authenticated
    def get(self):
        project_names = db.getProjectNames()
        remaining = len(db.get_unassigned_barcodes())
        self.render("ag_new_barcode.html", currentuser=self.current_user,
                    projects=project_names, barcodes=[], remaining=remaining,
                    msg="", newbc=[], assignedbc=[], assign_projects="")

    @authenticated
    def post(self):
        # create barcodes
        msg = ""
        newbc = []
        assignedbc = []
        projects = []
        action = self.get_argument("action")
        num_barcodes = int(self.get_argument('numbarcodes'))

        if action == "create":
            newbc = db.create_barcodes(num_barcodes)
            msg = ("%d Barcodes created! Please wait for barcode download"
                   % num_barcodes)

        elif action == "assign":
            projects = [url_unescape(p).encode('utf-8')
                        for p in self.get_arguments('projects')]
            new_project = self.get_argument('newproject').strip()
            try:
                if new_project:
                    db.create_project(new_project)
                    projects.append(new_project)
                assignedbc = db.assign_barcodes(num_barcodes, projects)
            except ValueError as e:
                msg = u"ERROR! %s" % e.message
            else:
                projects = [p.decode('utf-8') for p in projects]
                tmp = u"%d barcodes assigned to %s, please wait for download."
                msg = tmp % (num_barcodes, ", ".join(projects))

        else:
            raise HTTPError(400, 'Unknown action: %s' % action)

        project_names = db.getProjectNames()
        remaining = len(db.get_unassigned_barcodes())
        self.render("ag_new_barcode.html", currentuser=self.current_user,
                    projects=project_names, remaining=remaining,
                    msg=msg, newbc=newbc, assignedbc=assignedbc,
                    assign_projects=", ".join(projects))

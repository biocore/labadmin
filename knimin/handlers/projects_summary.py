#!/usr/bin/env python
from tornado.web import authenticated
from tornado.escape import xhtml_escape
from knimin.handlers.base import BaseHandler
from knimin.handlers.access_decorators import set_access
from knimin import db


@set_access(['Base'])
class ProjectsSummaryHandler(BaseHandler):
    @authenticated
    def get(self):
        projects = db.getProjectNames()
        # escape unicode project names for xhtml rendering
        info = [(xhtml_escape(p), len(db.get_barcodes_for_projects([p])))
                for p in projects]
        self.render('projects_summary.html', proj_counts=info)

#!/usr/bin/env python
from tornado.web import authenticated
from knimin.handlers.base import BaseHandler
from knimin import db
from knimin.handlers.access_decorators import set_access

"""
This page displays a list of plates (sample, DNA, protocol, run)
Columns:
ID, name, by, on, DNA plate (link), [view/edit]
view/edit (direct click)
set atts (multiple) (for DNA plates only)
"""


@set_access(['Admin'])
class PMPlateListHandler(BaseHandler):
    @authenticated
    def get(self):
        plates = [list(x) for x in db.get_plate_list()]
        for i in range(len(plates)):
            for j in range(len(plates[i])):
                if type(plates[i][j]) is long:
                    plates[i][j] = int(plates[i][j])
        self.render("pm_plate_list.html", currentuser=self.current_user,
                    plates=plates)

    @authenticated
    def post(self):
        action = self.get_argument("action")
        if action == 'migrate':
            db.migrate_data()

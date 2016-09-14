#!/usr/bin/env python
from tornado.web import authenticated
from knimin.handlers.base import BaseHandler
from knimin import db
from knimin.handlers.access_decorators import set_access


@set_access(['Admin'])
class PMPlateListHandler(BaseHandler):
    @authenticated
    def get(self):
        items = self.get_argument("items", default="10")
        pageno = self.get_argument("pageno", default="1")
        total = db.get_plate_total()
        plates = []
        for x in db.get_plate_info(items, int(items)*(int(pageno)-1)):
            plates.append([int(x[0]), x[1], x[2], int(x[3])])
        self.render("pm_plate_list.html", currentuser=self.current_user,
                    items=items, pageno=pageno, total=total, plates=plates)

    @authenticated
    def post(self):
        action = self.get_argument("action")
        if action == 'migrate':
            db.migrate_data()

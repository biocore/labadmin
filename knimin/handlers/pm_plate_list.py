#!/usr/bin/env python
from tornado.web import authenticated
from knimin.handlers.base import BaseHandler
from knimin import db
from knimin.handlers.access_decorators import set_access


@set_access(['Admin'])
class PMPlateListHandler(BaseHandler):
    @authenticated
    def get(self):
        items = self.get_argument("items", default=10)
        pageno = self.get_argument("pageno", default=1)
        total = db.get_plate_count()
        plates = [list(x) for x in db.get_plate_list(items,
                  int(items)*(int(pageno)-1))]
        for i in range(len(plates)):
            for j in range(len(plates[i])):
                if type(plates[i][j]) is long:
                    plates[i][j] = int(plates[i][j])
        self.render("pm_plate_list.html", currentuser=self.current_user,
                    items=items, pageno=pageno, total=total, plates=plates)

    @authenticated
    def post(self):
        action = self.get_argument("action")
        if action == 'migrate':
            db.migrate_data()

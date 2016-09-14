#!/usr/bin/env python
from tornado.web import authenticated
from knimin.handlers.base import BaseHandler
from knimin import db
from knimin.handlers.access_decorators import set_access


@set_access(['Admin'])
class PMPlateMapHandler(BaseHandler):
    @authenticated
    def get(self):
        id = self.get_argument("id", default="1")
        if int(id) > 0:
            # view/edit an existing plate (id>0)
            type = db.get_plate_type(id)
            type[0] = int(type[0])
            map = db.get_plate_map(id)
            self.render("pm_plate_map.html", currentuser=self.current_user,
                        id=id, type=type, map=map)
        else:
            # create a new plate (id=0)
            type = db.get_default_plate_type()
            type[0] = int(type[0])
            self.render("pm_plate_map.html", currentuser=self.current_user,
                        id=id, type=type, map=None)

    @authenticated
    def post(self):
        action = self.get_argument("action")
        if action == 'create':
            # do something
            self.render("pm_plate_map.html", currentuser=self.current_user,
                        plate_ids=plate_ids, plate_id=plate_id,
                        plate_details=plate_details)
        # elif action == 'modify':
            # do something

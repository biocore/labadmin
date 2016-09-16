#!/usr/bin/env python
from tornado.web import authenticated
from knimin.handlers.base import BaseHandler
from knimin import db
from knimin.handlers.access_decorators import set_access


@set_access(['Admin'])
class PMPlateMapHandler(BaseHandler):
    @authenticated
    def get(self):
        id = int(self.get_argument("id", default="1"))
        plate_type = db.get_plate_type(id)
        plate_type['plate_type_id'] = int(plate_type['plate_type_id'])
        plate_map = db.get_plate_map(id)
        plate_info = {}
        if id:
            plate_info = db.get_plate_info(id)
            plate_info = {key: value for key, value in plate_info.items()
                          if value}
            for i in plate_info:
                if type(plate_info[i]) is long:
                    plate_info[i] = int(plate_info[i])
        self.render("pm_plate_map.html", currentuser=self.current_user,
                    id=id, type=plate_type, info=plate_info, map=plate_map)

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

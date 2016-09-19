#!/usr/bin/env python
from tornado.web import authenticated
from tornado.escape import json_encode
from knimin.handlers.base import BaseHandler
from knimin import db
from knimin.handlers.access_decorators import set_access


@set_access(['Admin'])
class PMPlateMapHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_id = int(self.get_argument("id", default="1"))
        plate_count = int(db.get_plate_count())
        if plate_id == -1:
            plate_id = plate_count
        plate_type = db.get_plate_type(plate_id)
        plate_type['plate_type_id'] = int(plate_type['plate_type_id'])
        plate_map = [list(x) for x in db.get_plate_map(plate_id)]
        plate_info = {}
        if plate_id:
            plate_info = list(db.get_plate_info(plate_id))
            # plate_info = {key: value for key, value in plate_info.items()
            #              if value}
            for i in range(len(plate_info)):
                if plate_info[i] is None:
                    plate_info[i] = ''
                if type(plate_info[i]) is long:
                    plate_info[i] = int(plate_info[i])
        self.render("pm_plate_map.html", currentuser=self.current_user,
                    id=plate_id, type=plate_type, info=plate_info,
                    map=plate_map)

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

# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from tornado.web import authenticated
from tornado.escape import json_decode

from knimin.handlers.base import BaseHandler
from knimin.handlers.access_decorators import set_access
from knimin import db


@set_access(['Admin'])
class PMPoolPlatesHandler(BaseHandler):
    @authenticated
    def get(self):
        plates_arg = map(int, self.get_arguments('plate'))

        all_plates = []
        plates = []
        for plate in db.get_targeted_plate_list():
            plate['date'] = plate['date'].isoformat()
            all_plates.append(plate)
            if plate['id'] in plates_arg:
                plates.append(plate)

        self.render("pm_targeted_pool.html", all_plates=all_plates,
                    plates=plates)

    @authenticated
    def post(self):
        pools = json_decode(self.get_argument('pools'))
        name = self.get_argument('name')
        volume = self.get_argument('volume')

        pool_id = db.pool_plates(pools, name, volume)
        self.redirect("/pm_sequence/?pool_id=%s" % pool_id)

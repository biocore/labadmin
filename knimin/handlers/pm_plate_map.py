# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from tornado.web import authenticated

from knimin import db
from knimin.handlers.base import BaseHandler
from knimin.handlers.access_decorators import set_access


@set_access(['Admin'])
class PMCreatePlateHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_types = db.get_plate_types()
        studies = db.get_studies()
        self.render("pm_create_plate.html", currentuser=self.current_user,
                    plate_types=plate_types, studies=studies)

    @authenticated
    def post(self):
        plate_type = self.get_argument('plate_type')
        studies = self.get_argument('studies').split(',')
        plate_name = self.get_argument('plate_name')
        user = self.current_user
        plate_id = db.create_sample_plate(plate_name, plate_type,
                                          user, studies)
        self.redirect('/pm_plate_map/%d/' % plate_id)


@set_access(['Admin'])
class PMPlateNameCheckerHandler(BaseHandler):
    @authenticated
    def get(self):
        name = self.get_argument('name')
        self.write({'result': db.sample_plate_name_exists(name)})
        self.finish()

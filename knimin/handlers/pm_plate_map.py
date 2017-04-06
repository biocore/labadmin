# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

import re

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
        self.redirect('/pm_plate_map?plate_id=%d' % plate_id)


@set_access(['Admin'])
class PMPlateNameCheckerHandler(BaseHandler):
    @authenticated
    def get(self):
        name = self.get_argument('name')
        res = db.sample_plate_name_exists(name)
        code = 200 if res else 404
        self.write({'result': res})
        self.set_status(code)
        self.finish()


@set_access(['Admin'])
class PMPlateMapHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_id = self.get_argument('plate_id')
        self.render("pm_plate_map.html", currentuser=self.current_user,
                    plate_id=plate_id)


@set_access(['Admin'])
class PMSamplePlateHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_id = self.get_argument('plate_id')

        # Retrieve the plate information, taking into account that the given
        # id may not exist in the DB
        try:
            plate_info = db.read_sample_plate(plate_id)
        except ValueError as e:
            if re.match('Sample plate ID [0-9]* does not exist', e.message):
                self.set_status(404)
                self.write({'message': e.message})
                self.finish()
                return
            # If there has been any other error, simply re-raise it
            raise

        # Format the output dictionary to contain a bit more information
        # instead of the different objects ids
        plate_info['plate_type'] = dict(db.read_plate_type(
            plate_info.pop('plate_type_id')))

        studies = []
        for s_id in plate_info['studies']:
            study = db.read_study(s_id)
            study['samples'] = {}
            study['samples']['all'] = db.get_study_samples(s_id)
            study['samples']['plated'] = db.get_study_plated_samples(s_id)
            studies.append(study)

        plate_info['studies'] = studies

        plate_info['plate_id'] = plate_id
        plate_info['created_on'] = plate_info['created_on'].isoformat(sep=' ')

        self.write(plate_info)
        self.finish()

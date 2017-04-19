# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

import re

from tornado.web import authenticated, HTTPError
from tornado.escape import json_decode

from knimin import db
from knimin.lib.qiita_jira_util import sync_qiita_study_samples
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

    @authenticated
    def post(self):
        plate_id = self.get_argument('plate_id')
        action = self.get_argument('action')
        layout = json_decode(self.get_argument('layout'))

        if action not in ('save', 'extract'):
            raise HTTPError(400, 'Action should be save or extract')
        else:
            # In any of the two cases we need to save the plate layout
            db.write_sample_plate_layout(plate_id, layout)

            if action == 'save':
                # At this point we are done! Simply return a 200
                self.set_status(200)
                self.finish()
            elif action == 'extract':
                # The plate is promoted for extraction
                self.redirect("/pm_extract_plate?plate_id=%s" % plate_id)


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
            # Make sure to sync the samples with Qiita
            sync_qiita_study_samples(s_id)
            study = db.read_study(s_id)
            study['samples'] = {}
            study['samples']['all'] = db.get_study_samples(s_id)
            study['samples']['plated'] = db.get_study_plated_samples(s_id)
            # Remove the entry for the current plate if it exists
            # Note: casting to long because the keys in the dictionary are
            # longs, so we need the cast to safely remove the entry
            study['samples']['plated'].pop(long(plate_id), None)
            studies.append(study)

        plate_info['studies'] = studies

        plate_info['plate_id'] = plate_id
        plate_info['created_on'] = plate_info['created_on'].isoformat(sep=' ')
        plate_info['layout'] = db.read_sample_plate_layout(plate_id)
        plate_info['blanks'] = db.get_blanks()

        self.write(plate_info)
        self.finish()


@set_access(['Admin'])
class PMExtractPlateHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_id = self.get_argument('plate_id')
        plate_name = db.read_sample_plate(plate_id)['name']
        plates = [[p['id'], p['name']] for p in db.get_sample_plate_list()]
        robots = db.get_property_options('extraction_robot')
        tools = db.get_property_options('extraction_tool')
        kits = db.get_property_options('extraction_kit_lot')

        self.render("pm_extract_plate.html", currentuser=self.get_current_user,
                    plate_id=plate_id, plate_name=plate_name, plates=plates,
                    robots=robots, tools=tools, kits=kits)

    @authenticated
    def post(self):
        plates = json_decode(self.get_argument('plates'))
        robot = self.get_argument('robot')
        tool = self.get_argument('tool')
        kit = self.get_argument('kit')
        user = self.current_user

        db.extract_sample_plates(plates, user, robot, kit, tool)

        self.redirect("/pm_plate_list/")

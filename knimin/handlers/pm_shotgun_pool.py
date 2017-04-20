# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

import datetime

from tornado.web import authenticated

from knimin import db
from knimin.handlers.base import BaseHandler
from knimin.handlers.access_decorators import set_access
from knimin.lib.parse import parse_qpcr_object
from knimin.lib.format import format_pooling_echo_pick_list
from knimin.lib.shotgun import (compute_qpcr_concentration,
                                compute_shotgun_pooling_values_qpcr)


@set_access(['Admin'])
class PMShotgunPool(BaseHandler):
    @authenticated
    def get(self):
        plate_id = int(self.get_argument('plate_id'))

        res = db.read_normalized_shotgun_plate(plate_id)
        machines = db.get_property_options('qpcr')

        # normalized shotgun plates do not have a name, we need to fetch the
        # name from the non-normalized table
        res = db.read_shotgun_plate(res['shotgun_plate_id'])

        # echo is the name of the plate
        self.render('pm_shotgun_pool.html', name=res['name'],
                    plate_id=plate_id, machines=machines)

    @authenticated
    def post(self):
        plate_id = self.get_argument('plate-id')
        plate_name = self.get_argument('plate-name')

        min_conc = float(self.get_argument('minimum-concentration'))
        floor_conc = float(self.get_argument('floor-concentration'))
        total_nmol = float(self.get_argument('total-quantity'))
        qpcr_machine = self.get_argument('qpcr-machine')

        file_contents = self.request.files['qpcr-readout-fp'][0]['body']

        qpcr_data = parse_qpcr_object(file_contents)
        qpcr_concentrations = compute_qpcr_concentration(qpcr_data)

        # not sure this is the function that needs to be used here
        sample_vols = compute_shotgun_pooling_values_qpcr(
            qpcr_concentrations, min_conc=min_conc, floor_conc=floor_conc,
            total_nmol=total_nmol)

        content = format_pooling_echo_pick_list(sample_vols)

        db.qpcr_shotgun(plate_id, self.get_current_user(), qpcr_machine, '',
                        qpcr_data, qpcr_concentrations)

        # setup a unique filename
        file_name = "echo_pool_%s_%s_%s.csv" % (
            plate_id, plate_name.replace(' ', '.'),
            datetime.datetime.today().strftime('%Y_%m_%d'))

        self.set_header('Content-Type', 'application/octet-stream')
        self.set_header('Content-Disposition',
                        'attachment; filename=' + file_name)
        self.write(content)
        self.flush()
        self.finish()

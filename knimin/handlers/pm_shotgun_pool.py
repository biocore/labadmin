# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from knimin import db
from knimin.handlers.base import BaseHandler
from knimin.handlers.access_decorators import set_access
from knimin.lib.parse import parse_qpcr_object
from knimin.lib.shotgun import compute_qpcr_concentration


@set_access(['Admin'])
class PMShotgunPool(BaseHandler):
    @authenticated
    def get(self):
        plate_id = int(self.get_argument('plate_id'))

        res = db.read_normalized_shotgun_plate(plate_id)

        # echo is the name of the plate
        self.render('pm_shotgun_pool.html', name=res['echo'],
                    plate_id=plate_id)

    @authenticated
    def post(self):

        min_conc = self.get_argument('minimum-concentration')
        floor_conc = self.get_argument('floor-concentration')
        total_nmol = self.get_argument('total-quantity')

        file_contents = self.request.files['qpcr-readout-fp'][0]['body']
        qpcr_data = parse_qpcr_object(file_contents)

        # not sure this is the function that needs to be used here
        sample_vols = compute_shotgun_pooling_values_qpcr(
            qpcr_data, min_conc=min_conc, floor_conc=floor_conc,
            total_nmol=total_nmol)

        # what do we do now with the sample volumes?

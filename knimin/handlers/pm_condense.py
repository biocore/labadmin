# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from tornado.web import authenticated

from knimin.handlers.base import BaseHandler
from knimin.handlers.access_decorators import set_access
from knimin import db


@set_access(['Admin'])
class PMCondensePlatesHandler(BaseHandler):
    @authenticated
    def get(self):
        dna_plates = db.get_dna_plate_list()
        for plate in dna_plates:
            plate['date'] = plate['date'].isoformat()

        self.render("pm_condense.html",
                    plates=dna_plates,
                    robots=db.get_property_options("processing_robot"))

    @authenticated
    def post(self):
        plate1 = self.get_argument('plate-1')
        plate2 = self.get_argument('plate-2')
        plate3 = self.get_argument('plate-3')
        plate4 = self.get_argument('plate-4')
        name = self.get_argument('name')
        robot = self.get_argument('robot')
        volume = self.get_argument('volume')

        dna_plates = [(plate1, 0), (plate2, 1), (plate3, 2), (plate4, 3)]
        plates = [plate1, plate2, plate3, plate4]
        pos = [0, 1, 2, 3]
        dna_plates = [(p, idx) for p, idx in zip(plates, pos) if p]
        # Magic number 2 -> The only supported plate type here is
        # a 384-well plate
        plate_id = db.condense_dna_plates(
            dna_plates, name, self.get_current_user(), robot, 2, volume)

        self.redirect("/pm_normalize/?plate=%s" % plate_id)

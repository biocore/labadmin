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
class PMTargetGeneLibraryPrepHandler(BaseHandler):
    @authenticated
    def get(self):
        dna_plates = db.get_dna_plate_list()
        for plate in dna_plates:
            plate['date'] = plate['date'].isoformat()

        self.render("pm_target_gene_library_prep.html",
                    dna_plates=dna_plates,
                    primer_plates=db.get_targeted_primer_plates(),
                    robots=db.get_property_options("processing_robot"),
                    tm300tools=db.get_property_options("tm300_8_tool"),
                    tm50tools=db.get_property_options("tm50_8_tool"),
                    mastermixlots=db.get_property_options("master_mix_lot"),
                    waterlots=db.get_property_options("water_lot"))

    @authenticated
    def post(self):
        plates = json_decode(self.get_argument('plates'))
        robot = self.get_argument('robot')
        tm300 = self.get_argument('tm300')
        tm50 = self.get_argument('tm50')
        master_mix = self.get_argument('master_mix')
        water = self.get_argument('water')
        user = self.current_user

        plate_ids = db.prepare_targeted_libraries(
            plates, user, robot, tm300, tm50, master_mix, water)

        self.redirect(
            "/pm_pool_plates/?%s"
            % "&".join(["plate=%d" % pid for pid in plate_ids]))


@set_access(['Admin'])
class PMMetagenomicsLibraryPrepHandler(BaseHandler):
    @authenticated
    def get(self):
        self.render("pm_metagenomics_library_prep.html")

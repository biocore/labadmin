# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from datetime import date

from tornado.web import authenticated
from tornado.escape import json_decode

from knimin.handlers.base import BaseHandler
from knimin.handlers.access_decorators import set_access
from knimin import db
from knimin.lib.qiita_jira_util import prepare_targeted_libraries
from knimin.lib.shotgun import prepare_shotgun_libraries
from knimin.lib.format import format_index_echo_pick_list


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

        plate_ids = prepare_targeted_libraries(
            plates, user, robot, tm300, tm50, master_mix, water)

        self.redirect(
            "/pm_targeted_concentration/?%s"
            % "&".join(["plate=%d" % pid for pid in plate_ids]))


@set_access(['Admin'])
class PMMetagenomicsLibraryPrepHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_id = self.get_argument('plate')

        plate = db.read_normalized_shotgun_plate(plate_id)
        plate['name'] = db.read_shotgun_plate(
            plate['shotgun_plate_id'])['name']

        self.render("pm_metagenomics_library_prep.html",
                    plate=plate,
                    idx_protocols=db.get_shotgun_index_technology_list(),
                    mosquitos=db.get_property_options('mosquito'),
                    library_kits=db.get_property_options(
                        'shotgun_library_prep_kit'),
                    aliquots=db.get_property_options(
                        'shotgun_index_aliquot'))

    @authenticated
    def post(self):
        plate_id = self.get_argument('plate-id')
        mosquito = self.get_argument('mosquito')
        kit = self.get_argument('kit')
        aliquot = self.get_argument('aliquot')
        idx_tech = self.get_argument('idx-tech')

        prepare_shotgun_libraries(plate_id, self.get_current_user(), mosquito,
                                  kit, aliquot, idx_tech)

        self.set_status(200)
        self.finish()


@set_access(['Admin'])
class PMMetagenomicsLibraryPrepEchoHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_id = self.get_argument('plate_id')
        volume = float(self.get_argument('volume'))

        plate = db.read_normalized_shotgun_plate(plate_id)
        plate['name'] = db.read_shotgun_plate(
            plate['shotgun_plate_id'])['name']

        contents = format_index_echo_pick_list(plate['shotgun_index'], volume)
        file_name = "echo_index_PickList_%s_%s_%s.csv" % (
            plate['shotgun_normalized_plate_id'], plate['name'],
            date.today().strftime('%Y_%m_%d'))

        self.set_header('Content-Type', 'application/octet-stream')
        self.set_header('Content-Disposition',
                        'attachment; filename=' + file_name)
        self.write(contents)
        self.finish()

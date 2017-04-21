# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from tornado.web import authenticated
from datetime import date

from knimin.handlers.base import BaseHandler
from knimin.handlers.access_decorators import set_access
from knimin import db
from knimin.lib.parse import parse_plate_reader_output
from knimin.lib.format import format_normalization_echo_pick_list
from knimin.lib.shotgun import compute_shotgun_normalization_values


@set_access(['Admin'])
class PMNormalizeHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_id = self.get_argument('plate')

        plate = db.read_shotgun_plate(plate_id)
        plate['created_on'] = plate['created_on'].isoformat(sep=' ')

        condensed = plate['condensed_plates']
        plate['condensed_plates'] = []
        for pid, pos in condensed:
            p = db.read_dna_plate(pid)
            p['created_on'] = p['created_on'].isoformat(sep=' ')
            plate['condensed_plates'].append((pos, p))

        self.render("pm_normalize.html", plate=plate,
                    plate_readers=db.get_property_options("plate_reader"),
                    echos=db.get_property_options("echo"))

    @authenticated
    def post(self):
        plate_id = self.get_argument("plate_id")
        input_vol = self.get_argument("pm-volume")
        input_dna = self.get_argument("pm-dna-input")
        upload_type = self.get_argument("upload-select")
        plate_reader = self.get_argument("plate-reader")
        echo = self.get_argument("echo")

        if upload_type == 'Single file':
            qubit_assay = self.request.files['single-plate-fp'][0]['body']
            dna_conc = parse_plate_reader_output(qubit_assay)
            cond_dna_conc = None
        else:
            dna_conc = None
            cond_dna_conc = [
                parse_plate_reader_output(
                    self.request.files['plate-%d-fp' % i][0]['body'])
                for i in range(4)]

        db.quantify_shotgun_plate(plate_id, self.get_current_user(),
                                  input_vol, plate_reader, dna_conc,
                                  cond_dna_conc)

        plate = db.read_shotgun_plate(plate_id)
        vol_sample, vol_water = compute_shotgun_normalization_values(
            plate['shotgun_plate_layout'], input_vol, input_dna)

        norm_plate_id = db.normalize_shotgun_plate(
            plate_id, self.get_current_user(), echo, vol_sample, vol_water)

        self.write({'norm_plate_id': norm_plate_id})
        self.finish()


@set_access(['Admin'])
class PMNormalizeEchoFileHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_id = self.get_argument('plate_id')
        plate = db.read_normalized_shotgun_plate(plate_id)
        data = format_normalization_echo_pick_list(
            plate['plate_normalization_sample'],
            plate['plate_normalization_water'])

        sh_plate = db.read_shotgun_plate(plate['shotgun_plate_id'])

        file_name = "echo_norm_PickList_%s_%s_%s.csv" % (
            plate['shotgun_normalized_plate_id'], sh_plate['name'],
            date.today().strftime('%Y_%m_%d'))

        self.set_header('Content-Type', 'application/octet-stream')
        self.set_header('Content-Disposition',
                        'attachment; filename=' + file_name)
        self.write(data)
        self.finish()

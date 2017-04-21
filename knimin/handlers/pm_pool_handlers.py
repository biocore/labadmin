# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from tornado.web import authenticated
from tornado.escape import json_decode
from datetime import date

import numpy as np

from knimin.lib.parse import parse_plate_reader_output
from knimin.lib.format import format_epmotion_file
from knimin.handlers.base import BaseHandler
from knimin.handlers.access_decorators import set_access
from knimin import db


def _get_targeted_plates(plates_arg):
    """Retrieve the targeted plates

    This function is done simply to avoid looping the plate list twice
    and to avoid code duplication

    Parameters
    ----------
    plates_arg : list of int
        The list of id

    Returns
    -------
    list of dict, list of dict
        A list with all plates info and a list with the requested plates info
    """
    plates_arg = set(plates_arg)
    all_plates = []
    plates = []
    for plate in db.get_targeted_plate_list():
        plate['date'] = plate['date'].isoformat()
        all_plates.append(plate)
        if plate['id'] in plates_arg:
            plates.append(plate)

    return all_plates, plates


def _get_quantified_targeted_plates(plates_arg):
    """Retrieve the quantified targeted plates

    This function is done simply to avoid looping the plate list twice
    and to avoid code duplication

    Parameters
    ----------
    plates_arg : list of int
        The list of id

    Returns
    -------
    list of dict, list of dict
        A list with all plates info and a list with the requested plates info
    """
    plates_arg = set(plates_arg)
    all_plates = []
    plates = []
    for plate in db.get_quantified_targeted_plate_list():
        plate['date'] = plate['date'].isoformat()
        plate['primer_plate'] = db.read_targeted_plate(
            plate['id'])['primer_plate_id']
        all_plates.append(plate)
        if plate['id'] in plates_arg:
            plates.append(plate)

    return all_plates, plates


def _get_clean_targeted_plate_data(plate_id):
    """Retrieves the targeted plate information

    We need to make sure that the information sent to the handler is JSONized

    Parameters
    ----------
    plate_id : int
        The plate identifier

    Returns
    -------
    dict
        The plate information
    """
    # Get the plate information
    plate = db.read_targeted_plate(plate_id)
    dna_plate = db.read_dna_plate(plate['dna_plate_id'])
    sample_plate = db.read_sample_plate(dna_plate['sample_plate_id'])
    # Get the blanks
    plate['blanks'] = db.get_blanks_from_sample_plate(
        dna_plate['sample_plate_id'])
    # Get the plate size
    plate_type = dict(
        db.read_plate_type(sample_plate['plate_type_id']))
    plate['rows'] = plate_type['rows']
    plate['cols'] = plate_type['cols']
    # The raw files have only 3 decimals, so the extra decimals is just
    # an artifact of the machine. Rounding them to 3 decimals
    plate['raw_concentration'] = np.around(
        plate['raw_concentration'], decimals=3).tolist()
    if plate['mod_concentration'] is not None:
        plate['mod_concentration'] = np.around(
            plate['mod_concentration'], decimals=3).tolist()
    # Datetime is not JSON serializable
    plate['created_on'] = plate['created_on'].isoformat()

    return plate


@set_access(['Admin'])
class PMTargetedConcentrationHandler(BaseHandler):
    @authenticated
    def get(self):
        plates_arg = map(int, self.get_arguments('plate'))
        all_plates, plates = _get_targeted_plates(plates_arg)

        self.render("pm_targeted_concentration.html", all_plates=all_plates,
                    plates=plates)

    @authenticated
    def post(self):
        plates = self.get_arguments('plate')

        file_contents = self.request.files['plate-reader-fp'][0]['body']
        plate_reader_data = parse_plate_reader_output(file_contents)

        for p, d in zip(plates, [plate_reader_data]):
            db.quantify_targeted_plate(p, 'raw_concentration', d)

        self.redirect(
            "/pm_targeted_concentration_check/?%s"
            % "&".join(["plate=%s" % pid for pid in plates]))


@set_access(['Admin'])
class PMTargetedConcentrationCheckHandler(BaseHandler):
    @authenticated
    def get(self):
        plates_arg = map(int, self.get_arguments('plate'))

        plates = []
        for p_id in plates_arg:
            plate = _get_clean_targeted_plate_data(p_id)
            plates.append(plate)

        self.render("pm_targeted_concentration_check.html", plates=plates)

    @authenticated
    def post(self):
        plates = json_decode(self.get_argument('plates'))

        for plate in plates:
            db.quantify_targeted_plate(
                plate['id'], 'mod_concentration',
                np.asarray(plate['mod_concentration'], dtype=np.float))

        self.redirect("/pm_targeted_pool/?%s"
                      % "&".join(["plate=%s" % p['id'] for p in plates]))


@set_access(['Admin'])
class PMTargetedPoolEPMotionHandler(BaseHandler):
    @authenticated
    def post(self):
        plate = json_decode(self.get_argument('plate'))
        dest = self.get_argument('destination')

        plate['mod_concentration'] = np.asarray(
            plate['mod_concentration'], dtype=np.float)
        db.quantify_targeted_plate(plate['id'], 'mod_concentration',
                                   plate['mod_concentration'])

        data = format_epmotion_file(plate['mod_concentration'], dest)
        file_name = "EPMotion_%s_%s_%s.csv" % (
            plate['id'], plate['name'].replace(' ', '.'),
            date.today().strftime('%Y_%m_%d'))

        self.set_header('Content-Type', 'application/octet-stream')
        self.set_header('Content-Disposition',
                        'attachment; filename=' + file_name)
        self.write(data)
        self.flush()
        self.finish()


@set_access(['Admin'])
class PMTargetedPoolHandler(BaseHandler):
    @authenticated
    def get(self):
        plates_arg = map(int, self.get_arguments('plate'))
        all_plates, plates = _get_quantified_targeted_plates(plates_arg)

        self.render("pm_targeted_pool.html", all_plates=all_plates,
                    plates=plates)

    @authenticated
    def post(self):
        pools = json_decode(self.get_argument('pools'))
        name = self.get_argument('name')

        pool_id = db.pool_plates(pools, name)
        self.redirect('/pm_sequence/?pool_id=%s' % pool_id)

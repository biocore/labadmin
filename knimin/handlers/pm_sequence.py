# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------
from collections import defaultdict

from tornado.web import authenticated

from knimin.handlers.base import BaseHandler
from knimin.handlers.access_decorators import set_access
from knimin import db


@set_access(['Admin'])
class PMSequenceHandler(BaseHandler):
    @authenticated
    def get(self):
        pool_id = self.get_argument('pool_id')
        reagents = defaultdict(list)
        for r in db.get_reagent_kit_lots():
            reagent_type = r.pop('reagent_kit_type')
            reagents[reagent_type].append(r['name'])

        self.render("pm_sequence.html",
                    pool=db.read_pool(pool_id),
                    sequencers=db.get_sequencers(),
                    reagents=reagents)

    @authenticated
    def post(self):
        pool_id = self.get_argument('pool_id')
        sequencer = self.get_argument('sequencer')
        reagent_type = self.get_argument('reagent_kit_type')
        reagent_lot = self.get_argument('reagent_kit_lot')

        run_id = db.create_sequencing_run(
            pool_id, self.get_current_user(), sequencer,
            reagent_type, reagent_lot)
        run = db.read_sequencing_run(run_id)
        self.render("pm_sequence_success.html", run=run)

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
from knimin.lib.qiita_jira_util import (
    create_sequencing_run, complete_sequencing_run)


@set_access(['Admin'])
class PMSequenceHandler(BaseHandler):
    @authenticated
    def get(self):
        pool_id = self.get_argument('pool_id')

        self.render("pm_sequence.html",
                    pool=db.read_pool(pool_id))

    @authenticated
    def post(self):
        pool_id = self.get_argument('pool_id')
        platform = self.get_argument('platform')
        instrument_model = self.get_argument('instrument_model')
        assay = self.get_argument('assay')

        reagent_type = self.get_argument('reagent_type')
        reagent_lot = self.get_argument('reagent_lot')

        fwd_cycles = int(self.get_argument('fwd_cycles'))
        rev_cycles = int(self.get_argument('rev_cycles'))

        run_id, jira_links = create_sequencing_run(
            pool_id, self.get_current_user(), reagent_type, reagent_lot,
            platform, instrument_model, assay, fwd_cycles, rev_cycles)

        run = db.read_sequencing_run(run_id)
        self.render("pm_sequence_success.html", run=run, jira_links=jira_links)


@set_access(['Admin'])
class PMSequencingCompleteHandler(BaseHandler):
    @authenticated
    def post(self):
        run_id = self.get_argument('run_id')
        run_path = self.get_argument('run_path')
        exit_status = int(self.get_argument('exit_status'))
        logs = self.get_argument('logs', [])
        if logs:
            logs = json_decode(logs)

        complete_sequencing_run(exit_status == 0, run_id, run_path, logs)

        self.set_status(200)
        self.finish()

# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from tornado.web import authenticated
from tornado.escape import json_decode, json_encode

from knimin.handlers.base import BaseHandler
from knimin.handlers.access_decorators import set_access
from knimin.lib.qiita_jira_util import create_study
from knimin import qiita_client, db


@set_access(['Admin'])
class PMCreateStudyHandler(BaseHandler):
    @authenticated
    def get(self):
        _, qiita_persons = qiita_client.get('/api/v1/person')
        # We don't have an id for each person. "Create" one by jsonizing
        # the information of each person
        for q in qiita_persons:
            q['json'] = json_encode(q)

        self.render("pm_create_study.html", currentuser=self.current_user,
                    qiita_persons=qiita_persons)

    @authenticated
    def post(self):
        qiita_user = self.get_argument('qiita-user')
        jira_user = self.get_argument('jira-user')
        title = self.get_argument('study-title')
        alias = self.get_argument('study-alias')
        description = self.get_argument('study-description')
        abstract = self.get_argument('study-abstract')
        qiita_pi = json_decode(self.get_argument('qiita-pi'))
        qiita_lp = json_decode(self.get_argument('qiita-lp'))

        study_id = create_study(title, abstract, description, alias,
                                qiita_user, qiita_pi, qiita_lp, jira_user)
        study = db.read_study(study_id)

        self.render("pm_study_created.html", current_user=self.current_user,
                    title=title, study_id=study_id, jira_key=study['jira_id'])

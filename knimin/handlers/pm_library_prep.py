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


@set_access(['Admin'])
class PMTargetGeneLibraryPrepHandler(BaseHandler):
    @authenticated
    def get(self):
        self.render("pm_target_gene_library_prep.html")


@set_access(['Admin'])
class PMMetagenomicsLibraryPrepHandler(BaseHandler):
    @authenticated
    def get(self):
        self.render("pm_metagenomics_library_prep.html")

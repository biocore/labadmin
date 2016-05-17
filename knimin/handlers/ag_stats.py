#!/usr/bin/env python
from knimin.handlers.base import BaseHandler
from knimin.handlers.access_decorators import set_access
from tornado.web import authenticated

from knimin import db


@set_access(['Base'])
class AGStatsHandler(BaseHandler):
    @authenticated
    def get(self):
        stats = db.getAGStats()
        for item, stat in stats:
            stat = '' if stat is None else stat
        self.render("ag_stats.html", stats=stats, loginerror='')

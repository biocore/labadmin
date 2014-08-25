#!/usr/bin/env python
from knimin.handlers.base import BaseHandler

from amgut.util import AG_DATA_ACCESS


class AGStatsHandler(BaseHandler):
    def get(self):
        stats = AG_DATA_ACCESS.getAGStats()
        for item, stat in stats:
            stat = '' if stat is None else stat
        self.render("ag_stats.html", stats=stats, loginerror='')

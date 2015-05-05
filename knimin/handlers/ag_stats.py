#!/usr/bin/env python
from knimin.handlers.base import BaseHandler

from amgut.connections import ag_data


class AGStatsHandler(BaseHandler):
    def get(self):
        stats = ag_data.getAGStats()
        for item, stat in stats:
            stat = '' if stat is None else stat
        self.render("ag_stats.html", stats=stats, loginerror='')

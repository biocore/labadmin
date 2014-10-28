#!/usr/bin/env python
from tornado.web import authenticated
from knimin.handlers.base import BaseHandler

from amgut.util import AG_DATA_ACCESS


class AGUpdateGeocodeHandler(BaseHandler):
    @authenticated
    def get(self):
        stats = AG_DATA_ACCESS.getGeocodeStats()
        self.render("ag_update_geocode.html", stats=stats,
                    currentuser=self.current_user)

    @authenticated
    def post(self):
        retry = int(self.get_argument("retry", 0))
        limit = int(self.get_argument('limit', -1))
        limit = None if limit == -1 else limit
        AG_DATA_ACCESS.addGeocodingInfo(limit, retry)
        stats = AG_DATA_ACCESS.getGeocodeStats()

        self.render("ag_update_geocode.html", stats=stats,
                    currentuser=self.current_user)

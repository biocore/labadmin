#!/usr/bin/env python
from knimin.handlers.base import BaseHandler


class LoggedInIndexHandler(BaseHandler):
    def get(self):
        self.render("logged_in_index.html", loginerror='')

    def post(self):
        self.render("logged_in_index.html", loginerror='')

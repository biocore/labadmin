#!/usr/bin/env python
from tornado.web import authenticated
from knimin.handlers.base import BaseHandler
from knimin.handlers.access_decorators import set_access


@set_access(['Base'])
class LoggedInIndexHandler(BaseHandler):
    @authenticated
    def get(self):
        self.render("logged_in_index.html", currentuser=self.current_user)

    @authenticated
    def post(self):
        self.render("logged_in_index.html", currentuser=self.current_user)

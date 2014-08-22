#!/usr/bin/env python

from tornado.escape import json_encode

from knimin import db
from knimin.handlers.base import BaseHandler

# login code modified from https://gist.github.com/guillaumevincent/4771570


class AuthLoginHandler(BaseHandler):
    """user login, no page necessary"""
    def post(self):
        user = self.get_argument("user", "").strip()
        password = self.get_argument("password", "")
        login = db.authenticate_user(user, password)

        if login:
            self.set_current_user(user)
            self.redirect("/")
        else:
            msg = "Invalid username or password"
            self.render("index.html", user=None, loginerror=msg)

    def set_current_user(self, user):
        if user:
            self.set_secure_cookie("user", json_encode(user))
        else:
            self.clear_cookie("user")


class AuthLogoutHandler(BaseHandler):
    """Logout handler, no page necessary"""
    def get(self):
        self.clear_cookie("user")
        self.redirect("/")

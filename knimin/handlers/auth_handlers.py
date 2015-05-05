#!/usr/bin/env python

from tornado.escape import json_encode

from knimin import db
from knimin.lib.data_access import IncorrectEmailError, IncorrectPasswordError
from knimin.handlers.base import BaseHandler

# login code modified from https://gist.github.com/guillaumevincent/4771570

# ARP, 17 Feb 2015: Modified from qiita handlers from repo version
# d3984140ab3db185920f473710da53c2587aee49


class AuthLoginHandler(BaseHandler):
    """user login, no page necessary"""
    def get(self):
        self.redirect("/")

    def post(self):
        email = self.get_argument("email", "").strip().lower()
        password = self.get_argument("password", "")

        msg = "Unknown error"

        success = False
        try:
            success = db.authenticate_user(email, password)
        except IncorrectEmailError:
            msg = "Unknown user"
        except IncorrectPasswordError:
            msg = "Incorrect password"

        if success:
            # everything good so log in
            self.set_current_user(email)
            self.redirect("/logged_in_index/")
        else:
            self.render("index.html", loginerror=msg)

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

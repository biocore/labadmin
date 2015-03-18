#!/usr/bin/env python

from tornado.escape import json_encode
from tornado.web import HTTPError

from qiita_db.user import User
from qiita_db.exceptions import QiitaDBUnknownIDError, QiitaDBDuplicateError

# login code modified from https://gist.github.com/guillaumevincent/4771570

# ARP, 17 Feb 2015: Modified from qiita handlers from repo version
# d3984140ab3db185920f473710da53c2587aee49


class AuthLoginHandler(BaseHandler):
    """user login, no page necessary"""
    def get(self):
        self.redirect("/")

    def post(self):
        username = self.get_argument("username", "").strip().lower()
        passwd = self.get_argument("password", "")

        msg = ""

        login = None
        # check the user level
        try:
            if User(username).level == "unverified":
                # email not verified so dont log in
                msg = "Email not verified"
        except QiitaDBUnknownIDError:
            msg = "Unknown user"
        except RuntimeError:
            # means DB not available, so set maintenance mode and failover
            msg = ("Cannot reach database. Please contact Daniel, Adam, "
                   "and/or Jeff")
        else:
            # Check the login information
            try:
                login = User.login(username, passwd)
            except IncorrectEmailError:
                msg = "Unknown user"
            except IncorrectPasswordError:
                msg = "Incorrect password"

        if login is not None:
            # everything good so log in
            self.set_current_user(username)
            self.redirect('/')
        else:
            self.render("index.html", message=msg, level='danger')

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

#!/usr/bin/env python
from tornado.web import authenticated
from knimin.handlers.base import BaseHandler
from knimin.handlers.access_decorators import set_access

from knimin import db


@set_access(['Admin'])
class AGEditAccessHandler(BaseHandler):
    @authenticated
    def get(self):
        user = self.get_argument('user', None)
        all_levels = []
        user_levels = []
        if user is not None:
            all_levels = db.get_access_levels()
            user_levels = db.get_access_levels_user(user)
        users = db.get_users()

        self.render('edit_user.html', all_levels=all_levels,
                    user_levels=user_levels, users=users, user=user, msg='')

    @authenticated
    def post(self):
        msg = 'Access levels updated'
        access_levels = [int(x) for x in self.get_arguments('levels')]
        user = self.get_argument('user')
        try:
            db.alter_access_levels(user, access_levels)
        except Exception as e:
            msg = 'ERROR: %s' % str(e)

        all_levels = db.get_access_levels()
        user_levels = db.get_access_levels_user(user)
        users = db.get_users()
        self.render('edit_user.html', all_levels=all_levels,
                    user_levels=user_levels, users=users, user=user,
                    msg=msg)

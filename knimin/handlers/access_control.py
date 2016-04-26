#!/usr/bin/env python
from tornado.web import authenticated
from knimin.handlers.base import BaseHandler
from knimin.handlers.access_decorators import set_access

from knimin import db


@set_access(['Admin'])
class AGEditAccessHandler(BaseHandler):
    @authenticated
    def get(self):
        all_levels = db.get_access_levels()
        user_levels = db.get_access_levels_user(self.current_user)

        self.render('edit_user.html', all_levels=all_levels,
                    user_levels=user_levels)

    @authenticated
    def post(self):
        access_levels = self.get_arguments('levels')
        try:
            db.alter_access(self.current_user, access_levels)
        except Exception as e:
            self.write('ERROR: %s' % str(e))
            return
        self.write('Access levels updated')

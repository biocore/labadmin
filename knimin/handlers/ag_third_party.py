#!/usr/bin/env python
from knimin.handlers.base import BaseHandler
from tornado.web import authenticated
from wtforms import (Form, SelectField, FileField, validators)
from knimin import db


class ThirdParty(Form):
    required = validators.required
    survey = SelectField('Third Party survey',
                         choices=db.list_external_surveys(),
                         validators=[required("Required field")])
    file_in = FileField('Third party survey data',
                        validators=[required("Required field")])
    seperator = SelectField('File seperator', choices=[
        ('comma', 'comma'), ('tab', 'tab'), ('space', 'space')])
    survey_id = SelectField('Survey id column name', disabled=True)


class AGStatsHandler(BaseHandler):
    @authenticated
    def get(self):
        self.render("ag_third_party.html", form=ThirdParty)

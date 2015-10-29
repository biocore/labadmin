#!/usr/bin/env python
from knimin.handlers.base import BaseHandler
from tornado.web import authenticated
from wtforms import (Form, SelectField, FileField, TextField, validators)
from knimin import db


class ThirdPartyData(Form):
    required = validators.required
    survey = SelectField('Third Party survey',
                         choices=db.list_external_surveys(),
                         validators=[required("Required field")])
    file_in = FileField('Third party survey data',
                        validators=[required("Required field")])
    seperator = SelectField('File seperator', choices=[
        ('comma', 'comma'), ('tab', 'tab'), ('space', 'space')],
        validators=[required("Required field")])
    survey_id = TextField('Survey id column name',
                          validators=[required("Required field")])


class NewThirdPartyThirdParty(Form):
    required = validators.required
    name = TextField('Survey Name', validators=[required("Required field")])
    description = TextField('Description',
                            validators=[required("Required field")])
    url = TextField('Survey URL', validators=[required("Required field")])


class NewThirdParty(Form):
    required = validators.required
    survey = SelectField('Third Party survey',
                         choices=db.list_external_surveys(),
                         validators=[required("Required field")])
    file_in = FileField('Third party survey data',
                        validators=[required("Required field")])
    seperator = SelectField('File seperator', choices=[
        ('comma', 'comma'), ('tab', 'tab'), ('space', 'space')],
        validators=[required("Required field")])
    survey_id = TextField('Survey id column name',
                          validators=[required("Required field")])


class AGThirdPartyHandler(BaseHandler):
    @authenticated
    def get(self):
        self.render("ag_third_party.html", the_form=ThirdPartyData(),
                    errors='')


class AGNewThirdPartyHandler(BaseHandler):
    @authenticated
    def get(self):
        self.render("new_third_party.html", the_form=NewThirdParty(),
                    errors='')

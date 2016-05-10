#!/usr/bin/env python
from io import StringIO
from future.utils import viewitems
from tornado.web import authenticated
from wtforms import (Form, SelectField, FileField, TextField, validators)

from knimin.handlers.base import BaseHandler
from knimin.handlers.access_decorators import set_access
from knimin import db


class ThirdPartyData(Form):
    required = validators.required
    survey = SelectField('Third Party survey',
                         validators=[required("Required field")])
    file_in = FileField('Third party survey data')
    seperator = SelectField('File seperator', choices=[
        ('comma', 'comma'), ('tab', 'tab'), ('space', 'space')],
        validators=[required("Required field")])
    survey_id = TextField('Survey id column name',
                          validators=[required("Required field")])
    trim = TextField('Regex to trim survey id (leave blank for none)')


class NewThirdParty(Form):
    required = validators.required
    name = TextField('Survey Name', validators=[required("Required field")])
    description = TextField('Description',
                            validators=[required("Required field")])
    url = TextField('Survey URL', validators=[required("Required field")])


@set_access(['External surveys'])
class AGThirdPartyHandler(BaseHandler):
    @authenticated
    def get(self):
        form = ThirdPartyData()
        form.survey.choices = [(x, x) for x in db.list_external_surveys()]
        self.render("ag_third_party.html", the_form=form,
                    errors='')

    @authenticated
    def post(self):
        form = ThirdPartyData()
        form.survey.choices = [(x, x) for x in db.list_external_surveys()]
        msg = ''
        seperators = {'comma': ',', 'tab': '\t', 'space': ' '}

        args = {a: v[0] for a, v in viewitems(self.request.arguments)}
        form.process(data=args)
        # Validate form and make sure upload happened
        if not form.validate() or 'file_in' not in self.request.files:
            self.render("ag_third_party.html", the_form=form,
                        errors=msg)
            return

        # Format file for stringIO
        file_body = self.request.files['file_in'][0]['body'].replace(
            "\r\n", "\n").replace("\r", "\n")
        file_body = StringIO(unicode(file_body), newline=None)
        try:
            count = db.store_external_survey(
                file_body, form.survey.data,
                separator=seperators[form.seperator.data],
                survey_id_col=form.survey_id.data, trim=form.trim.data)
        except KeyError as e:
            msg = 'Header column not found: %s' % str(e)
        except Exception as e:
            # Print any error that happens to the page
            msg = str(e)
        else:
            msg = "%d surveys added to '%s' successfully" % \
                  (count, form.survey.data)
        self.render("ag_third_party.html", the_form=form,
                    errors=msg)


@set_access(['External surveys'])
class AGNewThirdPartyHandler(BaseHandler):
    @authenticated
    def get(self):
        self.render("new_third_party.html", the_form=NewThirdParty(),
                    errors='')

    @authenticated
    def post(self):
        form = NewThirdParty()
        msg = ''
        args = {a: v[0] for a, v in viewitems(self.request.arguments)}
        form.process(data=args)
        if not form.validate():
            self.render("new_third_party.html", the_form=form,
                        errors=msg)
            return

        try:
            db.add_external_survey(form.name.data, form.description.data,
                                   form.url.data)
        except Exception as e:
            # Print any error that happens to the page
            msg = str(e)
        else:
            msg = "Added '%s' successfully" % form.name.data
        self.render("new_third_party.html", the_form=form,
                    errors=msg)

#!/usr/bin/env python
from tornado.web import authenticated
from tornado.escape import json_encode
from tornado import gen, concurrent
from knimin.handlers.base import BaseHandler
from datetime import datetime
import requests
import functools
from qiita_client import QiitaClient

from knimin import db
from knimin.lib.constants import survey_type
from knimin.lib.mail import send_email
from knimin.handlers.access_decorators import set_access
from knimin.lib.configuration import config


def get_qiita_client():
    if config.debug:
        class _mock:
            def get(self, *args, **kwargs):
                return {'categories': ['a', 'b', 'c']}

            def http_patch(self, *args, **kwargs):
                return 'okay'

        qclient = _mock()
    else:
        # interface for making HTTP requests against Qiita
        qclient = QiitaClient(':'.join([config.qiita_host, config.qiita_port]),
                              config.qiita_client_id,
                              config.qiita_client_secret,
                              config.qiita_certificate)

        # we are monkeypatching to use qclient's internal machinery
        # and to fix the broken HTTP patch
        qclient.http_patch = functools.partial(qclient._request_retry,
                                               requests.patch)
    return qclient


class BarcodeUtilHelper(object):
    def get_ag_details(self, barcode):
        ag_details = db.getAGBarcodeDetails(barcode)
        _, failures = db.pulldown([barcode], [])

        if len(ag_details) == 0 and failures:
            div_id = "no_metadata"
            message = "Cannot retrieve metadata: %s" % failures[barcode]
        elif len(ag_details) > 0:
            for col, val in ag_details.iteritems():
                if val is None:
                    ag_details[col] = ''
            ag_details['other_checked'] = ''
            ag_details['overloaded_checked'] = ''
            ag_details['moldy_checked'] = ''
            ag_details['login_user'] = ag_details['name']
            if ag_details['moldy'] == 'Y':
                ag_details['moldy_checked'] = 'checked'
            if ag_details['overloaded'] == 'Y':
                ag_details['overloaded_checked'] = 'checked'
            if ag_details['other'] == 'Y':
                ag_details['other_checked'] = 'checked'

            survey_id = db.get_barcode_survey(barcode)

            # it has all sample details
            # (sample time, date, site)
            if failures:
                div_id = "no_metadata"
                message = "Cannot retrieve metadata: %s" % failures[barcode]
                ag_details['email_type'] = "-1"
            elif (survey_id is None and ag_details['environment_sampled']) \
                    or survey_id in survey_type:
                div_id = "verified"
                message = "All good"
                ag_details['email_type'] = "1"
            else:
                # should never get here (this would happen
                # if the metadata
                # pulldown returned more than one row for a
                # single barcode)
                div_id = "md_pulldown_error"
                message = ("This barcode has multiple entries "
                           "in the database, which should "
                           "never happen. Please notify "
                           "someone on the database crew.")
                ag_details['email_type'] = "-1"
        else:
            # TODO: Stefan Janssen: I cannot see how this case should ever be
            # reached, since failures will be set to 'Unknown reason' at the
            # outmost.
            div_id = "not_assigned"
            message = ("In American Gut project group but no "
                       "American Gut info for barcode")
            ag_details['email_type'] = "-1"
        return div_id, message, ag_details

    def update_ag_barcode(self, barcode, login_user, login_email, email_type,
                          sent_date, send_mail, sample_date, sample_time,
                          other_text):
        email_msg = ag_update_msg = None
        if all([send_mail is not None, login_email is not None,
                login_email != '']):
            subject, body_message = self._build_email(
                login_user, barcode, email_type, sample_date, sample_time)
            if body_message != '':
                sent_date = datetime.now()
                email_msg = ("Sent email successfully to kit owner %s" %
                             login_email)
                try:
                    send_email(body_message, subject, login_email, html=True)
                except:  # noqa
                    email_msg = ("Email sending to (%s) failed (barcode: %s)!"
                                 "<br/>" % (login_email, barcode))
        sample_issue = self.get_argument('sample_issue', [])
        moldy = overloaded = other = 'N'
        if 'moldy' in sample_issue:
            moldy = 'Y'
        if 'overloaded' in sample_issue:
            overloaded = 'Y'
        if 'other' in sample_issue:
            other = 'Y'
        ag_update_msg = ("Barcode %s AG info was successfully updated" %
                         barcode)
        try:
            db.updateAKB(barcode, moldy, overloaded, other, other_text,
                         sent_date)
        except:  # noqa
            ag_update_msg = ("Barcode %s AG update failed!!!" % barcode)

        return email_msg, ag_update_msg

    def _build_email(self, login_user, barcode, email_type,
                     sample_date, sample_time):
        subject = body_message = u""

        if email_type in ('0', '-1'):
            subject = u'ACTION REQUIRED - Assign your samples in American Gut'
            body_message = u"""
<html>
<body>
<p>Dear {name},</p>
<p>We have recently received your sample barcode: {barcode}, but we cannot
process your sample until the following steps have been completed online.
Please ensure that you have completed <b>both</b> steps outlined below:</p>
<ol>
<li><b>Submit your consent form and survey-<i>if you have already done these
please proceed to step 2 below.</i></b><br/>For human samples, the consent form
is mandatory. Even if you elect not to answer the questions on the survey,
please click through and submit the survey in order to ensure we receive your
completed consent form.</li>
<li><b>Assign your sample(s) to your survey(s)</b><br/>This step is critical as
it connects your consent form to your sample. We cannot legally work with your
sample until this step has been completed.</li>
</ol>
<p>To assign your sample to your survey:</p>
<ul>
<li>Log into your account and click the &quot;Assign&quot; button at the bottom
of the left-hand navigation menu. This will bring you to a screen with the
heading &quot;Choose your sample source&quot;.</li>
<li>Click on the name of the participant that the sample belongs to.</li>
<li>Fill out the required fields and submit.</li>
</ul>
<p>
The American Gut participant website is located at<br/>
<a href='https://microbio.me/americangut'>https://microbio.me/americangut</a>
<br/>The British Gut participant website is located at<br/>
<a href='https://microbio.me/britishgut'>https://microbio.me/britishgut</a>
<br/>If you have any questions, please contact us at
<a href='mailto:info@americangut.org'>info@americangut.org</a>.</p>
<p>Thank you,<br/>
American Gut Team</p>
</body>
</html>"""

            body_message = body_message.format(name=login_user,
                                               barcode=barcode)
        elif email_type == '1':
            subject = (u'American Gut Sample with Barcode %s is Received.'
                       % barcode)
            body_message = u"""<html><body><p>
Dear {name},</p>

<p>We have recently received your sample with barcode {barcode} dated
{sample_date} {sample_time} and we have begun processing it.  Please see our
FAQ section for when you can expect results.<br/>
(<a href='https://microbio.me/AmericanGut/faq/#faq4'
>https://microbio.me/AmericanGut/faq/#faq4</a>)</p>

<p>Thank you for your participation!</p>

<p>--American Gut Team--</p></body></html>
"""
            body_message = body_message.format(name=login_user,
                                               barcode=barcode,
                                               sample_date=sample_date,
                                               sample_time=sample_time)
        else:
            raise RuntimeError("Unknown email type passed: %s" % email_type)

        return subject, body_message


def align_with_qiita_categories(samples, categories):
    # obviously should instead align to the actual sample metadata...
    aligned = {}
    for s in samples:
        aligned[s] = {c: 'LabControl test' for c in categories}
    return aligned


@set_access(['Scan Barcodes'])
class PushQiitaHandler(BaseHandler):
    executor = concurrent.futures.ThreadPoolExecutor(5)
    study_id = config.qiita_study_id
    qclient = get_qiita_client()

    @concurrent.run_on_executor
    def _push_to_qiita(self, study_id, samples):
        # TODO: add a mutex or block to ensure a single call process at a time
        cats = self.qclient.get('/api/v1/study/%s/samples/info' % study_id)
        cats = cats['categories']

        samples = align_with_qiita_categories(samples, cats)
        data = json_encode(samples)

        return self.qclient.http_patch('/api/v1/study/%s/samples' % study_id,
                                       data=data)

    @authenticated
    def get(self):
        barcodes = db.get_unsent_barcodes_from_qiita_buffer()
        status = db.get_send_qiita_buffer_status()
        dat = {'status': status, "barcodes": barcodes}
        self.write(json_encode(dat))
        self.finish()

    @authenticated
    @gen.coroutine
    def post(self):
        barcodes = db.get_unsent_barcodes_from_qiita_buffer()
        if not barcodes:
            return

        # certainly not a perfect mutex, however tornado is single threaded
        status = db.get_send_qiita_buffer_status()
        if status in ['Failed!', 'Pushing...']:
            return

        db.set_send_qiita_buffer_status("Pushing...")

        try:
            yield self._push_to_qiita(self.study_id, barcodes)
        except:  # noqa
            db.set_send_qiita_buffer_status("Failed!")
        else:
            db.mark_barcodes_sent_to_qiita(barcodes)
            db.set_send_qiita_buffer_status("Idle")


@set_access(['Scan Barcodes'])
class BarcodeUtilHandler(BaseHandler, BarcodeUtilHelper):

    @authenticated
    def get(self):
        barcode = self.get_argument('barcode', None)
        if barcode is None:
            self.render("barcode_util.html", div_and_msg=None,
                        barcode_projects=[], parent_project=None,
                        project_names=[], barcode=None, email_type=None,
                        barcode_info=None, proj_barcode_info=None, msgs=None,
                        currentuser=self.current_user)
            return
        # gather info to display
        barcode_details = db.get_barcode_details(barcode)
        if len(barcode_details) == 0:
            div_id = "invalid_barcode"
            message = ("Barcode %s does not exist in the database" %
                       barcode)
            self.render("barcode_util.html",
                        div_and_msg=(div_id, message, barcode),
                        barcode_projects=[], parent_project=None,
                        project_names=[],
                        barcode=barcode, email_type=None,
                        barcode_info=None, proj_barcode_info=None,
                        msgs=None, currentuser=self.current_user)
            return

        barcode_projects, parent_project = db.getBarcodeProjType(
            barcode)
        project_names = db.getProjectNames()

        # barcode exists get general info
        # TODO (Stefan Janssen): check spelling of "received", i.e. tests in
        # the template check for 'Recieved'. I think the logic is broken due
        # to that.
        if barcode_details['status'] is None:
            barcode_details['status'] = 'Received'
        if barcode_details['biomass_remaining'] is None:
            barcode_details['biomass_remaining'] = 'Unknown'
        if barcode_details['sequencing_status'] is None:
            barcode_details['sequencing_status']
        if barcode_details['obsolete'] is None:
            barcode_details['obsolete'] = 'N'
        div_id = message = ""
        if (barcode_details['obsolete'] == "Y"):
            # the barcode is obsolete
            div_id = "obsolete"
            # TODO: Stefan: why is that set here, as far as I see, this
            # message will in all cases be overwritten!
            message = "Barcode is Obsolete"
        # get project info for div
        ag_details = []
        if parent_project == 'American Gut':
            div_id, message, ag_details = self.get_ag_details(barcode)
        else:
            div_id = "verified"
            message = "Barcode Info is correct"
        div_and_msg = (div_id, message, barcode)
        self.render("barcode_util.html", div_and_msg=div_and_msg,
                    barcode_projects=barcode_projects,
                    parent_project=parent_project,
                    project_names=project_names,
                    barcode=barcode, email_type=None,
                    barcode_info=barcode_details,
                    proj_barcode_info=ag_details, msgs=None,
                    currentuser=self.current_user)

    @authenticated
    def post(self):
        barcode = self.get_argument('barcode')
        postmark_date = self.get_argument('postmark_date', None)
        scan_date = self.get_argument('scan_date', None)
        biomass_remaining_value = self.get_argument('biomass_remaining_value',
                                                    None)
        sequencing_status = self.get_argument('sequencing_status', None)
        obsolete_status = self.get_argument('obsolete_status', None)
        projects = set(self.get_arguments('project'))
        sent_date = self.get_argument('sent_date', None)
        login_user = self.get_argument('login_user',
                                       'American Gut participant')
        send_mail = self.get_argument('send_mail', None)
        login_email = self.get_argument('login_email', None)
        other_text = self.get_argument('other_text', None)
        email_type = self.get_argument('email_type', None)
        sample_time = self.get_argument('sample_time', None)
        sample_date = self.get_argument('sample_date', None)
        # now we collect data and update based on forms
        # first update general barcode info
        # Set to non to make sure no conflicts with new date typing in DB
        if not postmark_date:
            postmark_date = None
        if not scan_date:
            scan_date = None
        try:
            db.updateBarcodeStatus('Received',
                                   postmark_date,
                                   scan_date, barcode,
                                   biomass_remaining_value,
                                   sequencing_status,
                                   obsolete_status)
            gen_update_msg = "Barcode %s general details updated" % barcode
        except:  # noqa
            gen_update_msg = "Barcode %s general details failed" % barcode

        email_msg = ag_update_msg = project_msg = None
        exisiting_proj, parent_project = db.getBarcodeProjType(
            barcode)
        # This WILL NOT let you remove a sample from being in AG if it is
        # part of AG to begin with
        exisiting_proj = set(exisiting_proj.split(', '))
        if exisiting_proj != projects:
            try:
                add_projects = projects.difference(exisiting_proj)
                rem_projects = exisiting_proj.difference(projects)
                db.setBarcodeProjects(barcode, add_projects, rem_projects)
                project_msg = "Project successfully changed"
            except:  # noqa
                project_msg = "Error changing project"

            new_proj, parent_project = db.getBarcodeProjType(barcode)
        if parent_project == 'American Gut':
            db.push_barcode_to_qiita_buffer(barcode)

            email_msg, ag_update_msg = self.update_ag_barcode(
                barcode, login_user, login_email, email_type, sent_date,
                send_mail, sample_date, sample_time, other_text)

        self.render("barcode_util.html", div_and_msg=None,
                    barcode_projects=[],
                    parent_project=None,
                    project_names=[], barcode=None,
                    email_type=None,
                    barcode_info=None, proj_barcode_info=None,
                    msgs=(gen_update_msg, email_msg, ag_update_msg,
                          project_msg),
                    currentuser=self.current_user)

#!/usr/bin/env python
from tornado.web import authenticated
from knimin.handlers.base import BaseHandler
from datetime import datetime
from tornado.escape import json_decode

import pandas as pd

from knimin import db, qiita_client
from knimin.lib.constants import survey_type
from knimin.lib.mail import send_email
from knimin.handlers.access_decorators import set_access


class BarcodeUtilHelper(object):
    def get_ag_details(self, barcode):
        ag_details = db.getAGBarcodeDetails(barcode)
        md, failures = db.pulldown([barcode], [])

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
        return div_id, message, ag_details, md

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
                except:
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
        except:
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
            div_id, message, ag_details, md = self.get_ag_details(barcode)
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
        except:
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
            except:
                project_msg = "Error changing project"

            new_proj, parent_project = db.getBarcodeProjType(barcode)
        if parent_project == 'American Gut':
            email_msg, ag_update_msg = self.update_ag_barcode(
                barcode, login_user, login_email, email_type, sent_date,
                send_mail, sample_date, sample_time, other_text)
            div_id, message, ag_details, md = self.get_ag_details(barcode)
            if div_id == 'verified':
                msg = update_ag_metadata(barcode, md)
                gen_update_msg = '. '.join([gen_update_msg, msg])

        self.render("barcode_util.html", div_and_msg=None,
                    barcode_projects=[],
                    parent_project=None,
                    project_names=[], barcode=None,
                    email_type=None,
                    barcode_info=None, proj_barcode_info=None,
                    msgs=(gen_update_msg, email_msg, ag_update_msg,
                          project_msg),
                    currentuser=self.current_user)


def update_ag_metadata(barcode, md):
    """Push the sample's metadata to Qiita

    This is specific for American Gut samples. We need to make sure the sample
    is represented in Qiita so that it can be plated by the PlateMapper
    interface.
    """
    sc, response = qiita_client.get('/api/v1/study/10317/samples')
    if sc != 200:
        return "Unable to get sample IDs from Qiita"

    existing = set(json_decode(response.body))
    if barcode in existing:
        return "Metadata for %s already exists in Qiita" % barcode

    # the db.pulldown call returns formatted metadata, so we actually need to
    # reparse it unfortunately.
    md = pd.read_csv(md, sep='\t', dtype=str, na_values=[],
                     keep_default_na=False)
    md.rename({'#SampleID': 'sample_name'}, inplace=True)
    md.set_index('sample_name', inplace=True)
    sc, response = qiita_client.patch('/api/v1/study/10317',
                                      data=md.todict(),
                                      as_json=True)

    if sc == 201:
        return "Metadata for AG sample %s added into Qiita"
    elif sc == 200:
        # this should not happen as we first check whether the sample is
        # already represented; this status code means that the sample is
        # already present in the qiita study. there is a race condition
        # though as we cannot put a lock on the remote resouce. So it is
        # technically possible that a sample metadata for this sample will
        # get loaded via a different mechanism in between the time we check
        # qiita, and the time we push sample metadata.

        # and obviously, this message is _not_ the best way to handle this
        # situation but it isn't clear what is best at this time. it also is
        # not clear whether there is an actual problem here given the limited
        # scope of how this scenario can arise.
        return ("UNEXPECTED: the metadata for this sample was updated, please "
                "notify the development team that this message was received.")
    else:
        raise ValueError("%d was received; response details: %s" %
                         (sc, response.body))

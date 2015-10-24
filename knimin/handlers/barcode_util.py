#!/usr/bin/env python
from tornado.web import authenticated
from knimin.handlers.base import BaseHandler
import time

from knimin import db
from knimin.lib.constants import survey_type
from knimin.lib.mail import send_email


class BarcodeUtilHandler(BaseHandler):
    @authenticated
    def get(self):
        self.render("barcode_util.html", div_and_msg=None, barcode_projects=[],
                    parent_project=None,
                    project_names=[], barcode=None, email_type=None,
                    barcode_info=None, proj_barcode_info=None, msgs=None,
                    currentuser=self.current_user)

    @authenticated
    def post(self):
        barcode = self.get_argument('barcode', None)
        bstatus = self.get_argument('bstatus', None)
        postmark_date = self.get_argument('postmark_date', None)
        scan_date = self.get_argument('scan_date', None)
        biomass_remaining_value = self.get_argument('biomass_remaining_value',
                                                    None)
        sequencing_status = self.get_argument('sequencing_status', None)
        obsolete_status = self.get_argument('obsolete_status', None)
        projects = set(self.get_arguments('project'))
        barcode_projects = 'Unknown'
        ag_details = {}
        if bstatus is None:
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
            else:
                barcode_projects, parent_project = db.getBarcodeProjType(
                    barcode)
                project_names = db.getProjectNames()

                # barcode exists get general info
                if barcode_details['status'] is None:
                    barcode_details['status'] = 'Received'
                if barcode_details['biomass_remaining'] is None:
                    barcode_details['biomass_remaining'] = 'Unknown'
                if barcode_details['sequencing_status'] is None:
                    barcode_details['sequencing_status']
                if barcode_details['obsolete'] is None:
                    barcode_details['obsolete'] = 'N'
                div_id = message = ""
                ag_details = []
                if (barcode_details['obsolete'] == "Y"):
                        # the barcode is obsolete
                        div_id = "obsolete"
                        message = "Barcode is Obsolete"
                # get project info for div
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
        else:
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
                msg1 = "Barcode %s general details updated" % barcode
            except:
                msg1 = "Barcode %s general details failed" % barcode

            msg2 = msg3 = msg4 = None
            exisiting_proj, parent_project = db.getBarcodeProjType(
                barcode)
            exisiting_proj = set(exisiting_proj.split(','))
            if exisiting_proj != projects:
                try:
                    add_projects = projects.difference(exisiting_proj)
                    rem_projects = exisiting_proj.difference(projects)
                    print exisiting_proj
                    print projects
                    print add_projects
                    print rem_projects
                    db.setBarcodeProjects(barcode, add_projects, rem_projects)
                    msg4 = "Project successfully changed"
                except:
                    msg4 = "Error changing project"

                new_proj, parent_project = db.getBarcodeProjType(barcode)
            if parent_project == 'American Gut':
                msg2, msg3 = self.update_ag_barcode(barcode)
            self.render("barcode_util.html", div_and_msg=None,
                        barcode_projects=[],
                        parent_project=None,
                        project_names=[], barcode=None,
                        email_type=None,
                        barcode_info=None, proj_barcode_info=None,
                        msgs=(msg1, msg2, msg3, msg4),
                        currentuser=self.current_user)

    def get_ag_details(self, barcode):
        ag_details = db.getAGBarcodeDetails(barcode)
        if len(ag_details) > 0:
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
            _, failures = db.pulldown([barcode], [])

            # it has all sample details
            # (sample time, date, site)
            if failures:
                div_id = "no_metadata"
                message = "Cannot retrieve metadata: %s" % failures[0][1]
                ag_details['email_type'] = "-1"
            elif survey_type[survey_id] == 'Human':
                # and we can successfully retrieve sample
                # metadata
                div_id = "verified"
                message = "All good"
                ag_details['email_type'] = "1"
            elif survey_type[survey_id] == 'Animal':
                div_id = "verified_animal"
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
            div_id = "not_assigned"
            message = ("In American Gut project group but No "
                       "American Gut info for barcode")
            ag_details['email_type'] = "-1"
        return div_id, message, ag_details

    def update_ag_barcode(self, barcode):
        msg2 = msg3 = None
        sent_date = self.get_argument('sent_date', None)
        general_name = "American Gut participant"
        login_user = self.get_argument('login_user', None)  # kit owner name
        if login_user == "None":
            login_user = general_name
        send_mail = self.get_argument('send_mail', None)
        if send_mail is not None:
            email_type = self.get_argument('email_type', None)
            subject = body_message = ""
            sample_time = self.get_argument('sample_time', None)
            sample_date = self.get_argument('sample_date', None)
            if email_type == '0':
                subject = ('Follow up on Your American Gut Sample with '
                           'Barcode %s' % barcode)
                body_message = """
Dear {name},

We have recently received your sample barcode: {barcode}, but we cannot process
your sample until the following steps have been completed online. Please ensure
 that you have completed both steps outlined below:

1). Submit consent form & survey
For human samples, the consent form is mandatory. Please note that the consent
form is located on the first page of the survey. Even if you elect not to
answer the questions on the survey (as every question is optional), please
click through and submit the survey in order to ensure we receive your
completed consent form.
For pet samples, we ask that you fill out a short survey.
No consent form is necessary
For environmental samples, no consent form or survey is necessary.
Please skip to step 2 below.
To begin the consent/survey process, click on the "Add Source & Survey" tab
on the main page. Select the category (human, animal, or environmental) your
intended sample belongs to.
2). Log your sample
Note that for human & pet samples, the survey must be completed before doing
this step

In order to log your sample, please log into your account and click the
"Log Sample" button at the bottom of the left-hand navigation menu.
This will bring you to a screen with the heading "Choose your sample source".
Click on the name that the sample belongs to, then fill out the prompted
fields. To facilitate this process, the details you included on the side of
your sample tube are:
Sample Date: {sample_date}
Sample Time: {sample_time}

Our website is located at www.microbio.me/americangut. If you have any
questions, please contact us at info@americangut.org.

Thank you,
American Gut Team

"""

                body_message = body_message.format(name=login_user,
                                                   barcode=barcode,
                                                   sample_date=sample_date,
                                                   sample_time=sample_time)
            elif email_type == '1':
                subject = ('American Gut Sample with Barcode %s is Received.'
                           % barcode)
                body_message = """
Dear {name},

We have recently received your sample with barcode {barcode} dated
{sample_date} {sample_time} and we have begun processing it.  Please see our
FAQ section for when you can expect results.
(http://www.microbio.me/americangut/FAQ.psp#faq4)

Thank you for your participation!

--American Gut Team--
"""
                body_message = body_message.format(name=login_user,
                                                   barcode=barcode,
                                                   sample_date=sample_date,
                                                   sample_time=sample_time)
            login_email = self.get_argument('login_email', None)
            if login_email != "" or login_email is not None:
                try:
                    send_email(body_message, subject, login_email)
                    sent_date = time.now()
                    msg2 = ("Sent email successfully to kit owner %s"
                            % login_email)
                except:
                    msg2 = ("Email sending to (%s) failed failed "
                            "(barcode: %s)!!!<br/>" % (login_email, barcode))
        sample_issue = self.get_argument('sample_issue', [])
        moldy = overloaded = other = 'N'
        if 'moldy' in sample_issue:
            moldy = 'Y'
        if 'overloaded' in sample_issue:
            overloaded = 'Y'
        if 'other' in sample_issue:
            other = 'Y'
        try:
            db.updateAKB(barcode, moldy, overloaded, other,
                         self.get_argument('other_text', None),
                         sent_date)
            msg3 = ("Barcode %s AG info was sucessfully updated" % barcode)
        except:
            msg3 = ("Barcode %s AG update failed!!!" % barcode)

        return msg2, msg3

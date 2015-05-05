#!/usr/bin/env pythonget_barcode_info_by_kit_id
from tornado.web import authenticated
from knimin.handlers.base import BaseHandler
from urllib import unquote
import time

from amgut.connections import ag_data
from amgut.lib.mail import send_email


class BarcodeUtilHandler(BaseHandler):
    @authenticated
    def get(self):
        self.render("barcode_util.html", div_and_msg=None, proj=None,
                    proj_group=None,
                    project_names=None, barcode=None, email_type=None,
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
        project = self.get_argument('project', None)
        proj_type = 'Unknown'
        ag_details = {}
        if bstatus is None:
            # gather info to display
            barcode_details = ag_data.get_barcode_details(barcode)
            if len(barcode_details) == 0:
                div_id = "invalid_barcode"
                message = ("Barcode %s does not exisit in the database" %
                           barcode)
                self.render("barcode_util.html",
                            div_and_msg=(div_id, message, barcode),
                            proj=None, proj_group=None, project_names=None,
                            barcode=barcode, email_type=None,
                            barcode_info=None, proj_barcode_info=None,
                            msgs=None,
                            currentuser=self.current_user)
                return
            else:
                proj_type, proj_group = ag_data.getBarcodeProjType(
                    barcode)
                project_names = ag_data.getProjectNames()
                # barcode exists get general info
                if barcode_details['status'] is None:
                    barcode_details['status'] = 'Received'
                if barcode_details['scan_date'] is None:
                    barcode_details['scan_date'] = 'NA'
                if barcode_details['sample_postmark_date'] is None:
                    barcode_details['sample_postmark_date'] = 'NA'
                if barcode_details['biomass_remaining'] is None:
                    barcode_details['biomass_remaining'] = 'Unknown'
                if barcode_details['sequencing_status'] is None:
                    barcode_details['sequencing_status']
                if barcode_details['obsolete'] is None:
                    barcode_details['obsolete'] = 'N'
                div_id = message = email_type = ""
                ag_details = []
                if (barcode_details['obsolete'] == "Y"):
                        #the barcode is obsolete
                        div_id = "obsolete"
                        message = "Barcode is Obsolete"
                #get project info for div
                if proj_group == 'American Gut':
                    div_id, message, ag_details = self.get_ag_details(barcode)
                else:
                    div_id = "verified"
                    message = "Barcode Info is correct"
            div_and_msg = (div_id, message, barcode)
            self.render("barcode_util.html", div_and_msg=div_and_msg,
                        proj=proj_type, proj_group=proj_group,
                        project_names=project_names,
                        barcode=barcode, email_type=None,
                        barcode_info=barcode_details,
                        proj_barcode_info=ag_details, msgs=None,
                        currentuser=self.current_user)
        else:
            #now we collect data and update based on forms
            #first update general barcode info
            try:
                ag_data.updateBarcodeStatus('Received', postmark_date,
                                                   scan_date, barcode,
                                                   biomass_remaining_value,
                                                   sequencing_status,
                                                   obsolete_status)
                msg1 = "Barcode %s general details updated" % barcode
            except:
                msg1 = "Barcode %s general details failed" % barcode
            msg2 = msg3 = msg4 = None
            exisiting_proj, proj_group = ag_data.getBarcodeProjType(
                barcode)
            if exisiting_proj != project:
                try:
                    ag_data.setBarcodeProjType(project, barcode)
                    msg4 = "Project successfully changed"
                except:
                    msg4 = "Error changing project"
                new_proj, proj_group = ag_data.getBarcodeProjType(
                    barcode)
            if proj_group == 'American Gut':
                msg2, msg3 = self.update_ag_barcode(barcode)
            self.render("barcode_util.html", div_and_msg=None, proj=None,
                        proj_group=None,
                        project_names=None, barcode=None, email_type=None,
                        barcode_info=None, proj_barcode_info=None,
                        msgs=(msg1, msg2, msg3, msg4),
                        currentuser=self.current_user)

        return

    def get_ag_details(self, barcode):
        ag_details = ag_data.getAGBarcodeDetails(barcode)
        if len(ag_details) > 0:
            if ag_details['site_sampled'] is None:
                ag_details['site_sampled'] = ''
            if ag_details['sample_date'] is None:
                ag_details['sample_date'] = ''
            if ag_details['sample_time'] is None:
                ag_details['sample_time'] = ''
            if ag_details['moldy'] is None:
                ag_details['moldy'] = 'NA'
            if ag_details['overloaded'] is None:
                ag_details['overloaded'] = 'NA'
            if ag_details['other'] is None:
                ag_details['other'] = 'NA'
            if ag_details['other_text'] is None:
                ag_details['other_text'] = ''
            if ag_details['date_of_last_email'] is None:
                ag_details['date_of_last_email'] = ''
            if ag_details['email'] is None:
                ag_details['email'] = ''
            if ag_details['name'] is None:
                ag_details['login_user'] = ''
            else:
                ag_details['login_user'] = \
                    ag_details['name']
            if ag_details['moldy'] == 'Y':
                ag_details['moldy_checked'] = 'checked'
            else:
                ag_details['moldy_checked'] = ''
            if ag_details['overloaded'] == 'Y':
                ag_details['overloaded_checked'] = 'checked'
            else:
                ag_details['overloaded_checked'] = ''
            if ag_details['other'] == 'Y':
                ag_details['other_checked'] = 'checked'
            else:
                ag_details['other_checked'] = ''

            barcode_metadata = ag_data.AGGetBarcodeMetadata(
                barcode)
            if not (ag_details['sample_date'] ==
                    ag_details['site_sampled'] ==
                    ag_details['sample_time'] == ''):
                # it has all sample details
                # (sample time, date, site)
                if len(barcode_metadata) == 1:
                    # and we can successfully retrieve sample
                    # metadata
                    div_id = "verified"
                    message = "All good"
                    ag_details['email_type'] = "1"
                elif len(barcode_metadata) == 0:
                    barcode_metadata_animal = \
                        ag_data.AGGetBarcodeMetadataAnimal(
                            barcode)
                    if len(barcode_metadata_animal) == 0:
                        #check for new survey
                        if ag_data.ag_new_survey_exists(barcode):
                            div_id = "verified"
                            message = "All good"
                            ag_details['email_type'] = "1"
                        else:
                            div_id = "no_metadata"
                            message = "Cannot retrieve metadata"
                            ag_details['email_type'] = "-1"
                    elif len(barcode_metadata_animal) == 1:
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
                               "never happeen. Please notify "
                               "someone on the database crew.")
                    ag_details['email_type'] = "-1"
            else:
                div_id = "not_assigned"
                message = "Missing info"
                ag_details['email_type'] = "0"
        else:
            div_id = "not_assigned"
            message = ("In American Gut project group but No "
                       "Amerincan Gut info for barcode")
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
                    sent_date = time.strftime("%d/%m/%Y")
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
            ag_data.updateAKB(barcode, moldy, overloaded, other,
                                     self.get_argument('other_text', None),
                                     sent_date)
            msg3 = ("Barcode %s AG info was sucessfully updated" % barcode)
        except:
            msg3 = ("Barcode %s AG update failed!!!" % barcode)
        return msg2, msg3

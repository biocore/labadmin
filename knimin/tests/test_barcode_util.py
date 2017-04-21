# -*- coding: utf-8 -*-
from unittest import main
from random import choice
from string import ascii_letters
from datetime import date, time
import os

from tornado.escape import url_escape, xhtml_escape

from knimin import db
from knimin.tests.tornado_test_base import TestHandlerBase
from knimin.handlers.barcode_util import BarcodeUtilHelper


class TestBarcodeUtil(TestHandlerBase):
    def setUp(self):
        self.ag_good = '000001018'
        self.ag_enviro = '000009460'
        self.not_ag = '000006155'
        self.not_logged = '000001137'

        self.data = {
            'barcode': self.ag_good,
            'login_email': 'REMOVED',
            'email_type': '1',
            'sample_site': 'Stool',
            'login_user': 'REMOVED',
            'other_text': 'REMOVED',
            'sample_date': '2013-04-18',
            'sample_time': '06:50:00',
            'postmark_date': '',
            'scan_date': '10/25/2015',
            'sent_date': '',
            'sequencing_status': 'SUCCESS',
            'bstatus': 'Recieved',
            'project': 'American Gut Project',
            'obsolete_status': 'N',
            'parent_project': 'American Gut',
            'biomass_remaining': 'Unknown',
        }

        self.data_not_logged = {
            'barcode': self.not_logged,
            'login_email': 'REMOVED',
            'email_type': 0}

        super(TestBarcodeUtil, self).setUp()

    def test_get_not_logged_in(self):
        db.alter_access_levels('test', [3])
        response = self.get('/barcode_util/')
        self.assertEqual(response.code, 200)
        self.assertTrue(
            response.effective_url.endswith('?next=%2Fbarcode_util%2F'))

    def test_get_not_authed(self):
        self.mock_login()
        response = self.get('/barcode_util/')
        self.assertEqual(response.code, 403)

    def test_get(self):
        self.mock_login()
        db.alter_access_levels('test', [3])
        response = self.get('/barcode_util/')
        self.assertEqual(response.code, 200)
        self.assertIn(
            '<input id="barcode" name="barcode" type="text" '
            'onclick="this.select()" />',
            response.body)

        self.assertNotIn('<option value="American Gut Project">'
                         'American Gut Project</option>',
                         response.body)

    def test_get_ag_barcode(self):
        self.mock_login()
        db.alter_access_levels('test', [3])
        response = self.get('/barcode_util/', {'barcode': self.ag_good})
        self.assertEqual(response.code, 200)
        self.assertIn(
            '<input id="barcode" name="barcode" type="text" '
            'onclick="this.select()" />',
            response.body)

        self.assertIn('<input class="checkbox" type="checkbox" name='
                      '"sample_issue" id="overloaded" value="overloaded" }/>',
                      response.body)

        self.assertIn('Project type: American Gut', response.body)
        self.assertIn('All good', response.body)

    def test_get_enviro_barcode(self):
        self.mock_login()
        db.alter_access_levels('test', [3])
        response = self.get('/barcode_util/', {'barcode': self.ag_enviro})
        self.assertEqual(response.code, 200)
        self.assertIn(
            '<input id="barcode" name="barcode" type="text" '
            'onclick="this.select()" />',
            response.body)

        self.assertIn('<input class="checkbox" type="checkbox" name='
                      '"sample_issue" id="overloaded" value="overloaded" }/>',
                      response.body)

        self.assertIn('Project type: American Gut', response.body)
        self.assertIn('All good', response.body)

    def test_get_handout_barcode(self):
        self.mock_login()
        db.alter_access_levels('test', [3])

        barcode = db.ut_get_arbitrary_handout_barcode()
        response = self.get('/barcode_util/', {'barcode': barcode})
        self.assertEqual(response.code, 200)
        self.assertIn(
            '<input id="barcode" name="barcode" type="text" '
            'onclick="this.select()" />',
            response.body)

        self.assertNotIn('<input class="checkbox" type="checkbox" name="sample'
                         '_issue" id="overloaded" value="overloaded" }/>',
                         response.body)

        self.assertIn('Project type: American Gut', response.body)
        self.assertIn('Cannot retrieve metadata: Unassigned handout kit '
                      'barcode', response.body)

    def test_get_unassigned_barcode(self):
        self.mock_login()
        db.alter_access_levels('test', [3])
        barcode = db.ut_get_arbitrary_unassigned_barcode()
        response = self.get('/barcode_util/', {'barcode': barcode})

        self.assertEqual(response.code, 200)
        self.assertIn(
            '<input id="barcode" name="barcode" type="text" '
            'onclick="this.select()" />',
            response.body)

        self.assertNotIn('<input class="checkbox" type="checkbox" name="sample'
                         '_issue" id="overloaded" value="overloaded" }/>',
                         response.body)

        self.assertIn('Project type: American Gut', response.body)
        self.assertIn('Cannot retrieve metadata: Unassigned handout kit '
                      'barcode', response.body)

    def test_get_non_ag_barcode(self):
        self.mock_login()

        db.alter_access_levels('test', [3])
        response = self.get('/barcode_util/', {'barcode': self.not_ag})
        self.assertEqual(response.code, 200)
        self.assertIn(
            '<input id="barcode" name="barcode" type="text" '
            'onclick="this.select()" />',
            response.body)

        self.assertNotIn('<input class="checkbox" type="checkbox" name="sample'
                         '_issue" id="overloaded" value="overloaded" }/>',
                         response.body)

        exp_prj_name = list(set(db.getBarcodeProjType(self.not_ag)))[0]
        self.assertIn('Project type: %s' % exp_prj_name.encode('utf-8'),
                      response.body)
        self.assertIn('Barcode Info is correct', response.body)

    def test_post_not_logged_in(self):
        db.alter_access_levels('test', [3])
        response = self.post('/barcode_util/', self.data)
        self.assertEqual(response.code, 403)

    def test_post_not_authed(self):
        self.mock_login()
        response = self.post('/barcode_util/', self.data)
        self.assertEqual(response.code, 403)

    def test_post_update_ag(self):
        db.alter_access_levels('test', [3])
        notes = ''.join([choice(ascii_letters) for x in range(40)])
        self.data['other_text'] = notes
        self.mock_login()
        response = self.post('/barcode_util/', data=self.data)
        self.assertEqual(response.code, 200)
        self.assertIn('Barcode %s AG info was successfully updated' %
                      self.ag_good, response.body)
        obs = db.getAGBarcodeDetails(self.ag_good)
        self.assertEqual(obs['other_text'], notes)

    def test_post_update_ag_project_change(self):
        db.alter_access_levels('test', [3])
        self.data['project'] = 'UNKNOWN_%s' % os.getpid()
        self.mock_login()
        # ensure project is in the DB
        db.create_project(self.data['project'])

        response = self.post('/barcode_util/', data=self.data)
        self.assertEqual(response.code, 200)
        self.assertIn('Barcode %s AG info was successfully updated' %
                      self.ag_good, response.body)
        self.assertIn('Project successfully changed', response.body)
        barcode_projects, parent_project = db.getBarcodeProjType(self.ag_good)
        self.assertEqual(barcode_projects, self.data['project'])
        self.assertEqual(parent_project, 'American Gut')

        # reset back
        db.setBarcodeProjects(self.ag_good,
                              rem_projects=[self.data['project']])
        barcode_projects, parent_project = db.getBarcodeProjType(self.ag_good)
        self.assertEqual(barcode_projects, '')
        self.assertEqual(parent_project, 'American Gut')
        db.ut_remove_project(self.data['project'])

    def test_post_not_logged_barcode(self):
        db.alter_access_levels('test', [3])
        notes = ''.join([choice(ascii_letters) for x in range(40)])
        self.data['other_text'] = notes
        self.mock_login()
        response = self.post('/barcode_util/', data=self.data_not_logged)
        self.assertEqual(response.code, 200)
        # I believe this is correct: the sample is marked as received, as well
        # as status such as moldy/etc but there is no consent or tie sample
        # site. This _should_ trigger an email
        self.assertIn('Barcode %s general details updated' %
                      self.not_logged, response.body)

    def test_build_email(self):
        db.alter_access_levels('test', [3])
        self.mock_login()
        subject, body = BarcodeUtilHelper()._build_email(
            u'persøn', '000001018', '0', '2016-12-14', '6:52 pm')
        self.assertEqual(
            subject, 'ACTION REQUIRED - Assign your samples in American Gut')
        self.assertEqual(
            body, u"""
<html>
<body>
<p>Dear persøn,</p>
<p>We have recently received your sample barcode: 000001018, but we cannot
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
</html>""")

        subject, body = BarcodeUtilHelper()._build_email(
            u'persøn', '000001018', '1', '2016-12-14', '6:52 pm')
        self.assertEqual(
            subject, 'American Gut Sample with Barcode 000001018 is Received.')
        self.assertEqual(
            body, u"""<html><body><p>
Dear persøn,</p>

<p>We have recently received your sample with barcode 000001018 dated
2016-12-14 6:52 pm and we have begun processing it.  Please see our
FAQ section for when you can expect results.<br/>
(<a href='https://microbio.me/AmericanGut/faq/#faq4'
>https://microbio.me/AmericanGut/faq/#faq4</a>)</p>

<p>Thank you for your participation!</p>

<p>--American Gut Team--</p></body></html>
""")

        with self.assertRaises(RuntimeError):
            BarcodeUtilHelper()._build_email(
                u'persøn', '000001018', 'UNKNOWN', '2016-12-14', '6:52 pm')

    def test_get_ag_details_SJ(self):
        h = BarcodeUtilHelper()

        # check output for a non existing barcode
        barcode = 'NotInDB'
        div_id, message, ag_details, md = h.get_ag_details(barcode)
        self.assertEqual(div_id, 'no_metadata')
        self.assertEqual(message, "Cannot retrieve metadata: %s" %
                         'Not an AG barcode')
        self.assertEqual(ag_details, {})
        self.assertEqual(md, {})

        # check normal behaviour
        barcode = '000001018'
        div_id, message, ag_details, md = h.get_ag_details(barcode)
        self.assertEqual(div_id, 'verified')
        self.assertEqual(message, "All good")
        header, sample = md[1].splitlines()
        self.assertTrue(header.startswith('sample_name'))
        self.assertTrue(sample.startswith(barcode))

        # TODO: Stefan Janssen: there seems to be differences weather this
        # test runs on my local machine or on Travis. Therefore, I delete
        # diverging entries
        del ag_details['moldy']
        del ag_details['overloaded']
        del ag_details['other']
        del ag_details['deposited']
        exp = {
               # 'login_user': 'REMOVED',
               'environment_sampled': '', 'withdrawn': '',
               'ag_kit_id': 'd8592c74-7ddb-2135-e040-8a80115d6401',
               'overloaded_checked': '',
               # 'participant_name': 'REMOVED-0',
               'ag_kit_barcode_id':
               'd8592c74-7ddc-2135-e040-8a80115d6401',
               'sample_date': date(2013, 4, 18),
               'other_checked': '', 'status': 'Received',
               'refunded': '', 'barcode': '000001018', 'moldy_checked': '',
               'date_of_last_email': '', 'site_sampled': 'Stool',
               # 'email_type': '1',
               # 'name': 'REMOVED',
               'sample_time': time(6, 50),
               # 'notes': 'REMOVED',
               # 'email': 'REMOVED'
              }
        # only look at those fields, that are not subject to scrubbing
        self.assertEqual({k: ag_details[k] for k in exp}, exp)
        exp_keys = ['login_user', 'environment_sampled', 'withdrawn',
                    'ag_kit_id', 'overloaded_checked', 'participant_name',
                    'ag_kit_barcode_id', 'sample_date', 'other_checked',
                    'status', 'refunded', 'other_text', 'barcode',
                    'moldy_checked', 'date_of_last_email', 'site_sampled',
                    'email_type', 'name', 'sample_time', 'notes', 'email']
        self.assertEqual(sorted(ag_details.keys()), sorted(exp_keys))

        # check that None values are set to ''
        barcode = '000016744'
        div_id, message, ag_details, md = h.get_ag_details(barcode)
        self.assertEqual(ag_details['environment_sampled'], '')  # and not None
        self.assertEqual(ag_details['other_checked'], '')
        header, sample = md[1].splitlines()
        self.assertTrue(header.startswith('sample_name'))
        self.assertTrue(sample.startswith(barcode))

        # check that other is set to 'checked' instead of DB values, which is Y
        barcode = "000003411"
        div_id, message, ag_details, _ = h.get_ag_details(barcode)
        self.assertNotEqual(ag_details['other_checked'], 'Y')
        self.assertEqual(ag_details['other_checked'], 'checked')

        # check that overloaded is set to 'checked' instead of DB values,
        # which is 'Y'
        barcode = '000001066'
        div_id, message, ag_details, _ = h.get_ag_details(barcode)
        self.assertNotEqual(ag_details['overloaded_checked'], 'Y')
        self.assertEqual(ag_details['overloaded_checked'], 'checked')

        # check that moldy is set to 'checked' instead of DB values,
        # which is 'Y'
        barcode = "000007677"
        div_id, message, ag_details, _ = h.get_ag_details(barcode)
        self.assertNotEqual(ag_details['moldy_checked'], 'Y')
        self.assertEqual(ag_details['moldy_checked'], 'checked')


class BarcodeUtilHandler(TestHandlerBase):
    def test_get_not_authed(self):
        response = self.get('/barcode_util/')
        self.assertEqual(response.code, 200)
        port = self.get_http_port()
        self.assertEqual(response.effective_url,
                         'http://localhost:%d/login/?next=%s' %
                         (port, url_escape('/barcode_util/')))

    def test_get(self):
        self.mock_login_admin()

        # test that only textbox for barcode is show, if no barcode is given.
        response = self.get('/barcode_util/')
        self.assertEqual(response.code, 200)
        self.assertNotIn('<h2 class="verification_text">', response.body)
        self.assertNotIn('<form action="/barcode_util/" method="post"',
                         response.body)

        # test display of non existing barcode on website
        barcode = 'NotInDB'
        response = self.get('/barcode_util/', {'barcode': barcode})
        self.assertEqual(response.code, 200)
        self.assertIn('Barcode %s does not exist in the database' % barcode,
                      response.body)
        self.assertIn('<h2 class="verification_text">', response.body)
        self.assertNotIn('<form action="/barcode_util/" method="post"',
                         response.body)
        self.assertIn('Project type: None', response.body)
        self.assertIn('Subprojects: []', response.body)
        self.assertIn('Barcode: %s' % barcode, response.body)

        # TODO: I think we have a problem with spelling the word 'received'!
        # barcode_status_received = '000000001'

        # check that neighter option from the combobox is selected, if status
        # is empty
        barcode_status_empty = "000001003"
        response = self.get('/barcode_util/',
                            {'barcode': barcode_status_empty})
        self.assertEqual(response.code, 200)
        self.assertIn('<option value="Recieved">Recieved</option>',
                      response.body)
        self.assertIn('<option value=""></option>', response.body)

        # check that neighter option from the combobox is selected, if status
        # is an empty quote
        barcode_status_quote = "000001420"
        response = self.get('/barcode_util/',
                            {'barcode': barcode_status_quote})
        self.assertEqual(response.code, 200)
        self.assertIn('<option value="Recieved">Recieved</option>',
                      response.body)
        self.assertIn('<option value="" selected></option>', response.body)

        # test correct option is set for barcodes with biomass remainings
        barcode_biomass_Y = "000003336"
        response = self.get('/barcode_util/',
                            {'barcode': barcode_biomass_Y})
        self.assertEqual(response.code, 200)
        self.assertIn('<option value="N" >No</option>', response.body)
        self.assertIn('<option value="Y" selected>Yes</option>',
                      response.body)
        self.assertIn('<option value="Unknown" >Unknown</option>',
                      response.body)

        # test correct option is set for barcodes without biomass remainings
        barcode_biomass_N = "000004244"
        response = self.get('/barcode_util/',
                            {'barcode': barcode_biomass_N})
        self.assertEqual(response.code, 200)
        self.assertIn('<option value="N" selected>No</option>', response.body)
        self.assertIn('<option value="Y" >Yes</option>', response.body)
        self.assertIn('<option value="Unknown" >Unknown</option>',
                      response.body)

        # test correct option is set for barcodes without info about biomass
        # remainings
        barcode_biomass_empty = "000004242"
        response = self.get('/barcode_util/',
                            {'barcode': barcode_biomass_empty})
        self.assertEqual(response.code, 200)
        self.assertIn('<option value="N" >No</option>', response.body)
        self.assertIn('<option value="Y" >Yes</option>', response.body)
        self.assertIn('<option value="Unknown" selected>Unknown</option>',
                      response.body)

        # check if sequencing status is set to ''
        # (TODO: currently it is set to WAITING, which seems to be wrong!)
        barcode_seqstatus_quote = "000012397"  # ''
        response = self.get('/barcode_util/',
                            {'barcode': barcode_seqstatus_quote})
        self.assertEqual(response.code, 200)
        self.assertIn('<option value="WAITING" >WAITING</option>',
                      response.body)
        self.assertIn('<option value="SUCCESS" >SUCCESS</option>',
                      response.body)
        self.assertIn('<option value="FAILED_SEQUENCING" >%s</option>' %
                      'FAILED_SEQUENCING',
                      response.body)
        self.assertIn('<option value="" selected></option>',
                      response.body)

        # check if sequencing status is set to ''
        # (TODO: currently it is set to WAITING, which seems to be wrong!)
        barcode_seqstatus_empty = "000001850"  #
        response = self.get('/barcode_util/',
                            {'barcode': barcode_seqstatus_empty})
        self.assertEqual(response.code, 200)
        self.assertIn('<option value="WAITING" >WAITING</option>',
                      response.body)
        self.assertIn('<option value="SUCCESS" >SUCCESS</option>',
                      response.body)
        self.assertIn('<option value="FAILED_SEQUENCING" >%s</option>' %
                      'FAILED_SEQUENCING',
                      response.body)
        self.assertIn('<option value="" ></option>',
                      response.body)

        # check if sequencing status is set to 'FAILED_SEQUENCING'
        barcode_seqstatus_fail = "000001139"  # FAILED_SEQUENCING
        response = self.get('/barcode_util/',
                            {'barcode': barcode_seqstatus_fail})
        self.assertEqual(response.code, 200)
        self.assertIn('<option value="WAITING" >WAITING</option>',
                      response.body)
        self.assertIn('<option value="SUCCESS" >SUCCESS</option>',
                      response.body)
        self.assertIn('<option value="FAILED_SEQUENCING" selected>%s</option>'
                      % 'FAILED_SEQUENCING',
                      response.body)
        self.assertIn('<option value="" ></option>',
                      response.body)

        # check if sequencing status is set to 'FAILED_SEQUENCING'
        # (TODO: currently it is set to nothing, which seems to be wrong!)
        barcode_seqstatus_fail1 = "000004053"  # FAILED_SEQUENCING_1
        response = self.get('/barcode_util/',
                            {'barcode': barcode_seqstatus_fail1})
        self.assertEqual(response.code, 200)
        self.assertIn('<option value="WAITING" >WAITING</option>',
                      response.body)
        self.assertIn('<option value="SUCCESS" >SUCCESS</option>',
                      response.body)
        self.assertIn('<option value="FAILED_SEQUENCING" >%s</option>' %
                      'FAILED_SEQUENCING',
                      response.body)
        self.assertIn('<option value="" ></option>',
                      response.body)

        # check if sequencing status is set to 'FAILED_SEQUENCING'
        # (TODO: currently it is set to nothing, which seems to be wrong!)
        barcode_seqstatus_fail2 = "000004244"  # FAILED_SEQUENCING_2
        response = self.get('/barcode_util/',
                            {'barcode': barcode_seqstatus_fail2})
        self.assertEqual(response.code, 200)
        self.assertIn('<option value="WAITING" >WAITING</option>',
                      response.body)
        self.assertIn('<option value="SUCCESS" >SUCCESS</option>',
                      response.body)
        self.assertIn('<option value="FAILED_SEQUENCING" >%s</option>' %
                      'FAILED_SEQUENCING',
                      response.body)
        self.assertIn('<option value="" ></option>',
                      response.body)

        # check if sequencing status is set to 'SUCCESS'
        barcode_seqstatus_succ = "000004234"  # SUCCESS
        response = self.get('/barcode_util/',
                            {'barcode': barcode_seqstatus_succ})
        self.assertEqual(response.code, 200)
        self.assertIn('<option value="WAITING" >WAITING</option>',
                      response.body)
        self.assertIn('<option value="SUCCESS" selected>SUCCESS</option>',
                      response.body)
        self.assertIn('<option value="FAILED_SEQUENCING" >%s</option>' %
                      'FAILED_SEQUENCING',
                      response.body)
        self.assertIn('<option value="" ></option>',
                      response.body)
        # check if sequencing status is set to 'WAITING'
        barcode_seqstatus_wait = "000004247"  # WAITING
        response = self.get('/barcode_util/',
                            {'barcode': barcode_seqstatus_wait})
        self.assertEqual(response.code, 200)
        self.assertIn('<option value="WAITING" selected>WAITING</option>',
                      response.body)
        self.assertIn('<option value="SUCCESS" >SUCCESS</option>',
                      response.body)
        self.assertIn('<option value="FAILED_SEQUENCING" >%s</option>' %
                      'FAILED_SEQUENCING',
                      response.body)
        self.assertIn('<option value="" ></option>',
                      response.body)

        # check if barcode is marked as obsolete
        # TODO: is that correct if the info in DB is ''?
        barcode_obsolete_empty = "000012395"  #
        response = self.get('/barcode_util/',
                            {'barcode': barcode_obsolete_empty})
        self.assertEqual(response.code, 200)
        self.assertIn('<option value="N" selected>No</option>', response.body)
        self.assertIn('<option value="Y" >Yes</option>', response.body)

        # check if barcode is marked as obsolete
        barcode_obsolete_N = "000012397"  # "N"
        response = self.get('/barcode_util/',
                            {'barcode': barcode_obsolete_N})
        self.assertEqual(response.code, 200)
        self.assertIn('<option value="N" selected>No</option>', response.body)
        self.assertIn('<option value="Y" >Yes</option>', response.body)

        # check if barcode is marked as obsolete
        barcode_obsolete_Y = "000012412"  # "Y"
        response = self.get('/barcode_util/',
                            {'barcode': barcode_obsolete_Y})
        self.assertEqual(response.code, 200)
        self.assertIn('<option value="N" >No</option>', response.body)
        self.assertIn('<option value="Y" selected>Yes</option>', response.body)

        # test display of non american gut barcode
        barcode_nonAGP = "000004369"
        response = self.get('/barcode_util/',
                            {'barcode': barcode_nonAGP})
        self.assertEqual(response.code, 200)
        self.assertIn('Barcode Info is correct</h2>', response.body)

        # test display of american gut barcode
        barcode_AGP = "000001001"
        response = self.get('/barcode_util/',
                            {'barcode': barcode_AGP})
        self.assertEqual(response.code, 200)
        self.assertIn('All good</h2>', response.body)

    def test_post(self):
        data = {
            'barcode': '000029153',
            'parent_project': 'American+Gut',
            'postmark_date': '2015-06-25',
            'scan_date': '2015-07-01',
            'bstatus': 'Recieved',
            'biomass_remaining': 'Unknown',
            'sequencing_status': 'WAITING',
            'obsolete_status': 'N',
            'sent_date': '2015-01-07',
            'login_user': 'REMOVED',
            'login_email': 'REMOVED',
            'email_type': '1',
            'sample_date': '2015-06-24',
            'sample_time': '22%3A50%3A00',
            'sample_site': 'Stool',
            'other_text': 'REMOVED',
            'send_mail': 'send_mail',
        }

        self.mock_login_admin()

        # check normal behaviour
        response = self.post('/barcode_util/', data)
        self.assertEqual(response.code, 200)
        self.assertIn('Barcode %s AG info was successfully updated' %
                      data['barcode'], response.body)
        self.assertIn('Project successfully changed', response.body)
        dbInfo = db.get_barcode_details(data['barcode'])
        self.assertEqual(date(2015, 6, 25), dbInfo['sample_postmark_date'])
        self.assertEqual(date(2015, 7, 1), dbInfo['scan_date'])

        # check that postmark_date and scan_date is set to None
        # if missed as an argument
        del data['postmark_date']
        del data['scan_date']
        response = self.post('/barcode_util/', data)
        self.assertEqual(response.code, 200)
        dbInfo = db.get_barcode_details(data['barcode'])
        self.assertEqual(None, dbInfo['sample_postmark_date'])
        self.assertEqual(None, dbInfo['scan_date'])
        data['postmark_date'] = '2015-06-25'
        data['scan_date'] = '2015-07-01'

        # TODO: Stefan Janssen: looks like we can successfully update a non
        # existing barcode!!
        data['barcode'] = 'rdskjmxykgrlyh'
        response = self.post('/barcode_util/', data)
        self.assertEqual(response.code, 200)
        self.assertTrue('<p> Barcode %s general details updated </p>'
                        % data['barcode'], response.body)
        data['barcode'] = '000029153'

        # check that update failes for wrong data types
        data['postmark_date'] = 'invalid date'
        response = self.post('/barcode_util/', data)
        self.assertEqual(response.code, 200)
        self.assertIn("Barcode %s general details failed" % data['barcode'],
                      response.body)

        # test changing the barcode's project to a non existing one
        # TODO: Stefan Janssen: I think this should not result in a positive
        # message like 'Project successfully changed', because this does not
        # trigger the creation of a new project!
        data['project'] = 'NotAProject'
        response = self.post('/barcode_util/', data)
        self.assertEqual(response.code, 200)
        self.assertTrue('<p> Barcode %s general details updated </p>'
                        % data['barcode'], response.body)
        self.assertIn('Project successfully changed', response.body)
        self.assertNotIn('%s added into Qiita' % data['barcode'],
                         response.body)

        # check updating a AGP barcode
        del data['project']
        response = self.post('/barcode_util/', data)
        self.assertEqual(response.code, 200)
        self.assertIn("Barcode %s AG info was successfully updated"
                      % data['barcode'], response.body)

        data = {
            'barcode': db.ut_get_arbitrary_non_ag_barcode(),
            'parent_project': db.getProjectNames()[1],
            'scan_date': '2014-12-15',
            'bstatus': 'Recieved',
            'biomass_remaining': 'Unknown',
            'sequencing_status': 'WAITING',
            'obsolete_status': 'N',
            'project': 'UNKNOWN',
        }

        response = self.post('/barcode_util/', data)
        self.assertEqual(response.code, 200)
        self.assertNotIn("Barcode %s AG info was successfully updated"
                         % data['barcode'], response.body)
        self.assertTrue('<p> Barcode %s general details updated </p>'
                        % data['barcode'], response.body)

    def test_get_ag_details(self):
        self.mock_login_admin()

        # test if AGP data are rendered correctly
        barcode = '000029153'
        response = self.get('/barcode_util/', {'barcode': barcode})
        self.assertEqual(response.code, 200)
        self.assertIn('<h2>%s Details</h2>' % 'American Gut', response.body)
        ag_details = db.getAGBarcodeDetails(barcode)
        self.assertIn('<tr><td>Sample Date</td><td>%s</td></tr>'
                      % ag_details['sample_date'], response.body)
        self.assertIn('<tr><td>Sample Time</td><td>%s</td></tr>'
                      % ag_details['sample_time'], response.body)
        self.assertIn('<tr><td>Sample Site</td><td>%s</td></tr>'
                      % ag_details['site_sampled'], response.body)

        self.assertIn('<label for="moldy"> moldy (current: %s) </label> <br />'
                      % ag_details['moldy'], response.body)
        self.assertIn(('<label for="overloaded"> overloaded (current: %s) '
                       '</label> <br />') % ag_details['overloaded'],
                      response.body)
        self.assertIn(('<label for="other"> other (current: %s) '
                       '</label> <br />') % ag_details['other'], response.body)

        self.assertIn(('<textarea name="other_text" onclick="this.select()'
                       '">%s</textarea>') %
                      xhtml_escape(ag_details['other_text']),
                      response.body)
        self.assertIn(('<label for="send_mail" style="display:block;">send kit'
                       ' owner %s (%s) an email </label>')
                      % (xhtml_escape(ag_details['name']),
                         xhtml_escape(ag_details['email'])),
                      response.body)


if __name__ == '__main__':
    main()

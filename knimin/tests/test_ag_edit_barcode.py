# -*- coding: utf-8 -*-
from unittest import main

from tornado.escape import url_escape, xhtml_escape

from knimin.tests.tornado_test_base import TestHandlerBase
from knimin import db


class TestAGEditBarcodeHandler(TestHandlerBase):
    # these fields switch None representation and thus are hard to check
    # for equality
    none_fields = ['environment_sampled', 'withdrawn', 'refunded']

    def test_get_not_authed(self):
        response = self.get('/ag_edit_barcode/')
        self.assertEqual(response.code, 200)
        port = self.get_http_port()
        self.assertEqual(response.effective_url,
                         'http://localhost:%d/login/?next=%s' %
                         (port, url_escape('/ag_edit_barcode/')))

    def test_get_no_auth(self):
        self.mock_login()
        response = self.get('/ag_edit_barcode/', {'barcode': '000004216'})
        self.assertEqual(response.code, 403)

    def test_get(self):
        self.mock_login_admin()

        # check that error is raised for unknown barcode
        response = self.get('/ag_edit_barcode/', {'barcode': 'unknown'})
        self.assertEqual(response.code, 500)

        # make sure return code 400 is returned, if barcode is not given
        response = self.get('/ag_edit_barcode/', {})
        self.assertEqual(response.code, 400)

        # check if page is rendered properly
        barcode = '000004216'
        response = self.get('/ag_edit_barcode/', {'barcode': barcode})
        self.assertEqual(response.code, 200)
        self.assertIn('name="barcode" id="barcode" value="%s"' %
                      barcode, response.body)
        self.assertIn('<option value="Stool" selected>Stool</option>',
                      response.body)
        self.assertIn('2013-10-15', response.body)

        hs = db.human_sites
        hs.remove('Stool')
        for s in hs:
            self.assertIn('<option value="%s">%s</option>' %
                          (str(s), str(s)), response.body)

        for e in db.general_sites:
            self.assertIn('<option value="%s">%s</option>' %
                          (str(e), str(e)), response.body)

        pname = xhtml_escape(
            db.getAGBarcodeDetails(barcode)['participant_name'])
        self.assertIn('<option value="%s" selected>%s</option>' %
                      (pname, pname), response.body)

    def test_post(self):
        details = db.getAGBarcodeDetails('000004216')
        payload = {'barcode': '000004216',
                   'ag_kit_id': details['ag_kit_id'],
                   'site_sampled': details['site_sampled'],
                   'sample_date': details['sample_date'],
                   'sample_time': details['sample_time'],
                   'participant_name': details['participant_name'],
                   'notes': details['notes'],
                   'environment_sampled': details['environment_sampled'],
                   'refunded': details['refunded'] or 'N'}

        self.mock_login_admin()
        # Missing a parameters ('withdrawn')
        response = self.post('/ag_edit_barcode/', payload)
        self.assertEqual(response.code, 400)

        payload['withdrawn'] = details['withdrawn'] or 'N'
        payload['notes'] = 'Some new notes'
        response = self.post('/ag_edit_barcode/', payload)
        self.assertEqual(response.code, 200)
        self.assertIn("Barcode was updated successfully", response.body)
        self.assertEqual(db.getAGBarcodeDetails('000004216')['notes'],
                         'Some new notes')

        payload['ag_kit_id'] = 'notInDB'
        response = self.post('/ag_edit_barcode/', payload)
        # TODO: think about returning a non-OK status code to better report
        # this error, see issue #139
        self.assertEqual(response.code, 200)
        self.assertIn("Error Updating Barcode Info", response.body)

    def test_source_reassignment(self):
        # Elaine Wolfe found this bug, May 13th:
        # Manually changing the survey a sample is assigned to is not saved
        # even after getting the "barcode has successfully been updated"
        # message. All other field changes (time, sample type, etc.) are
        # saving properly.
        self.mock_login_admin()

        # this is a barcode that belongs to a set of ag_kits which has multiple
        # participant_names, i.e. sources
        # SELECT barcode
        # FROM barcodes.barcode
        # JOIN ag.ag_kit_barcodes USING (barcode)
        # JOIN ag.ag_kit USING (ag_kit_id)
        # WHERE ag_login_id IN
        #       (SELECT ag_login_id
        #               FROM (SELECT array_agg(participant_name) as sources,
        #                            count(participant_name) as numsources,
        #                            ag_login_id FROM ag.ag_login_surveys
        #                     GROUP BY ag_login_id) as foo
        #               WHERE numsources > 2);
        barcode = '000023125'  # current survey_id = "a4f1061f5bac9ae3"
        details = db.getAGBarcodeDetails(barcode)
        payload = {'barcode': barcode,
                   'ag_kit_id': details['ag_kit_id'],
                   'site_sampled': details['site_sampled'],
                   'sample_date': details['sample_date'],
                   'sample_time': details['sample_time'],
                   'participant_name': details['participant_name'],
                   'notes': details['notes'],
                   'environment_sampled': details['environment_sampled'],
                   'refunded': details['refunded'] or 'N',
                   'withdrawn': details['withdrawn'] or 'N'}
        response = self.post('/ag_edit_barcode/', payload)
        self.assertEqual(response.code, 200)
        # check that no actual change has happened

        dbinfo = db.getAGBarcodeDetails(barcode)
        for field in payload.keys():
            if field in self.none_fields:
                if details[field] in [None, 'N', 'None', '']:
                    details[field] = None
                if dbinfo[field] in [None, 'N', 'None', '']:
                    dbinfo[field] = None
            self.assertEqual(details[field], dbinfo[field])

        # obtain all participant_names
        sql = """SELECT DISTINCT participant_name
                 FROM ag.ag_kit_barcodes
                 LEFT JOIN ag.ag_kit USING (ag_kit_id)
                 LEFT JOIN ag.ag_login_surveys USING (ag_login_id)
                 WHERE barcode = %s"""
        sourcenames = db._con.execute_fetchall(sql, [barcode])
        self.assertIsNotNone(sourcenames)

        sourcenames = [x[0] for x in sourcenames]
        # changing source for the barcode
        old_sourcename = payload['participant_name'].decode('utf-8')
        new_sourcename = list(set(sourcenames) - set(old_sourcename))[0]
        payload['participant_name'] = new_sourcename

        response = self.post('/ag_edit_barcode/', payload)
        obs_details = db.getAGBarcodeDetails(barcode)

        # revert to old participant_name to leave a clean DB
        payload['participant_name'] = old_sourcename
        response = self.post('/ag_edit_barcode/', payload)

        self.assertEqual(response.code, 200)
        self.assertEqual(obs_details['participant_name'], new_sourcename)
        self.assertTrue(obs_details['participant_name'] != old_sourcename)

    def test_edit_none_participant(self):
        self.mock_login_admin()

        barcode = '000023125'  # current survey_id = "a4f1061f5bac9ae3"
        details = db.getAGBarcodeDetails(barcode)
        payload = {'barcode': barcode,
                   'ag_kit_id': details['ag_kit_id'],
                   'site_sampled': details['site_sampled'],
                   'sample_date': details['sample_date'],
                   'sample_time': details['sample_time'],
                   'participant_name': details['participant_name'],
                   'notes': details['notes'],
                   'environment_sampled': details['environment_sampled'],
                   'refunded': details['refunded'] or 'N',
                   'withdrawn': details['withdrawn'] or 'N'}

        old_sourcename = payload['participant_name']
        payload['participant_name'] = None
        response = self.post('/ag_edit_barcode/', payload)
        obs_details = db.getAGBarcodeDetails(barcode)
        obs_surveys = db.get_barcode_survey(barcode)

        # revert to old participant_name to leave a clean DB
        payload['participant_name'] = old_sourcename
        response = self.post('/ag_edit_barcode/', payload)

        self.assertEqual(response.code, 200)
        self.assertIsNone(obs_details['participant_name'])
        self.assertIsNone(obs_surveys)
        self.assertIsNotNone(db.get_barcode_survey(barcode))


if __name__ == "__main__":
    main()

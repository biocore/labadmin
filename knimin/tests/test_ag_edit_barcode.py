# -*- coding: utf-8 -*-
from unittest import main

from tornado.escape import url_escape, xhtml_escape

from knimin.tests.tornado_test_base import TestHandlerBase
from knimin import db


class TestAGEditBarcodeHandler(TestHandlerBase):
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


if __name__ == "__main__":
    main()

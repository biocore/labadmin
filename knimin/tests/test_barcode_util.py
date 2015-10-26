from unittest import main
from random import choice
from string import ascii_letters
from knimin import db
from knimin.tests.tornado_test_base import TestHandlerBase


class TestBarcodeUtil(TestHandlerBase):
    def setUp(self):
        self.ag_good = '000001018'
        self.ag_enviro = '000009460'
        self.ag_handout = '000022146'
        self.ag_unlogged = '000022640'
        self.not_ag = '000006155'
        super(TestBarcodeUtil, self).setUp()

    def test_get_not_authed(self):
        response = self.get(
            '/barcode_util/')
        self.assertEqual(response.code, 200)
        self.assertTrue(
            response.effective_url.endswith('?next=%2Fbarcode_util%2F'))

    def test_get(self):
        self.mock_login()
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
        self.assertIn('Cannot retrieve metadata: Environmental sample',
                      response.body)

    def test_get_handout_barcode(self):
        self.mock_login()
        response = self.get('/barcode_util/', {'barcode': self.ag_handout})
        self.assertEqual(response.code, 200)
        self.assertIn(
            '<input id="barcode" name="barcode" type="text" '
            'onclick="this.select()" />',
            response.body)

        self.assertNotIn('<input class="checkbox" type="checkbox" name="sample'
                         '_issue" id="overloaded" value="overloaded" }/>',
                         response.body)

        self.assertIn('Project type: American Gut', response.body)
        self.assertIn('In American Gut project group but No American Gut info '
                      'for barcode',
                      response.body)

    def test_get_unlogged_barcode(self):
        self.mock_login()
        response = self.get('/barcode_util/', {'barcode': self.ag_unlogged})
        self.assertEqual(response.code, 200)
        self.assertIn(
            '<input id="barcode" name="barcode" type="text" '
            'onclick="this.select()" />',
            response.body)

        self.assertNotIn('<input class="checkbox" type="checkbox" name="sample'
                         '_issue" id="overloaded" value="overloaded" }/>',
                         response.body)

        self.assertIn('Project type: American Gut', response.body)
        self.assertIn('In American Gut project group but No American Gut info '
                      'for barcode',
                      response.body)

    def test_get_non_ag_barcode(self):
        self.mock_login()
        response = self.get('/barcode_util/', {'barcode': self.not_ag})
        self.assertEqual(response.code, 200)
        self.assertIn(
            '<input id="barcode" name="barcode" type="text" '
            'onclick="this.select()" />',
            response.body)

        self.assertNotIn('<input class="checkbox" type="checkbox" name="sample'
                         '_issue" id="overloaded" value="overloaded" }/>',
                         response.body)

        self.assertIn('Project type: UNKNOWN', response.body)
        self.assertIn('Barcode Info is correct', response.body)

    def test_post_update_ag(self):
        notes = ''.join([choice(ascii_letters) for x in range(40)])
        data = {
            'barcode': self.ag_good,
            'login_email': 'REMOVED',
            'email_type': '1',
            'sample_site': 'Stool',
            'login_user': 'REMOVED',
            'other_text': notes,
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
        self.mock_login()
        response = self.post('/barcode_util/', data=data)
        self.assertEqual(response.code, 200)
        self.assertIn('Barcode %s general details updated' % self.ag_good,
                      response.body)
        self.assertIn('Barcode %s AG info was sucessfully updated' %
                      self.ag_good, response.body)
        obs = db.getAGBarcodeDetails(self.ag_good)
        self.assertEqual(obs['other_text'], notes)


if __name__ == '__main__':
    main()

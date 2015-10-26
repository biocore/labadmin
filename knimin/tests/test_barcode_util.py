from unittest import main
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

    def test_post_ag_barcode(self):
        self.mock_login()
        response = self.post('/barcode_util/', {'barcode': self.ag_good})
        self.assertIn(
            '<input id="barcode" name="barcode" type="text" '
            'onclick="this.select()" />',
            response.body)

        self.assertIn('<input class="checkbox" type="checkbox" name='
                      '"sample_issue" id="overloaded" value="overloaded" }/>',
                      response.body)

        self.assertIn('Project type: American Gut', response.body)
        self.assertIn('All good', response.body)

    def test_post_enviro_barcode(self):
        self.mock_login()
        response = self.post('/barcode_util/', {'barcode': self.ag_enviro})
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

    def test_post_handout_barcode(self):
        self.mock_login()
        response = self.post('/barcode_util/', {'barcode': self.ag_handout})
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

    def test_post_unlogged_barcode(self):
        self.mock_login()
        response = self.post('/barcode_util/', {'barcode': self.ag_unlogged})
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

    def test_post_non_ag_barcode(self):
        self.mock_login()
        response = self.post('/barcode_util/', {'barcode': self.not_ag})
        self.assertIn(
            '<input id="barcode" name="barcode" type="text" '
            'onclick="this.select()" />',
            response.body)

        self.assertNotIn('<input class="checkbox" type="checkbox" name="sample'
                         '_issue" id="overloaded" value="overloaded" }/>',
                         response.body)

        self.assertIn('Project type: UNKNOWN', response.body)
        self.assertIn('Barcode Info is correct', response.body)


if __name__ == '__main__':
    main()

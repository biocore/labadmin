from unittest import main
from knimin.tests.tornado_test_base import TestHandlerBase
from knimin import db


class TestEditBarcodeHandler(TestHandlerBase):
    def test_get_no_barcode(self):
        self.mock_login_admin()
        response = self.get('/ag_edit_barcode/')
        self.assertEqual(response.code, 400)

    def test_get_no_auth(self):
        self.mock_login()
        response = self.get('/ag_edit_barcode/', {'barcode': '000004216'})
        self.assertEqual(response.code, 403)

    def test_get_barcode(self):
        self.mock_login_admin()
        response = self.get('/ag_edit_barcode/', {'barcode': '000004216'})
        self.assertEqual(response.code, 200)
        self.assertIn('Stool', response.body)
        self.assertIn('2013-10-15', response.body)

    def test_post(self):
        details = db.getAGBarcodeDetails('000004216')
        payload = {'barcode': '000004216',
                   'ag_kit_id': details['ag_kit_id'],
                   'site_sampled': details['site_sampled'],
                   'sample_date': details['sample_date'],
                   'sample_time': details['sample_time'],
                   'participant_name': details['participant_name'],
                   'notes': details['notes'],
                   'environment_sampled': details['environment_sampled']}

        if details['refunded'] is None:
            payload['refunded'] = 'N'
        else:
            payload['refunded'] = details['refunded']
        if details['withdrawn'] is None:
            payload['withdrawn'] = 'N'
        else:
            payload['withdrawn'] = details['withdrawn']

        # toggle something
        if payload['withdrawn'] == 'Y':
            payload['withdrawn'] = 'N'
        else:
            payload['withdrawn'] = 'Y'

        self.assertNotEqual(details['withdrawn'], payload['withdrawn'])

        self.mock_login_admin()
        response = self.post('/ag_edit_barcode/', payload)

        self.assertEqual(response.code, 200)
        self.assertIn('Barcode was updated successfully', response.body)

        details = db.getAGBarcodeDetails('000004216')
        self.assertEqual(details['withdrawn'], payload['withdrawn'])


if __name__ == '__main__':
    main()

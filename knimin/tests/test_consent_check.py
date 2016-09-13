from unittest import main
from knimin.tests.tornado_test_base import TestHandlerBase


class TestConsentCheckHandler(TestHandlerBase):
    def test_get(self):
        self.mock_login()
        response = self.get('/consent_check')
        self.assertEqual(response.code, 200)
        self.assertIn('Knight lab admin - AG Consent Checker', response.body)

    def test_post_has_consent(self):
        self.mock_login()
        response = self.post('/consent_check', {'barcodes': ['000004216']})
        self.assertEqual(response.code, 200)
        self.assertIn('000004216</td><td style="color:green">', response.body)

    def test_post_no_consent(self):
        self.mock_login()
        response = self.post('/consent_check', {'barcodes': ['000004126']})
        self.assertEqual(response.code, 200)
        self.assertIn('000004126</td><td style="color:red">', response.body)

if __name__ == '__main__':
    main()

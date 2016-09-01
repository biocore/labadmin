from unittest import main
from knimin.tests.tornado_test_base import TestHandlerBase
from knimin import db


class TestConsentCheckHandler(TestHandlerBase):
    def test_get(self):
        self.mock_login()
        response = self.get('/consent_check')
        self.assertEqual(response.code, 200)
        self.assertIn('Knight lab admin - AG Consent Checker', response.body)

    def test_post(self):
        self.mock_login()
        response = self.post('/consent_check', {'barcodes': []})
        self.assertEqual(response.code, 200)


if __name__ == '__main__':
    main()

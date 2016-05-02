from unittest import TestCase, main
from os.path import join, dirname, realpath
import datetime
from knimin import db


class TestDataAccess(TestCase):
    ext_survey_fp = join(dirname(realpath(__file__)), '..', '..', 'tests',
                         'data', 'external_survey_data.csv')

    def setUp(self):
        # Make sure vioscreen survey exists in DB
        try:
            db.add_external_survey('Vioscreen', 'FFQ', 'http://vioscreen.com')
        except ValueError:
            pass

    def tearDown(self):
        db._clear_table('external_survey_answers', 'ag')

    def test_pulldown_third_party(self):
        # Add survey answers
        with open(self.ext_survey_fp, 'rU') as f:
            obs = db.store_external_survey(
                f, 'Vioscreen', separator=',', survey_id_col='SubjectId',
                trim='-160')
        self.assertEqual(obs, 3)

        barcodes = ['000029429', '000018046', '000023299', '000023300']
        # Test without third party
        obs, _ = db.pulldown(barcodes)
        survey = obs[1]
        self.assertFalse('VIOSCREEN' in survey)

        obs, _ = db.pulldown(barcodes, blanks=['BLANK.01'])
        survey = obs[1]
        self.assertFalse('VIOSCREEN' in survey)
        self.assertTrue('BLANK.01' in survey)

        # Test with third party
        obs, _ = db.pulldown(barcodes, external=['Vioscreen'])
        survey = obs[1]
        self.assertTrue('VIOSCREEN' in survey)

        obs, _ = db.pulldown(barcodes, blanks=['BLANK.01'],
                             external=['Vioscreen'])
        survey = obs[1]
        self.assertTrue('VIOSCREEN' in survey)
        self.assertTrue('BLANK.01' in survey)

    def test_check_consent(self):
        consent, fail = db.check_consent(['000027561', '000001124', '0000000'])
        self.assertEqual(consent, ['000027561'])
        self.assertEqual(fail, {'0000000': 'Not an AG barcode',
                                '000001124': 'Sample not logged'})

    def test_get_unconsented(self):
        obs = db.get_unconsented()
        self.assertEqual(len(obs), 433)
        exp = ['000014660', datetime.date(2015, 3, 25), 'REMOVED']
        self.assertEqual(obs[0], exp)

    def test_get_user_for_kit(self):
        obs = self.ag_data.get_user_for_kit('tst_IueFX')
        self.assertEqual('ded5101d-c8e3-f6b3-e040-8a80115d6f03', obs)

        obs = self.ag_data.get_user_for_kit('tst_esABz')
        self.assertEqual('d8592c74-8421-2135-e040-8a80115d6401', obs)

    def test_get_user_for_kit_errors(self):
        with self.assertRaises(ValueError):
            self.ag_data.get_user_for_kit('the_fooster')

        with self.assertRaises(ValueError):
            self.ag_data.get_user_for_kit('tst_esXXX')


if __name__ == "__main__":
    main()

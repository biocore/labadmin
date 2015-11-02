from unittest import TestCase, main
from os.path import join, dirname, realpath
from knimin import db


class TestDataAccess(TestCase):
    ext_survey_fp = join(dirname(realpath(__file__)), '..', '..', 'tests',
                         'data', 'external_survey_data.csv')

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

        # Test with third party
        obs, _ = db.pulldown(barcodes, external=['Vioscreen'])
        survey = obs[1]
        print survey
        self.assertTrue('VIOSCREEN' in survey)


if __name__ == "__main__":
    main()

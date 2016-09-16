from unittest import TestCase, main
from os.path import join, dirname, realpath
from six import StringIO
import datetime

import pandas as pd

from knimin import db
from knimin.lib.constants import ebi_remove


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
        db._revert_ready(['000023299'])

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

        # Parse the metadata into a pandas dataframe to test some invariants
        # This tests does not ensure that the columns have the exact value
        # but at least ensure that the contents looks as expected
        survey_df = pd.read_csv(
            StringIO(obs[1]), delimiter='\t', dtype=str, encoding='utf-8')
        survey_df.set_index('sample_name', inplace=True, drop=True)

        # Make sure that the prohibited columns from EBI are not in the
        # pulldown
        self.assertEqual(set(survey_df.columns).intersection(ebi_remove),
                         set())

        freq_accepted_vals = {
            'Never', 'Rarely (a few times/month)',
            'Regularly (3-5 times/week)', 'Occasionally (1-2 times/week)',
            'Unspecified', 'Daily'}

        freq_cols = ['ALCOHOL_FREQUENCY', 'PROBIOTIC_FREQUENCY',
                     'ONE_LITER_OF_WATER_A_DAY_FREQUENCY', 'POOL_FREQUENCY',
                     'FLOSSING_FREQUENCY', 'COSMETICS_FREQUENCY']

        for col in freq_cols:
            vals = set(survey_df[col])
            self.assertTrue(all([x in freq_accepted_vals for x in vals]))

        # This astype is making sure that the values in the BMI column are
        # values that can be casted to float.
        survey_df.BMI.astype(float)

        body_product_values = set(survey_df.BODY_PRODUCT)
        self.assertTrue(all([x.startswith('UBERON') or x == 'Unspecified'
                             for x in body_product_values]))

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
        exp = ['000001000', datetime.date(2015, 4, 10), 'REMOVED']
        self.assertEqual(obs[0], exp)

    def test_search_kits(self):
        obs = db.search_kits('tst_IueFX')
        self.assertEqual(['ded5101d-c8e3-f6b3-e040-8a80115d6f03'], obs)

        obs = db.search_kits('e1934dfe-8537-6dce-e040-8a80115d2da9')
        self.assertEqual(['e1934ceb-6e92-c36a-e040-8a80115d2d64'], obs)

        obs = db.search_kits('000001124')
        self.assertEqual([], obs)

    def test_get_barcodes_with_results(self):
        obs = db.get_barcodes_with_results()
        exp = ['000023299']
        self.assertEqual(obs, exp)

    def test_mark_results_ready(self):
        db._revert_ready(['000023299'])
        obs = db.get_ag_barcode_details(['000001072', '000023299'])
        self.assertEqual(obs['000023299']['results_ready'], None)
        self.assertEqual(obs['000001072']['results_ready'], 'Y')

        obs = db.mark_results_ready(['000001072', '000023299'], debug=True)
        self.assertEqual(obs['new_bcs'], ('000023299', ))
        self.assertEqual(obs['mail']['mimetext']['To'],
                         'americangut@gmail.com')
        self.assertEqual(obs['mail']['mimetext']['From'], '')
        self.assertEqual(obs['mail']['mimetext']['Subject'],
                         'Your American/British Gut results are ready')
        self.assertEqual(obs['mail']['recipients'],
                         ['americangut@gmail.com', 'REMOVED'])

        obs = db.get_ag_barcode_details(['000001072', '000023299'])
        self.assertEqual(obs['000023299']['results_ready'], 'Y')
        self.assertEqual(obs['000001072']['results_ready'], 'Y')

    def test_get_access_levels_user(self):
        obs = db.get_access_levels_user('test')
        self.assertEqual(obs, [])

        db.alter_access_levels('test', [1, 6])
        obs = db.get_access_levels_user('test')
        self.assertEqual(obs, [[1, 'Barcodes'], [6, 'Search']])

        db.alter_access_levels('test', [])
        obs = db.get_access_levels_user('test')
        self.assertEqual(obs, [])

    def test_get_users(self):
        obs = db.get_users()
        exp = ['test']
        self.assertEqual(obs, exp)

    def test_get_access_levels(self):
        obs = db.get_access_levels()
        exp = [[1, 'Barcodes'], [2, 'AG kits'], [3, 'Scan Barcodes'],
               [4, 'External surveys'], [5, 'Metadata Pulldown'],
               [6, 'Search'], [7, 'Admin']]
        self.assertEqual(obs, exp)

    def test_participant_names(self):
        obs = db.participant_names()
        self.assertEqual(len(obs), 8237)
        self.assertEqual(obs[0], ['000027561', 'REMOVED-0'])

    def test_search_barcodes(self):
        obs = db.search_barcodes('000001124')
        self.assertEqual(obs, ['d8592c74-7c27-2135-e040-8a80115d6401'])

        obs = db.search_barcodes('REMOVED-8')
        exp = ['d8592c74-7da1-2135-e040-8a80115d6401',
               '00711b0a-67d6-0fed-e050-8a800c5d7570',
               'd8592c74-9491-2135-e040-8a80115d6401',
               'f37dc99e-2241-3a4f-e040-8a80115d1694',
               'e025e238-4529-77a9-e040-8a80115d503f',
               'e76468db-82ca-bf84-e040-8a80115d55dc',
               'fa66366c-12f2-50aa-e040-8a800c5d6584',
               'df703c65-b700-401c-e040-8a80115d46ed',
               'e02a84fb-8db9-1e6a-e040-8a80115d6e16']
        self.assertEqual(obs, exp)

    def test_getAGBarcodeDetails(self):
        obs = db.getAGBarcodeDetails('000018046')
        exp = {'status': 'Received',
               'ag_kit_id': '0060a301-e5c0-6a4e-e050-8a800c5d49b7',
               'barcode': '000018046',
               'environment_sampled': None,
               'name': 'REMOVED',
               'ag_kit_barcode_id': '0060a301-e5c1-6a4e-e050-8a800c5d49b7',
               'sample_time': datetime.time(11, 15),
               'notes': 'REMOVED',
               'overloaded': 'N',
               'withdrawn': None, 'email': 'REMOVED',
               'other': 'N', 'deposited': False,
               'participant_name': 'REMOVED-0',
               'refunded': None, 'moldy': 'N',
               'sample_date': datetime.date(2014, 8, 13),
               'date_of_last_email': datetime.date(2014, 8, 15),
               'other_text': 'REMOVED',
               'site_sampled': 'Stool'}
        self.assertEqual(obs, exp)

    def test_get_barcode_info_by_kit_id(self):
        obs = db.get_barcode_info_by_kit_id(
            '0060a301-e5c0-6a4e-e050-8a800c5d49b7')
        exp = [{'ag_kit_id': '0060a301-e5c0-6a4e-e050-8a800c5d49b7',
                'environment_sampled': None,
                'sample_time': datetime.time(11, 15),
                'notes': 'REMOVED',
                'barcode': '000018046',
                'results_ready': 'Y',
                'refunded': None,
                'participant_name': 'REMOVED-0',
                'ag_kit_barcode_id': '0060a301-e5c1-6a4e-e050-8a800c5d49b7',
                'sample_date': datetime.date(2014, 8, 13),
                'withdrawn': None,
                'site_sampled': 'Stool'}]
        self.assertEqual(obs, exp)

    def test_getHumanParticipants(self):
        i = "d8592c74-9694-2135-e040-8a80115d6401"
        res = db.getHumanParticipants(i)
        exp = ['REMOVED-2', 'REMOVED-0', 'REMOVED-3', 'REMOVED-1']
        self.assertItemsEqual(res, exp)

    def test_getHumanParticipantsNotPresent(self):
        i = '00000000-0000-0000-0000-000000000000'
        res = db.getHumanParticipants(i)
        self.assertEqual(res, [])

    def test_getAnimalParticipants(self):
        i = "ed5ab96f-fe3b-ead5-e040-8a80115d1c4b"
        res = db.getAnimalParticipants(i)
        exp = ['REMOVED-0']
        self.assertItemsEqual(res, exp)

    def test_getAnimalParticipantsNotPresent(self):
        i = "00711b0a-67d6-0fed-e050-8a800c5d7570"
        res = db.getAnimalParticipants(i)
        self.assertEqual(res, [])

    def test_get_ag_barcode_details(self):
        obs = db.get_ag_barcode_details(['000018046'])
        exp = {'000018046': {
                'ag_kit_barcode_id': '0060a301-e5c1-6a4e-e050-8a800c5d49b7',
                'verification_email_sent': 'n',
                'pass_reset_code': None,
                'vioscreen_status': 3,
                'sample_barcode_file': '000018046.jpg',
                'environment_sampled': None,
                'supplied_kit_id': 'tst_nVEyP',
                'withdrawn': None,
                'kit_verified': 'y',
                'city': 'REMOVED',
                'ag_kit_id': '0060a301-e5c0-6a4e-e050-8a800c5d49b7',
                'zip': 'REMOVED',
                'ag_login_id': '0060a301-e5bf-6a4e-e050-8a800c5d49b7',
                'state': 'REMOVED',
                'results_ready': 'Y',
                'moldy': 'N',
                # The key 'registered_on' is a time stamp when the database is
                # created. It is unique per deployment.
                # 'registered_on': datetime.datetime(2016, 8, 17, 10, 47, 2,
                #                                   713292),
                'participant_name': 'REMOVED-0',
                'kit_password': ('$2a$12$LiakUCHOpAMvEp9Wxehw5OIlD/TIIP0Bs3blw'
                                 '18ePcmKHWWAePrQ.'),
                'deposited': False,
                'sample_date': datetime.date(2014, 8, 13),
                'email': 'REMOVED',
                'print_results': False,
                'open_humans_token': None,
                'elevation': 0.0,
                'refunded': None,
                'other_text': 'REMOVED',
                'barcode': '000018046',
                'swabs_per_kit': 1L,
                'kit_verification_code': '60260',
                'latitude': 0.0,
                'cannot_geocode': None,
                'address': 'REMOVED',
                'date_of_last_email': datetime.date(2014, 8, 15),
                'site_sampled': 'Stool',
                'name': 'REMOVED',
                'sample_time': datetime.time(11, 15),
                'notes': 'REMOVED',
                'overloaded': 'N',
                'longitude': 0.0,
                'pass_reset_time': None,
                'country': 'REMOVED',
                'survey_id': '084532330aca5885',
                'other': 'N',
                'sample_barcode_file_md5': None
        }}
        for key in obs:
            del(obs[key]['registered_on'])
        self.assertEqual(obs, exp)

    def test_plate_operations(self):
        """Test four functions involving read/write operations to tables
        pm.sample and pm.plate

        Notes
        -----
        They are put together in one test, because they are dependent on each
        other.
        """
        # setUp
        sample_ids = ['test_sample_1', 'test_sample_2', 'test_sample_3']
        db._add_new_samples(sample_ids)
        plate_id = db._get_new_plate_id()

        # Test set_plate_info
        # Create new plate
        plate_info = {
            'name': 'test plate 01',
            'email': 'test',
            'plate_type_id': 1,  # 96-well
            'linker_seq': 'GT',
            'extraction_robot_id': 1  # HOWE_KF1
        }
        obs = db.set_plate_info(0, plate_info)
        exp = plate_id
        self.assertEqual(obs, exp)
        # Edit existing plate
        plate_info = {
            'processing_robot_id': 2,  # RIKE
            'tm300_8_tool_id': 3,  # 109375A
        }
        obs = db.set_plate_info(plate_id, plate_info)
        exp = plate_id
        self.assertEqual(obs, exp)

        # Test get_plate_info:
        exp = {
            'plate_id': plate_id,
            'name': 'test plate 01',
            'email': 'test',
            'plate_type_id': 1,
            'template_id': None,
            'linker_seq': 'GT',
            'extraction_kit_lot_id': None,
            'extraction_robot_id': 1,  # HOWE_KF1
            'tm1000_8_tool_id': None,
            'master_mix_lot_id': None,
            'water_lot_id': None,
            'processing_robot_id': 2,  # RIKE
            'tm300_8_tool_id': 3,  # 109375A
            'tm50_8_tool_id': None,
            'notes': None
        }
        obs = db.set_plate_info(plate_id, plate_info)
        exp = plate_id
        self.assertEqual(obs, exp)

        # Test set_plate_map
        # Add two samples
        plate_map = [(1, 1, 'test_sample_1'), (1, 2, 'test_sample_2')]
        obs = db.set_plate_map(plate_id, plate_map)
        exp = (2, 0, 0)
        self.assertTupleEqual(obs, exp)
        # Modify one sample
        plate_map = [(1, 2, 'test_sample_3')]
        obs = db.set_plate_map(plate_id, plate_map)
        exp = (0, 1, 0)
        self.assertTupleEqual(obs, exp)
        # Delete one sample
        plate_map = [(1, 1, '')]
        obs = db.set_plate_map(plate_id, plate_map)
        exp = (0, 0, 1)
        self.assertTupleEqual(obs, exp)

        # Test get_plate_map
        exp = [[1, 2, 'test_sample_3']]
        obs = db.get_plate_map(plate_id)
        self.assertListEqual(obs, exp)

        # tearDown
        db.set_plate_map(plate_id, [(1, 2, '')])
        db._delete_new_plate(plate_id)
        db._delete_new_samples(sample_ids)

    def test_get_plate_type(self):
        exp = {'plate_type_id': 1,
               'name': '96-well',
               'cols': 12,
               'rows': 8,
               'notes': 'Standard 96-well plate'}
        obs = db.get_plate_type(0)
        self.assertDictEqual(obs, exp)


if __name__ == "__main__":
    main()

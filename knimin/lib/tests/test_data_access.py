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
        # Populate some field options
#        sql = """INSERT INTO pm.plate_type (name, cols, rows, notes)
#                 VALUES ('96-well', 12, 8, 'Standard 96-well plate')"""
#        db._con.execute(sql)
#        sql = """INSERT INTO pm.extraction_robot (name) VALUES ('HOWE_KF1'),
#                 ('HOWE_KF2'), ('HOWE_KF3'), ('HOWE_KF4')"""
#        db._con.execute(sql)
#        sql = """INSERT INTO pm.extraction_tool (name) VALUES ('108379Z')"""
#        db._con.execute(sql)
#        sql = """INSERT INTO pm.processing_robot (name) VALUES ('ROBE'),
#                 ('RIKE'), ('JERE'), ('CARMEN')"""
#        sql = """INSERT INTO pm.tm300_8_tool (name) VALUES ('208484Z'),
#                 ('311318B'), ('109375A'), ('3076189')"""
#        sql = """INSERT INTO pm.tm50_8_tool (name) VALUES ('108364Z'),
#                 ('311426B'), ('311441B'), ('409172Z')"""
#        db._con.execute(sql)
#       sql = """INSERT INTO pm.extraction_kit_lot (name) VALUES ('PM16B11')"""
#        db._con.execute(sql)
#        sql = """INSERT INTO pm.master_mix_lot (name) VALUES ('14459')"""
#        db._con.execute(sql)
#        sql = """INSERT INTO pm.water_lot (name) VALUES ('RNBD9959')"""
#        db._con.execute(sql)

    def tearDown(self):
        db._clear_table('external_survey_answers', 'ag')
        db._revert_ready(['000023299'])
        # Remove populated field options
#        db._clear_table('plate_type', 'pm')
#        db._clear_table('extraction_robot', 'pm')
#        db._clear_table('extraction_tool', 'pm')
#        db._clear_table('processing_robot', 'pm')
#        db._clear_table('tm300_8_tool', 'pm')
#        db._clear_table('tm50_8_tool', 'pm')
#        db._clear_table('extraction_kit_lot', 'pm')
#        db._clear_table('master_mix_lot', 'pm')
#        db._clear_table('water_lot', 'pm')

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

    def test_get_id_by_name(self):
        obs = db.get_id_by_name('extraction_robot', 'HOWE_KF1')
        exp = 1
        self.assertEqual(obs, exp)
        with self.assertRaises(ValueError):
            db.get_id_by_name('extraction_robot', 'an_invalid_name')

    def test_create_study(self):
        # Create a study with title
        obs = db.create_study(123, title='Test study 1')
        self.assertTrue(obs)
        obs = db.read_study(123)
        exp = {'title': 'Test study 1', 'alias': None, 'notes': None}
        self.assertDictEqual(obs, exp)
        # Create a study with empty title
        obs = db.create_study(456, title='', alias='the study')
        self.assertTrue(obs)
        obs = db.read_study(456)
        exp = {'title': None, 'alias': 'the study', 'notes': None}
        self.assertDictEqual(obs, exp)
        # Attempt to create a study with duplicate ID
        with self.assertRaises(ValueError) as context:
            db.create_study(123, title='Test study 2')
        err = ('Study ID or title conflicts with exisiting study 123: '
               'Test study 1.')
        self.assertEqual(str(context.exception), err)
        obs = db.read_study(123)['title']
        exp = 'Test study 2'
        self.assertNotEqual(obs, exp)
        # Attempt to create a study with duplicate title
        with self.assertRaises(ValueError) as context:
            db.create_study(789, title='Test study 1')
        err = ('Study ID or title conflicts with exisiting study 123: '
               'Test study 1.')
        self.assertEqual(str(context.exception), err)
        with self.assertRaises(ValueError) as context:
            db.read_study(789)
        err = 'Study ID 789 does not exist.'
        self.assertEqual(str(context.exception), err)
        db.delete_study(123)
        db.delete_study(456)

    def test_edit_study(self):
        # Edit properties of a study
        db.create_study(123, title='Test study 1')
        obs = db.read_study(123)
        exp = {'title': 'Test study 1', 'alias': None, 'notes': None}
        self.assertDictEqual(obs, exp)
        obs = db.edit_study(123, title='Test study 1', alias='the study',
                            notes='Say something.')
        self.assertTrue(obs)
        obs = db.read_study(123)
        exp = {'title': 'Test study 1', 'alias': 'the study',
               'notes': 'Say something.'}
        self.assertDictEqual(obs, exp)
        # Attempt to assign a duplicate title to a study
        obs = db.create_study(456)
        self.assertIsNotNone(obs)
        with self.assertRaises(ValueError) as context:
            db.edit_study(456, title='Test study 1')
        err = 'Study title "Test study 1" conflicts with another study: 123.'
        self.assertEqual(str(context.exception), err)
        db.delete_study(123)
        db.delete_study(456)
        # Attempt to edit properties of a non-existing study
        with self.assertRaises(ValueError) as context:
            db.read_study(123)
        err = 'Study ID 123 does not exist.'
        self.assertEqual(str(context.exception), err)

    def test_read_study(self):
        # Read properties of a study
        db.create_study(123, title='Test study 1', alias='the study',
                        notes='There is nothing to say.')
        obs = db.read_study(123)
        exp = {'title': 'Test study 1', 'alias': 'the study',
               'notes': 'There is nothing to say.'}
        self.assertDictEqual(obs, exp)
        db.delete_study(123)
        # Attempt to read properties of a non-existing study
        with self.assertRaises(ValueError) as context:
            db.read_study(123)
        err = 'Study ID 123 does not exist.'
        self.assertEqual(str(context.exception), err)

    def test_delete_study(self):
        # Delete a study
        db.create_study(123, title='Test study 1')
        obs = db.read_study(123)
        self.assertIsNotNone(obs)
        obs = db.delete_study(123)
        self.assertTrue(obs)
        with self.assertRaises(ValueError):
            db.read_study(123)
        # Attempt to delete a non-existing study
        with self.assertRaises(ValueError) as context:
            db.delete_study(123)
        err = 'Study ID 123 does not exist.'
        self.assertEqual(str(context.exception), err)

    def test_delete_sample(self):
        sample_ids = ['test_sample_1']
        db.create_sample(sample_ids)
        obs = db.delete_sample(sample_ids)
        self.assertTrue(obs)

    def test_create_sample(self):
        sample_ids = ['test_sample_1']
        obs = db.create_sample(sample_ids)
        self.assertTrue(obs)
        db.delete_sample(sample_ids)

    def test_delete_sample(self):
        sample_ids = ['test_sample_1']
        db.create_sample(sample_ids)
        obs = db.delete_sample(sample_ids)
        self.assertTrue(obs)

    def test_create_sample_plate(self):
        spinfo = ('test_plate', 'test', datetime.date.today(), '', '96-well')
        obs = db.create_sample_plate(spinfo)
        self.assertGreater(obs, 0)
        db.delete_sample_plate([obs])

    def test_set_sample_plate_info(self):
        spid = db.create_sample_plate(('test_plate', '', None, '', '96-well'))
        spinfo = ('test_plate', 'test', datetime.date.today(), '', '96-well')
        obs = db.set_sample_plate_info(spid, spinfo)
        self.assertTrue(obs)
        db.delete_sample_plate([spid])

    def test_get_sample_plate_info(self):
        timestamp = datetime.datetime(2016, 8, 15, 0, 0)
        spinfo = ('test_plate', 'test', timestamp, 'Test notes', '96-well')
        spid = db.create_sample_plate(spinfo)
        obs = db.get_sample_plate_info(spid)
        exp = spinfo
        self.assertTupleEqual(obs, exp)
        db.delete_sample_plate([spid])

    def test_set_sample_plate_layout(self):
        sample_ids = ['test_sample_1', 'test_sample_2', 'test_sample_3']
        db.create_sample(sample_ids)
        spid = db.create_sample_plate(('test_plate', '', None, '', '96-well'))
        splayout = [
            ('test_sample_1', 1, 1, '', ''),
            ('test_sample_2', 1, 2, 'B', 'duplicate'),
            ('test_sample_3', 1, 3, '', 'low'),
        ]
        obs = db.set_sample_plate_layout(spid, splayout)
        self.assertTrue(obs)
        db.delete_sample_plate([spid])
        db.delete_sample(sample_ids)

    def test_get_sample_plate_layout(self):
        sample_ids = ['test_sample_1', 'test_sample_2', 'test_sample_3']
        db.create_sample(sample_ids)
        spid = db.create_sample_plate(('test_plate', '', None, '', '96-well'))
        splayout = [
            ('test_sample_1', 1, '1', None, None),
            ('test_sample_2', 1, '2', 'B', 'duplicate'),
            ('test_sample_3', 1, '3', None, 'low')
        ]
        db.set_sample_plate_layout(spid, splayout)
        obs = db.get_sample_plate_layout(spid)
        exp = splayout
        self.assertListEqual(obs, exp)
        db.delete_sample_plate([spid])
        db.delete_sample(sample_ids)

    def test_delete_sample_plate(self):
        spinfo = ('test_plate', 'test', datetime.date.today(), '', '96-well')
        spid = db.create_sample_plate(spinfo)
        obs = db.delete_sample_plate([spid])
        self.assertTrue(obs)

    def test_create_dna_plate(self):
        spid = db.create_sample_plate('test_sample_plate', 'test', '96-well')
        obs = db.create_dna_plate('test_dna_plate', 'test', spid)
        self.assertGreater(obs, 0)
        db.delete_dna_plate([obs])
        db.delete_sample_plate([spid])

    def test_delete_dna_plate(self):
        spid = db.create_sample_plate('test_sample_plate', 'test', '96-well')
        dpid = db.create_dna_plate('test_dna_plate', 'test', spid)
        obs = db.delete_dna_plate([dpid])
        self.assertTrue(obs)
        db.delete_sample_plate([spid])

    def test_get_plate_type(self):
        obs = db.get_plate_type(0)
        exp = {'plate_type_id': 1,
               'name': '96-well',
               'cols': 12,
               'rows': 8,
               'notes': 'Standard 96-well plate'}
        self.assertDictEqual(obs, exp)

    def test_get_plate_count(self):
        plate_id = db.create_plate('test_plate_1', 'test', '96-well')
        obs = db.get_plate_count()
        self.assertGreater(obs, 0)
        db.delete_plate([plate_id])

    def test_get_plate_list(self):
        sample_ids = ['test_sample_1', 'test_sample_2', 'test_sample_3']
        db.create_sample(sample_ids)
        n_plate = db.get_plate_count()
        plate_1_id = db.create_plate('test_plate_1', 'test', '96-well')
        plate_map = [(1, 1, sample_ids[0]), (1, 2, sample_ids[1])]
        db.set_plate_map(plate_1_id, plate_map)
        plate_2_id = db.create_plate('test_plate_2', 'test', '96-well')
        plate_map = [(2, 3, sample_ids[2])]
        db.set_plate_map(plate_2_id, plate_map)
        obs = db.get_plate_list(2, n_plate)
        exp = [
            (plate_1_id, 'test_plate_1', '96-well', 2, 'test'),
            (plate_2_id, 'test_plate_2', '96-well', 1, 'test')
        ]
        self.assertListEqual(obs, exp)
        db.delete_plate([plate_1_id, plate_2_id])
        db.delete_sample(sample_ids)


if __name__ == "__main__":
    main()

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

    def test_create_study(self):
        # Create a study with all properties
        sid = db.create_study(qiita_study_id=123, title='Test study 1',
                              alias='the study', notes='hi there')
        self.assertGreater(sid, 0)
        obs = db.read_study(sid)
        exp = {'qiita_study_id': 123, 'title': 'Test study 1',
               'alias': 'the study', 'notes': 'hi there'}
        self.assertDictEqual(obs, exp)
        # Attempt to create a study without identifier
        with self.assertRaises(ValueError) as context:
            db.create_study()
        err = 'Either Qiita study ID or Title must be specified.'
        self.assertEqual(str(context.exception), err)
        # Attempt to create a study with duplicate title
        with self.assertRaises(ValueError) as context:
            db.create_study(qiita_study_id=456, title='Test study 1')
        err = 'Title \'Test study 1\' conflicts with exisiting study %s.' % sid
        self.assertEqual(str(context.exception), err)
        # Attempt to create a study with duplicate Qiita study ID
        with self.assertRaises(ValueError) as context:
            db.create_study(qiita_study_id=123, title='Test study 2')
        err = 'Qiita study ID 123 conflicts with exisiting study %s.' % sid
        self.assertEqual(str(context.exception), err)
        # Attempt to create a study with duplicate Qiita study ID and title
        with self.assertRaises(ValueError) as context:
            db.create_study(qiita_study_id=123, title='Test study 1')
        err = ('Qiita study ID 123 conflicts with exisiting study %s.\n'
               'Title \'Test study 1\' conflicts with exisiting study %s.'
               % (sid, sid))
        self.assertEqual(str(context.exception), err)
        db.delete_study(sid)

    def test_edit_study(self):
        # Edit properties of a study
        sid = db.create_study(qiita_study_id=123, title='Test study 1')
        obs = db.read_study(sid)
        exp = {'qiita_study_id': 123, 'title': 'Test study 1', 'alias': None,
               'notes': None}
        self.assertDictEqual(obs, exp)
        db.edit_study(sid, qiita_study_id=456, title='Test study 2',
                      alias='the study', notes='Say something.')
        obs = db.read_study(sid)
        exp = {'qiita_study_id': 456, 'title': 'Test study 2',
               'alias': 'the study', 'notes': 'Say something.'}
        self.assertDictEqual(obs, exp)
        # Attempt to assign a duplicate title to a study
        sid2 = db.create_study(qiita_study_id=123, title='Test study 1')
        with self.assertRaises(ValueError) as context:
            db.edit_study(sid2, qiita_study_id=123, title='Test study 2')
        err = 'Title \'Test study 2\' conflicts with exisiting study %s.' % sid
        self.assertEqual(str(context.exception), err)
        # Attempt to assign a duplicate Qiita study ID to a study
        with self.assertRaises(ValueError) as context:
            db.edit_study(sid2, qiita_study_id=456, title='Test study 1')
        err = 'Qiita study ID 456 conflicts with exisiting study %s.' % sid
        self.assertEqual(str(context.exception), err)
        db.delete_study(sid2)
        db.delete_study(sid)
        # Attempt to edit properties of a non-existing study
        with self.assertRaises(ValueError) as context:
            db.edit_study(sid, qiita_study_id=789, title='Test study 3')
        err = 'Study ID %s does not exist.' % sid
        self.assertEqual(str(context.exception), err)

    def test_read_study(self):
        # Read properties of a study
        sid = db.create_study(qiita_study_id=123, title='Test study 1',
                              alias='the study', notes='Say something.')
        obs = db.read_study(sid)
        exp = {'qiita_study_id': 123, 'title': 'Test study 1',
               'alias': 'the study', 'notes': 'Say something.'}
        self.assertDictEqual(obs, exp)
        db.delete_study(sid)
        # Attempt to read properties of a non-existing study
        with self.assertRaises(ValueError) as context:
            db.read_study(sid)
        err = 'Study ID %s does not exist.' % sid
        self.assertEqual(str(context.exception), err)

    def test_delete_study(self):
        # Delete a study without samples
        sid = db.create_study(qiita_study_id=123, title='study')
        obs = db.read_study(sid)
        self.assertIsNotNone(obs)
        db.delete_study(sid)
        with self.assertRaises(ValueError):
            db.read_study(sid)
        # Delete a study with three samples associated, two of which are also
        # associated with other studies
        sids = [db.create_study(title='study%s' % x) for x in range(3)]
        samples = [{'id': '1', 'study_ids': [sids[0]]},
                   {'id': '2', 'study_ids': [sids[0], sids[1]]},
                   {'id': '3', 'study_ids': [sids[0], sids[2]]}]
        db.create_samples(samples)
        obs = db.read_samples(['1', '2', '3'])
        exp = {'1': {'is_blank': False, 'barcode': None, 'notes': None,
                     'study_ids': [sids[0]]},
               '2': {'is_blank': False, 'barcode': None, 'notes': None,
                     'study_ids': sorted([sids[0], sids[1]])},
               '3': {'is_blank': False, 'barcode': None, 'notes': None,
                     'study_ids': sorted([sids[0], sids[2]])}}
        self.assertDictEqual(obs, exp)
        db.delete_study(sids[0])
        with self.assertRaises(ValueError):
            db.read_study(sids[0])
        obs = db.read_samples(['1', '2', '3'])
        exp = {'2': {'is_blank': False, 'barcode': None, 'notes': None,
                     'study_ids': [sids[1]]},
               '3': {'is_blank': False, 'barcode': None, 'notes': None,
                     'study_ids': [sids[2]]}}
        self.assertDictEqual(obs, exp)
        db.delete_samples(['2', '3'])
        db.delete_study(sids[1])
        db.delete_study(sids[2])
        # Attempt to delete a non-existing study
        with self.assertRaises(ValueError) as context:
            db.delete_study(sid)
        err = 'Study ID %s does not exist.' % sid
        self.assertEqual(str(context.exception), err)

    def test_create_samples(self):
        # Create three samples with sample IDs only
        sid = db.create_study(title='study')
        samples = [{'id': x, 'study_ids': [sid]} for x in ('1', '2', '3')]
        db.create_samples(samples)
        obs = db.read_samples(['1', '2', '3'])
        exp = {x: {'is_blank': False, 'barcode': None, 'notes': None,
                   'study_ids': [sid]} for x in ('1', '2', '3')}
        self.assertDictEqual(obs, exp)
        # Create a sample with barcode, without is_blank, and associated with
        # two studies
        sid2 = db.create_study(title='study2')
        sql = """SELECT barcode FROM barcodes.barcode LIMIT 1"""
        barcode = db._con.execute_fetchone(sql)[0]
        samples = [{'id': '4', 'barcode': barcode, 'notes': 'Hi!',
                    'study_ids': [sid, sid2]}]
        db.create_samples(samples)
        obs = db.read_samples(['4'])
        exp = {'4': {'is_blank': False, 'barcode': barcode, 'notes': 'Hi!',
               'study_ids': sorted([sid, sid2])}}
        self.assertDictEqual(obs, exp)
        # Attempt to create a sample with an invalid barcode
        samples = [{'id': '5', 'barcode': 'whatever', 'study_ids': [sid]}]
        with self.assertRaises(ValueError) as context:
            db.create_samples(samples)
        err = 'Barcode(s) whatever do not exist.'
        self.assertEqual(str(context.exception), err)
        # Attempt to create two samples, one with duplicate ID
        samples = [{'id': x, 'study_ids': [sid]} for x in ('5', '1')]
        with self.assertRaises(ValueError) as context:
            db.create_samples(samples)
        err = 'Sample ID(s) 1 already exist.'
        self.assertEqual(str(context.exception), err)
        # Test if one duplicate ID fails the creation of all samples
        obs = db.read_samples(['5'])
        self.assertDictEqual(obs, {})
        db.delete_samples(['1', '2', '3', '4'])
        db.delete_study(sid)
        db.delete_study(sid2)

    def test_edit_samples(self):
        # Assign properties to a sample and alter its associated study
        sid = db.create_study(title='study')
        db.create_samples([{'id': '1', 'study_ids': [sid]}])
        obs = db.read_samples(['1'])
        exp = {'1': {'is_blank': False, 'barcode': None, 'notes': None,
                     'study_ids': [sid]}}
        self.assertDictEqual(obs, exp)
        sql = """SELECT barcode FROM barcodes.barcode LIMIT 1"""
        barcode = db._con.execute_fetchone(sql)[0]
        sid2 = db.create_study(title='study2')
        db.edit_samples([{'id': '1', 'is_blank': True, 'barcode': barcode,
                          'notes': 'Hi!', 'study_ids': [sid2]}])
        obs = db.read_samples(['1'])
        exp = {'1': {'is_blank': True, 'barcode': barcode, 'notes': 'Hi!',
                     'study_ids': [sid2]}}
        self.assertDictEqual(obs, exp)
        # Attempt to assign an invalid barcode to a sample
        with self.assertRaises(ValueError) as context:
            db.edit_samples([{'id': '1', 'barcode': 'whatever'}])
        err = 'Barcode(s) whatever do not exist.'
        self.assertEqual(str(context.exception), err)
        # Attempt to associate a sample with an invalid study ID
        db.delete_study(sid)
        with self.assertRaises(ValueError) as context:
            db.edit_samples([{'id': '1', 'study_ids': [sid]}])
        err = 'Study ID(s) %s do not exist.' % sid
        self.assertEqual(str(context.exception), err)
        # Attempt to edit a non-existing sample
        db.delete_samples(['1'])
        db.delete_study(sid2)
        with self.assertRaises(ValueError) as context:
            db.edit_samples([{'id': '1', 'is_blank': True}])
        err = 'Sample ID(s) 1 do not exist.'
        self.assertEqual(str(context.exception), err)

    def test_read_samples(self):
        # Read properties and associated study IDs of three samples
        sids = [db.create_study(title='study%s' % x) for x in range(3)]
        sql = """SELECT barcode FROM barcodes.barcode LIMIT 1"""
        barcode = db._con.execute_fetchone(sql)[0]
        samples = [{'id': '1', 'barcode': barcode, 'notes': 'Hi!',
                    'study_ids': [sids[0]]},
                   {'id': '2', 'is_blank': True,
                    'study_ids': [sids[0]]},
                   {'id': '3', 'barcode': barcode, 'notes': 'Hey!',
                    'study_ids': [sids[1], sids[2]]}]
        db.create_samples(samples)
        obs = db.read_samples(['1', '2', '3', '4'])
        exp = {'1': {'is_blank': False, 'barcode': barcode, 'notes': 'Hi!',
                     'study_ids': [sids[0]]},
               '2': {'is_blank': True, 'barcode': None, 'notes': None,
                     'study_ids': [sids[0]]},
               '3': {'is_blank': False, 'barcode': barcode, 'notes': 'Hey!',
                     'study_ids': sorted([sids[1], sids[2]])}}
        self.assertDictEqual(obs, exp)
        db.delete_samples(['1', '2', '3'])
        for sid in sids:
            db.delete_study(sid)

    def test_delete_samples(self):
        # Delete two samples
        sid = db.create_study(title='study')
        samples = [{'id': x, 'study_ids': [sid]} for x in ('1', '2', '3')]
        db.create_samples(samples)
        db._samples_exist(['1', '2', '3'], exist=True)
        db.delete_samples(['1', '2'])
        obs = db.read_samples(['1', '2'])
        self.assertDictEqual(obs, {})
        # Attempt to delete two samples, one of which does not exist
        with self.assertRaises(ValueError) as context:
            db.delete_samples(['1', '3'])
            err = 'Sample ID(s) 1 do not exist.'
            self.assertEqual(str(context.exception), err)
        # Attempt to delete a sample that is associated with a sample plate
        sql = """SELECT plate_type_id FROM pm.plate_type LIMIT 1"""
        ptid = db._con.execute_fetchone(sql)[0]
        spid = db.create_sample_plate('test_plate', ptid)
        splayout = [{'sample_id': '3', 'col': 1, 'row': 1}]
        db.write_sample_plate_layout(spid, splayout)
        with self.assertRaises(ValueError) as context:
            db.delete_samples(['3'])
        err = ('Sample ID(s) 3 cannot be deleted because they are associated '
               'with sample plate(s) %s.' % spid)
        self.assertEqual(str(context.exception), err)
        db.delete_sample_plate(spid)
        db.delete_samples(['3'])
        db.delete_study(sid)

    def test_get_samples_by_study(self):
        # Retrieve samples associated with studies
        sids = [db.create_study(title='study%s' % x) for x in range(3)]
        samples = [{'id': '1', 'study_ids': [sids[0]]},
                   {'id': '2', 'study_ids': [sids[0], sids[1]]},
                   {'id': '3', 'study_ids': [sids[1], sids[2]]}]
        db.create_samples(samples)
        obs = db.get_samples_by_study(sids[0])
        exp = {'1': False, '2': True}
        self.assertDictEqual(obs, exp)
        obs = db.get_samples_by_study(sids[1])
        exp = {'2': True, '3': True}
        self.assertDictEqual(obs, exp)
        obs = db.get_samples_by_study(sids[2])
        exp = {'3': True}
        self.assertDictEqual(obs, exp)
        # Read an empty study
        db.delete_samples(['3'])
        obs = db.get_samples_by_study(sids[2])
        self.assertDictEqual(obs, {})
        # Attempt to read a non-existing study
        db.delete_samples(['1', '2'])
        for sid in sids:
            db.delete_study(sid)
        with self.assertRaises(ValueError) as context:
            db.get_samples_by_study(sids[0])
        err = 'Study ID %s does not exist.' % sids[0]
        self.assertEqual(str(context.exception), err)

    def test_create_sample_plate(self):
        # Create a sample plate
        sql = """SELECT plate_type_id FROM pm.plate_type LIMIT 1"""
        ptid = db._con.execute_fetchone(sql)[0]
        sql = """SELECT email FROM ag.labadmin_users LIMIT 1"""
        email = db._con.execute_fetchone(sql)[0]
        created_on = datetime.datetime.combine(datetime.date.today(),
                                               datetime.time.min)
        spinfo = {'name': 'test_plate',
                  'plate_type_id': ptid,
                  'email': email,
                  'created_on': created_on,
                  'notes': 'Hi!'}
        spid = db.create_sample_plate(**spinfo)
        self.assertGreater(spid, 0)
        obs = db.read_sample_plate(spid)
        self.assertDictEqual(obs, spinfo)
        # Create a sample plate with the default plate type
        spid2 = db.create_sample_plate('test_plate_2', ptid)
        self.assertGreater(spid2, 0)
        obs = db.read_sample_plate(spid2)
        exp = {'name': 'test_plate_2',
               'plate_type_id': ptid,
               'email': None,
               'created_on': None,
               'notes': None}
        self.assertDictEqual(obs, exp)
        db.delete_sample_plate(spid2)
        # Attempt to create a sample plate with a duplicate name
        with self.assertRaises(ValueError) as context:
            db.create_sample_plate('test_plate', ptid)
        err = ('Name \'test_plate\' conflicts with exisiting sample plate %s.'
               % spid)
        self.assertEqual(str(context.exception), err)
        # Attempt to create a sample plate with an invalid email
        with self.assertRaises(ValueError) as context:
            db.create_sample_plate('test_plate_2', ptid, email='not-an-email')
        err = 'Email not-an-email does not exist.'
        self.assertEqual(str(context.exception), err)
        # Attempt to create a sample plate with an invalid plate type
        with self.assertRaises(ValueError) as context:
            db.create_sample_plate('test_plate_2', 12345)
        err = 'Plate type ID 12345 does not exist.'
        self.assertEqual(str(context.exception), err)
        db.delete_sample_plate(spid)

    def test_edit_sample_plate(self):
        # Assign properties to a sample plate
        sql = """SELECT plate_type_id FROM pm.plate_type LIMIT 1"""
        ptid = db._con.execute_fetchone(sql)[0]
        spid = db.create_sample_plate('test_plate', ptid)
        obs = db.read_sample_plate(spid)
        exp = {'name': 'test_plate',
               'plate_type_id': ptid,
               'email': None,
               'created_on': None,
               'notes': None}
        self.assertDictEqual(obs, exp)
        sql = """SELECT email FROM ag.labadmin_users LIMIT 1"""
        email = db._con.execute_fetchone(sql)[0]
        created_on = datetime.datetime(2016, 8, 15, 0, 0)
        spinfo = {'name': 'test_plate',
                  'plate_type_id': ptid,
                  'email': email,
                  'created_on': created_on,
                  'notes': 'Hi!'}
        db.edit_sample_plate(spid, **spinfo)
        obs = db.read_sample_plate(spid)
        self.assertDictEqual(obs, spinfo)
        # Attempt to assign a duplicate name to a sample plate
        spid2 = db.create_sample_plate('test_plate_2', ptid)
        with self.assertRaises(ValueError) as context:
            db.edit_sample_plate(spid, 'test_plate_2', ptid)
        err = ('Name \'test_plate_2\' conflicts with exisiting sample plate %s'
               '.' % spid2)
        self.assertEqual(str(context.exception), err)
        db.delete_sample_plate(spid2)
        # Attempt to assign an invalid email to a sample plate
        with self.assertRaises(ValueError) as context:
            db.edit_sample_plate(spid, 'test_plate', ptid,
                                 email='not-an-email')
        err = 'Email not-an-email does not exist.'
        self.assertEqual(str(context.exception), err)
        # Attempt to edit a sample plate that does not exist
        db.delete_sample_plate(spid)
        with self.assertRaises(ValueError) as context:
            db.edit_sample_plate(spid, **spinfo)
        err = 'Sample plate ID %s does not exist.' % spid
        self.assertEqual(str(context.exception), err)

    def test_read_sample_plate(self):
        # Read properties of a sample plate
        sql = """SELECT plate_type_id FROM pm.plate_type LIMIT 1"""
        ptid = db._con.execute_fetchone(sql)[0]
        sql = """SELECT email FROM ag.labadmin_users LIMIT 1"""
        email = db._con.execute_fetchone(sql)[0]
        created_on = datetime.datetime(2016, 8, 15, 0, 0)
        spinfo = {'name': 'test_plate',
                  'plate_type_id': ptid,
                  'email': email,
                  'created_on': created_on,
                  'notes': 'Hi!'}
        spid = db.create_sample_plate(**spinfo)
        obs = db.read_sample_plate(spid)
        self.assertDictEqual(obs, spinfo)
        # Attempt to read a sample plate that does not exist
        db.delete_sample_plate(spid)
        with self.assertRaises(ValueError) as context:
            db.read_sample_plate(spid)
        err = 'Sample plate ID %s does not exist.' % spid
        self.assertEqual(str(context.exception), err)

    def test_write_sample_plate_layout(self):
        # Populate a sample plate with two samples
        sid = db.create_study(title='study')
        samples = [{'id': x, 'study_ids': [sid]} for x in ('1', '2', '3')]
        db.create_samples(samples)
        sql = """SELECT plate_type_id FROM pm.plate_type LIMIT 1"""
        ptid = db._con.execute_fetchone(sql)[0]
        spid = db.create_sample_plate('test_plate', ptid)
        splayout = [
            {'sample_id': '1', 'col': 1, 'row': 1},
            {'sample_id': '2', 'col': 1, 'row': 2, 'name': 'B'}
        ]
        db.write_sample_plate_layout(spid, splayout)
        obs = db.read_sample_plate_layout(spid)
        exp = [
            {'sample_id': '1', 'col': 1, 'row': 1, 'name': None,
             'notes': None},
            {'sample_id': '2', 'col': 1, 'row': 2, 'name': 'B',
             'notes': None}
        ]
        self.assertListEqual(obs, exp)
        # Clear the exisiting layout and add one sample
        splayout = [{'sample_id': '3', 'col': 1, 'row': 3, 'notes': 'Hi!'}]
        db.write_sample_plate_layout(spid, splayout)
        obs = db.read_sample_plate_layout(spid)
        exp = [{'sample_id': '3', 'col': 1, 'row': 3, 'name': None,
                'notes': 'Hi!'}]
        self.assertListEqual(obs, exp)
        # Attempt to populate a sample plate with a non-existing sample
        splayout = [{'sample_id': '4', 'col': 2, 'row': 1}]
        with self.assertRaises(ValueError) as context:
            db.write_sample_plate_layout(spid, splayout)
        err = 'Sample ID 4 does not exist.'
        self.assertEqual(str(context.exception), err)
        # Attempt to populate a sample plate that does not exist
        db.delete_sample_plate(spid)
        with self.assertRaises(ValueError) as context:
            db.write_sample_plate_layout(spid, splayout)
        err = 'Sample plate ID %s does not exist.' % spid
        self.assertEqual(str(context.exception), err)
        db.delete_samples([x['id'] for x in samples])
        db.delete_study(sid)

    def test_read_sample_plate_layout(self):
        # Read a sample plate's layout containing three sample
        sid = db.create_study(title='study')
        samples = [{'id': x, 'study_ids': [sid]} for x in ('1', '2', '3')]
        db.create_samples(samples)
        sql = """SELECT plate_type_id FROM pm.plate_type LIMIT 1"""
        ptid = db._con.execute_fetchone(sql)[0]
        spid = db.create_sample_plate('test_plate', ptid)
        splayout = [
            {'sample_id': '1', 'col': 1, 'row': 1},
            {'sample_id': '2', 'col': 1, 'row': 2, 'name': 'B'},
            {'sample_id': '3', 'col': 1, 'row': 3, 'notes': 'Hi!'}
        ]
        db.write_sample_plate_layout(spid, splayout)
        obs = db.read_sample_plate_layout(spid)
        exp = [
            {'sample_id': '1', 'col': 1, 'row': 1, 'name': None,
             'notes': None},
            {'sample_id': '2', 'col': 1, 'row': 2, 'name': 'B',
             'notes': None},
            {'sample_id': '3', 'col': 1, 'row': 3, 'name': None,
             'notes': 'Hi!'}
        ]
        self.assertListEqual(obs, exp)
        # Read a sample plate's layout that is clear
        db._clear_sample_plate_layout(spid)
        obs = db.read_sample_plate_layout(spid)
        self.assertListEqual(obs, [])
        # Attempt to read layout of a non-existing sample plate
        db.delete_sample_plate(spid)
        with self.assertRaises(ValueError) as context:
            db.write_sample_plate_layout(spid, splayout)
        err = 'Sample plate ID %s does not exist.' % spid
        self.assertEqual(str(context.exception), err)
        db.delete_samples([x['id'] for x in samples])
        db.delete_study(sid)

    def test_delete_sample_plate(self):
        # Delete a sample plate and its layout
        sql = """SELECT plate_type_id FROM pm.plate_type LIMIT 1"""
        ptid = db._con.execute_fetchone(sql)[0]
        spid = db.create_sample_plate('test_plate', ptid)
        obs = db.read_sample_plate(spid)
        self.assertIsNotNone(obs)
        sid = db.create_study(title='study')
        db.create_samples([{'id': '1', 'study_ids': [sid]}])
        splayout = [{'sample_id': '1', 'col': 1, 'row': 1}]
        db.write_sample_plate_layout(spid, splayout)
        obs = db.read_sample_plate_layout(spid)
        self.assertTrue(obs)
        db.delete_sample_plate(spid)
        with self.assertRaises(ValueError) as context:
            db.read_sample_plate(spid)
        err = 'Sample plate ID %s does not exist.' % spid
        self.assertEqual(str(context.exception), err)
        obs = db._sample_plate_layout_exists(spid)
        self.assertFalse(obs)
        db.delete_samples(['1'])
        db.delete_study(sid)
        # Attempt to delete a sample plate that does not exist
        with self.assertRaises(ValueError) as context:
            db.delete_sample_plate(spid)
        err = 'Sample plate ID %s does not exist.' % spid
        self.assertEqual(str(context.exception), err)

    def test_get_property_options(self):
        # Get available extraction robots
        obs = db.get_property_options("extraction_robot")
        exp = [{'id': 1, 'name': 'HOWE_KF1', 'notes': None},
               {'id': 2, 'name': 'HOWE_KF2', 'notes': None},
               {'id': 3, 'name': 'HOWE_KF3', 'notes': None},
               {'id': 4, 'name': 'HOWE_KF4', 'notes': None}]
        self.assertListEqual(obs, exp)

    def test_get_plate_types(self):
        # Get available plate types
        obs = db.get_plate_types()
        exp = [{'id': 1, 'name': '96-well', 'notes': 'Standard 96-well plate',
                'cols': 12, 'rows': 8}]
        self.assertListEqual(obs, exp)

    def test_get_emails(self):
        # Get available emails
        obs = db.get_emails()
        exp = ['test']
        self.assertListEqual(obs, exp)

    def test_get_sample_plate_ids(self):
        sql = """SELECT plate_type_id FROM pm.plate_type LIMIT 1"""
        ptid = db._con.execute_fetchone(sql)[0]
        spid = db.create_sample_plate('test_plate', ptid)
        obs = db.get_sample_plate_ids()[-1]
        self.assertEqual(obs, spid)
        db.delete_sample_plate(spid)

    def test_get_sample_plate_list(self):
        # Create a sample plate
        sql = """SELECT plate_type_id FROM pm.plate_type LIMIT 1"""
        ptid = db._con.execute_fetchone(sql)[0]
        sql = """SELECT email FROM ag.labadmin_users LIMIT 1"""
        email = db._con.execute_fetchone(sql)[0]
        created_on = datetime.datetime.combine(datetime.date.today(),
                                               datetime.time.min)
        spinfo = {'name': 'test_plate',
                  'plate_type_id': ptid,
                  'email': email,
                  'created_on': created_on,
                  'notes': 'A test plate'}
        spid = db.create_sample_plate(**spinfo)
        sid = db.create_study(title='test_study')
        samples = [{'id': x, 'study_ids': [sid]} for x in ('1', '2', '3')]
        db.create_samples(samples)
        splayout = [{'sample_id': str(x), 'col': 1, 'row': x}
                    for x in (1, 2, 3)]
        db.write_sample_plate_layout(spid, splayout)
        obs = db.get_sample_plate_list()[-1]
        exp = {'id': spid,
               'name': 'test_plate',
               'type': ['96-well', 96],
               'person': email,
               'date': created_on.strftime('%m/%d/%Y'),
               'fill': [3, 0.031],
               'study': [1, sid, None, 'test_study']}
        self.assertDictEqual(obs, exp)
        db.delete_sample_plate(spid)
        db.delete_samples(['1', '2', '3'])
        db.delete_study(sid)


if __name__ == "__main__":
    main()

from unittest import TestCase, main
from os.path import join, dirname, realpath
from six import StringIO
from functools import partial
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

        self._clean_up_funcs = []

    def tearDown(self):
        db._clear_table('external_survey_answers', 'ag')
        db._revert_ready(['000023299'])
        for f in self._clean_up_funcs:
            try:
                f()
            except Exception as e:
                print("Database clean-up failed. Downstream tests might be "
                      "affected by this! Reason: %s" % e.message)

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
        survey_df[survey_df.BMI != 'Unspecified'] .BMI.astype(float)

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
        # we don't know the actual number independent of DB version, but we can
        # assume that we have a certain amount of those barcodes.
        self.assertTrue(len(obs) >= 100)

        # we cannot know which barcodes are unconsented without executing the
        # db function itself. Thus, for unit tests, we should only check data
        # types.
        self.assertTrue(obs[0][0].isdigit())
        self.assertTrue(isinstance(obs[0][1], datetime.date))
        self.assertTrue(isinstance(obs[0][2], str))

    def test_search_kits(self):
        # obtain current test data from DB
        ag_login_id = 'd8592c74-7cf9-2135-e040-8a80115d6401'
        kits = db.get_kit_info_by_login(ag_login_id)

        # check if ag_login_id is regain with supplied_kit_id
        obs = db.search_kits(kits[0]['supplied_kit_id'])
        self.assertEqual([ag_login_id], obs)

        # check if kit_id is found by search
        obs = db.search_kits('e1934dfe-8537-6dce-e040-8a80115d2da9')
        self.assertEqual(['e1934ceb-6e92-c36a-e040-8a80115d2d64'], obs)

        # check that a non existing kit is not found
        obs = db.search_kits('990001124')
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
        # don't compare name, since it is scrubbed to random chars
        self.assertEqual(obs['mail']['recipients'][0],
                         'americangut@gmail.com')

        obs = db.get_ag_barcode_details(['000001072', '000023299'])
        self.assertEqual(obs['000023299']['results_ready'], 'Y')
        self.assertEqual(obs['000001072']['results_ready'], 'Y')

    def test_get_access_levels_user(self):
        # insert a fresh new user into DB.
        email = 'testmail@testdomain.com'
        password = ('$2a$10$2.6Y9HmBqUFmSvKCjWmBte70'
                    'WF.zd3h4VqbhLMQK1xP67Aj3rei86')
        sql = """INSERT INTO ag.labadmin_users (email, password)
                 VALUES (%s, %s)"""
        db._con.execute(sql, [email, password])

        obs = db.get_access_levels_user(email)
        self.assertItemsEqual(obs, [])

        db.alter_access_levels(email, [1, 6])
        obs = db.get_access_levels_user(email)
        self.assertItemsEqual(obs, [[1, 'Barcodes'], [6, 'Search']])

        db.alter_access_levels(email, [])
        obs = db.get_access_levels_user(email)
        self.assertItemsEqual(obs, [])

        # Remove test user from DB.
        sql = """DELETE FROM ag.labadmin_users WHERE email=%s"""
        db._con.execute(sql, [email])

    def test_get_users(self):
        obs = db.get_users()
        exp = 'test'
        self.assertIn(exp, obs)

    def test_get_access_levels(self):
        obs = db.get_access_levels()
        exp = [[1, 'Barcodes'], [2, 'AG kits'], [3, 'Scan Barcodes'],
               [4, 'External surveys'], [5, 'Metadata Pulldown'],
               [6, 'Search'], [7, 'Admin']]
        self.assertEqual(obs, exp)

    def test_participant_names(self):
        obs = db.participant_names()
        self.assertTrue(len(obs) >= 8237)
        self.assertIn('000027561', map(lambda x: x[0], obs))

    def test_search_barcodes(self):
        obs = db.search_barcodes('000001124')
        self.assertEqual(obs, ['d8592c74-7c27-2135-e040-8a80115d6401'])

        ag_login_id = "d8592c74-9491-2135-e040-8a80115d6401"
        names = db.ut_get_participant_names_from_ag_login_id(ag_login_id)

        obs = []
        for name in names:
            obs.extend(db.search_barcodes(name))
        self.assertTrue(ag_login_id in obs)

    def test_getAGBarcodeDetails(self):
        obs = db.getAGBarcodeDetails('000018046')
        exp = {'status': 'Received',
               'ag_kit_id': '0060a301-e5c0-6a4e-e050-8a800c5d49b7',
               'barcode': '000018046',
               'environment_sampled': None,
               # 'name': 'REMOVED',
               'ag_kit_barcode_id': '0060a301-e5c1-6a4e-e050-8a800c5d49b7',
               'sample_time': datetime.time(11, 15),
               # 'notes': 'REMOVED',
               'overloaded': 'N',
               'withdrawn': None,  # 'email': 'REMOVED',
               'other': 'N',
               # 'deposited': False,
               # 'participant_name': 'REMOVED-0',
               'refunded': None, 'moldy': 'N',
               'sample_date': datetime.date(2014, 8, 13),
               'date_of_last_email': datetime.date(2014, 8, 15),
               # 'other_text': 'REMOVED',
               'site_sampled': 'Stool'}
        # only look at those fields, that are not subject to scrubbing
        self.assertEqual({k: obs[k] for k in exp}, exp)

    def test_get_barcode_info_by_kit_id(self):
        obs = db.get_barcode_info_by_kit_id(
            '0060a301-e5c0-6a4e-e050-8a800c5d49b7')[0]
        exp = {'ag_kit_id': '0060a301-e5c0-6a4e-e050-8a800c5d49b7',
               'environment_sampled': None,
               'sample_time': datetime.time(11, 15),
               # 'notes': 'REMOVED',
               'barcode': '000018046',
               'results_ready': 'Y',
               'refunded': None,
               # 'participant_name': 'REMOVED-0',
               'ag_kit_barcode_id': '0060a301-e5c1-6a4e-e050-8a800c5d49b7',
               'sample_date': datetime.date(2014, 8, 13),
               'withdrawn': None,
               'site_sampled': 'Stool'}
        # only look at those fields, that are not subject to scrubbing
        self.assertEqual({k: obs[k] for k in exp}, exp)

    def test_getHumanParticipants(self):
        i = "d8592c74-9694-2135-e040-8a80115d6401"
        res = db.getHumanParticipants(i)
        # we can't compare to scrubbed participant names, thus we only check
        # number of names.
        self.assertTrue(len(res) >= 4)

    def test_getHumanParticipantsNotPresent(self):
        i = '00000000-0000-0000-0000-000000000000'
        res = db.getHumanParticipants(i)
        self.assertEqual(res, [])

    def test_getAnimalParticipants(self):
        i = "ed5ab96f-fe3b-ead5-e040-8a80115d1c4b"
        res = db.getAnimalParticipants(i)
        # we can't compare to scrubbed participant names, thus we only check
        # number of names.
        self.assertTrue(len(res) == 1)

    def test_getAnimalParticipantsNotPresent(self):
        i = "00711b0a-67d6-0fed-e050-8a800c5d7570"
        res = db.getAnimalParticipants(i)
        self.assertEqual(res, [])

    def test_get_ag_barcode_details(self):
        obs = db.get_ag_barcode_details(['000018046'])
        ag_login_id = '0060a301-e5bf-6a4e-e050-8a800c5d49b7'
        exp = {'000018046': {
                'ag_kit_barcode_id': '0060a301-e5c1-6a4e-e050-8a800c5d49b7',
                'verification_email_sent': 'n',
                'pass_reset_code': None,
                'vioscreen_status': 3,
                'sample_barcode_file': '000018046.jpg',
                'environment_sampled': None,
                'supplied_kit_id': db.ut_get_supplied_kit_id(ag_login_id),
                'withdrawn': None,
                'kit_verified': 'y',
                # 'city': 'REMOVED',
                'ag_kit_id': '0060a301-e5c0-6a4e-e050-8a800c5d49b7',
                # 'zip': 'REMOVED',
                'ag_login_id': ag_login_id,
                # 'state': 'REMOVED',
                'results_ready': 'Y',
                'moldy': 'N',
                # The key 'registered_on' is a time stamp when the database is
                # created. It is unique per deployment.
                # 'registered_on': datetime.datetime(2016, 8, 17, 10, 47, 2,
                #                                   713292),
                # 'kit_password': ('$2a$10$2.6Y9HmBqUFmSvKCjWmBte70WF.zd3h4Vqb'
                #                  'hLMQK1xP67Aj3rei86'),
                # 'deposited': False,
                'sample_date': datetime.date(2014, 8, 13),
                # 'email': 'REMOVED',
                'print_results': False,
                'open_humans_token': None,
                # 'elevation': 0.0,
                'refunded': None,
                # 'other_text': 'REMOVED',
                'barcode': '000018046',
                'swabs_per_kit': 1L,
                # 'kit_verification_code': '60260',
                # 'latitude': 0.0,
                'cannot_geocode': None,
                # 'address': 'REMOVED',
                'date_of_last_email': datetime.date(2014, 8, 15),
                'site_sampled': 'Stool',
                # 'name': 'REMOVED',
                'sample_time': datetime.time(11, 15),
                # 'notes': 'REMOVED',
                'overloaded': 'N',
                # 'longitude': 0.0,
                'pass_reset_time': None,
                # 'country': 'REMOVED',
                'survey_id': '084532330aca5885',
                'other': 'N',
                'sample_barcode_file_md5': None
        }}
        participant_names = db.ut_get_participant_names_from_ag_login_id(
            ag_login_id)
        for key in obs:
            del(obs[key]['registered_on'])
            # only look at those fields, that are not subject to scrubbing
            self.assertEqual({k: obs[key][k] for k in exp[key]}, exp[key])
            self.assertIn(obs[key]['participant_name'], participant_names)

    # - PlateMapper functions tests - #
    def test_get_studies(self):
        obs = db.get_studies()
        self.assertEqual(obs, [])

        db.create_study(9999, 'LabAdmin test project', 'LTP', 'KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))

        # Cast the DictCursor list to a dict list so assertEqual works
        obs = map(dict, db.get_studies())
        exp = [{'study_id': 9999, 'title': 'LabAdmin test project',
               'alias': 'LTP', 'jira_key': 'KL9999'}]
        self.assertEqual(obs, exp)

        db.create_study(9998, 'Understanding the Cannabis Microbiome',
                        'Cannabis Soils', 'KL9999998')
        self._clean_up_funcs.append(partial(db.delete_study, 9998))

        obs = map(dict, db.get_studies())
        exp = [{'study_id': 9998,
                'title': 'Understanding the Cannabis Microbiome',
                'alias': 'Cannabis Soils', 'jira_key': 'KL9999998'},
               {'study_id': 9999, 'title': 'LabAdmin test project',
                'alias': 'LTP', 'jira_key': 'KL9999'}]
        self.assertEqual(obs, exp)

    def test_study_exists(self):
        with self.assertRaises(ValueError) as ctx:
            db._study_exists(9999)
        self.assertEqual(ctx.exception.message,
                         "Study ID 9999 does not exist.")

        db.create_study(9999, 'LabAdmin test project', 'LTP', 'KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))
        db._study_exists(9999)

    def test_study_is_unique(self):
        db._study_is_unique(9999, 'LabAdmin test project')

        db.create_study(9999, 'LabAdmin test project', 'LTP', 'KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))

        db._study_is_unique(10318, 'Fake LabAdmin test project')
        db._study_is_unique(9999, 'LabAdmin test project', skip_id=9999)
        with self.assertRaises(ValueError) as ctx:
            db._study_is_unique(9999, 'LabAdmin test project')
        self.assertEqual(
            ctx.exception.message,
            "Study (9999, LabAdmin test project) conflicts with studies 9999")

        db._study_is_unique(9999, 'Fake LabAdmin test project', skip_id=9999)
        with self.assertRaises(ValueError) as ctx:
            db._study_is_unique(9999, 'Fake LabAdmin test project')
        self.assertEqual(
            ctx.exception.message,
            "Study (9999, Fake LabAdmin test project) conflicts "
            "with studies 9999")

        with self.assertRaises(ValueError) as ctx:
            db._study_is_unique(10318, 'LabAdmin test project')
        self.assertEqual(
            ctx.exception.message,
            "Study (10318, LabAdmin test project) conflicts with studies 9999")

    def test_create_study(self):
        # Test success
        db.create_study(9999, 'LabAdmin test project', 'LTP', 'KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))
        obs = db.read_study(9999)
        exp = {'study_id': 9999, 'title': 'LabAdmin test project',
               'alias': 'LTP', 'jira_key': 'KL9999'}
        self.assertEqual(obs, exp)

        # Test failures
        with self.assertRaises(ValueError) as ctx:
            db.create_study(9999, 'LabAdmin test project 2', 'LTP', 'KL9999')
        self.assertEqual(
            ctx.exception.message,
            "Study (9999, LabAdmin test project 2) conflicts with "
            "studies 9999")

    def test_edit_study(self):
        # Test success
        db.create_study(9999, 'LabAdmin test project', 'LTP', 'KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))
        obs = db.read_study(9999)
        exp = {'study_id': 9999, 'title': 'LabAdmin test project',
               'alias': 'LTP', 'jira_key': 'KL9999'}
        self.assertEqual(obs, exp)
        db.edit_study(9999, title='Test study 2', alias='the study')
        obs = db.read_study(9999)
        exp = {'study_id': 9999, 'title': 'Test study 2',
               'alias': 'the study', 'jira_key': 'KL9999'}
        self.assertEqual(obs, exp)

        # Test success changing only one of the values
        db.edit_study(9999, title='LabAdmin test project')
        obs = db.read_study(9999)
        exp = {'study_id': 9999, 'title': 'LabAdmin test project',
               'alias': 'the study', 'jira_key': 'KL9999'}
        self.assertEqual(obs, exp)

        db.edit_study(9999, alias='LTP')
        obs = db.read_study(9999)
        exp = {'study_id': 9999, 'title': 'LabAdmin test project',
               'alias': 'LTP', 'jira_key': 'KL9999'}
        self.assertEqual(obs, exp)

        # Test error no parameters
        with self.assertRaises(ValueError) as ctx:
            db.edit_study(9999)
        self.assertEqual(ctx.exception.message,
                         "At least one of title or alias should be provided")

        # Test error duplicated title
        db.create_study(9998, 'LabAdmin Test Project 2', 'LTP2', 'KL29998')
        self._clean_up_funcs.append(partial(db.delete_study, 9998))
        with self.assertRaises(ValueError) as ctx:
            db.edit_study(9998, title='LabAdmin test project')
        self.assertEqual(ctx.exception.message,
                         "Study (9998, LabAdmin test project) conflicts with "
                         "studies 9999")

        # Test error study does not exist
        with self.assertRaises(ValueError) as ctx:
            db.edit_study(0, title='LTP')
        self.assertEqual(ctx.exception.message, "Study ID 0 does not exist.")

    def test_read_study(self):
        # Read properties of a study
        db.create_study(9999, title='LabAdmin test project',
                        alias='LTP', jira_key='KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))
        obs = db.read_study(9999)
        exp = {'study_id': 9999, 'title': 'LabAdmin test project',
               'alias': 'LTP', 'jira_key': 'KL9999'}
        self.assertEqual(obs, exp)

        # Attempt to read properties of a non-existing study
        with self.assertRaises(ValueError) as ctx:
            db.read_study(0)
        self.assertEqual(ctx.exception.message,
                         'Study ID 0 does not exist.')

    def test_delete_study(self):
        # Delete a study without samples
        db.create_study(9999, title='LabAdmin test project',
                        alias='LTP', jira_key='KL9999')
        self.assertIsNotNone(db.read_study(9999))
        db.delete_study(9999)
        with self.assertRaises(ValueError):
            db._study_exists(9999)

        # Delete a study with three samples associated
        db.create_study(9999, title='LabAdmin test project',
                        alias='LTP', jira_key='KL9999')

        samples = [{'id': '1', 'study_ids': [9999]},
                   {'id': '2', 'study_ids': [9999]},
                   {'id': '3', 'study_ids': [9999]}]
        db.create_samples(samples)
        obs = db.read_samples(['1', '2', '3'])
        exp = {'1': {'is_blank': False, 'barcode': None, 'notes': None,
                     'study_ids': [9999]},
               '2': {'is_blank': False, 'barcode': None, 'notes': None,
                     'study_ids': [9999]},
               '3': {'is_blank': False, 'barcode': None, 'notes': None,
                     'study_ids': [9999]}}
        self.assertEqual(obs, exp)
        db.delete_study(9999)
        with self.assertRaises(ValueError):
            db.read_study(9999)
        obs = db.read_samples(['1', '2', '3'])
        exp = {}
        self.assertDictEqual(obs, exp)

        # Attempt to delete a non-existing study
        with self.assertRaises(ValueError) as ctx:
            db.delete_study(9999)
        self.assertEqual(ctx.exception.message,
                         'Study ID 9999 does not exist.')

    def test_create_samples(self):
        # Create three samples with sample IDs only
        db.create_study(9999, title='LabAdmin test project',
                        alias='LTP', jira_key='KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))
        samples = [{'id': x, 'study_ids': [9999]} for x in ('1', '2', '3')]
        db.create_samples(samples)
        obs = db.read_samples(['1', '2', '3'])
        exp = {x: {'is_blank': False, 'barcode': None, 'notes': None,
                   'study_ids': [9999]} for x in ('1', '2', '3')}
        self.assertDictEqual(obs, exp)

        # Create a sample with barcode, without is_blank, and associated with
        # two studies
        db.create_study(9998, title='LabAdmin test project 2',
                        alias='LTP', jira_key='KL9998')
        self._clean_up_funcs.append(partial(db.delete_study, 9998))
        sql = """SELECT barcode FROM barcodes.barcode LIMIT 1"""
        barcode = db._con.execute_fetchone(sql)[0]
        samples = [{'id': '4', 'barcode': barcode, 'notes': 'Hi!',
                    'study_ids': [9999, 9998]}]
        db.create_samples(samples)
        obs = db.read_samples(['4'])
        exp = {'4': {'is_blank': False, 'barcode': barcode, 'notes': 'Hi!',
               'study_ids': [9998, 9999]}}
        self.assertDictEqual(obs, exp)
        # Attempt to create a sample with an invalid barcode
        samples = [{'id': '5', 'barcode': 'whatever', 'study_ids': [9999]}]
        with self.assertRaises(ValueError) as context:
            db.create_samples(samples)
        err = 'Barcode(s) whatever do not exist.'
        self.assertEqual(str(context.exception), err)
        # Attempt to create two samples, one with duplicate ID
        samples = [{'id': x, 'study_ids': [9999]} for x in ('5', '1')]
        with self.assertRaises(ValueError) as context:
            db.create_samples(samples)
        err = 'Sample ID(s) 1 already exist.'
        self.assertEqual(str(context.exception), err)
        # Test if one duplicate ID fails the creation of all samples
        obs = db.read_samples(['5'])
        self.assertDictEqual(obs, {})
        db.delete_samples(['1', '2', '3', '4'])

    # def test_edit_samples(self):
    #     # Assign properties to a sample and alter its associated study
    #     sid = db.create_study(title='study')
    #     db.create_samples([{'id': '1', 'study_ids': [sid]}])
    #     obs = db.read_samples(['1'])
    #     exp = {'1': {'is_blank': False, 'barcode': None, 'notes': None,
    #                  'study_ids': [sid]}}
    #     self.assertDictEqual(obs, exp)
    #     sql = """SELECT barcode FROM barcodes.barcode LIMIT 1"""
    #     barcode = db._con.execute_fetchone(sql)[0]
    #     sid2 = db.create_study(title='study2')
    #     db.edit_samples([{'id': '1', 'is_blank': True, 'barcode': barcode,
    #                       'notes': 'Hi!', 'study_ids': [sid2]}])
    #     obs = db.read_samples(['1'])
    #     exp = {'1': {'is_blank': True, 'barcode': barcode, 'notes': 'Hi!',
    #                  'study_ids': [sid2]}}
    #     self.assertDictEqual(obs, exp)
    #     # Attempt to assign an invalid barcode to a sample
    #     with self.assertRaises(ValueError) as context:
    #         db.edit_samples([{'id': '1', 'barcode': 'whatever'}])
    #     err = 'Barcode(s) whatever do not exist.'
    #     self.assertEqual(str(context.exception), err)
    #     # Attempt to associate a sample with an invalid study ID
    #     db.delete_study(sid)
    #     with self.assertRaises(ValueError) as context:
    #         db.edit_samples([{'id': '1', 'study_ids': [sid]}])
    #     err = 'Study ID(s) %s do not exist.' % sid
    #     self.assertEqual(str(context.exception), err)
    #     # Attempt to edit a non-existing sample
    #     db.delete_samples(['1'])
    #     db.delete_study(sid2)
    #     with self.assertRaises(ValueError) as context:
    #         db.edit_samples([{'id': '1', 'is_blank': True}])
    #     err = 'Sample ID(s) 1 do not exist.'
    #     self.assertEqual(str(context.exception), err)
    #
    # def test_read_samples(self):
    #     # Read properties and associated study IDs of three samples
    #     sids = [db.create_study(title='study%s' % x) for x in range(3)]
    #     sql = """SELECT barcode FROM barcodes.barcode LIMIT 1"""
    #     barcode = db._con.execute_fetchone(sql)[0]
    #     samples = [{'id': '1', 'barcode': barcode, 'notes': 'Hi!',
    #                 'study_ids': [sids[0]]},
    #                {'id': '2', 'is_blank': True,
    #                 'study_ids': [sids[0]]},
    #                {'id': '3', 'barcode': barcode, 'notes': 'Hey!',
    #                 'study_ids': [sids[1], sids[2]]}]
    #     db.create_samples(samples)
    #     obs = db.read_samples(['1', '2', '3', '4'])
    #     exp = {'1': {'is_blank': False, 'barcode': barcode, 'notes': 'Hi!',
    #                  'study_ids': [sids[0]]},
    #            '2': {'is_blank': True, 'barcode': None, 'notes': None,
    #                  'study_ids': [sids[0]]},
    #            '3': {'is_blank': False, 'barcode': barcode, 'notes': 'Hey!',
    #                  'study_ids': sorted([sids[1], sids[2]])}}
    #     self.assertDictEqual(obs, exp)
    #     db.delete_samples(['1', '2', '3'])
    #     for sid in sids:
    #         db.delete_study(sid)
    #
    # def test_delete_samples(self):
    #     # Delete two samples
    #     sid = db.create_study(title='study')
    #     samples = [{'id': x, 'study_ids': [sid]} for x in ('1', '2', '3')]
    #     db.create_samples(samples)
    #     db._samples_exist(['1', '2', '3'], exist=True)
    #     db.delete_samples(['1', '2'])
    #     obs = db.read_samples(['1', '2'])
    #     self.assertDictEqual(obs, {})
    #     # Attempt to delete two samples, one of which does not exist
    #     with self.assertRaises(ValueError) as context:
    #         db.delete_samples(['1', '3'])
    #         err = 'Sample ID(s) 1 do not exist.'
    #         self.assertEqual(str(context.exception), err)
    #     # Attempt to delete a sample that is associated with a sample plate
    #     sql = """SELECT plate_type_id FROM pm.plate_type LIMIT 1"""
    #     ptid = db._con.execute_fetchone(sql)[0]
    #     spid = db.create_sample_plate('test_plate', ptid)
    #     splayout = [{'sample_id': '3', 'col': 1, 'row': 1}]
    #     db.write_sample_plate_layout(spid, splayout)
    #     with self.assertRaises(ValueError) as context:
    #         db.delete_samples(['3'])
    #     err = ('Sample ID(s) 3 cannot be deleted because they are associated '
    #            'with sample plate(s) %s.' % spid)
    #     self.assertEqual(str(context.exception), err)
    #     db.delete_sample_plate(spid)
    #     db.delete_samples(['3'])
    #     db.delete_study(sid)
    #
    # def test_get_samples_by_study(self):
    #     # Retrieve samples associated with studies
    #     sids = [db.create_study(title='study%s' % x) for x in range(3)]
    #     samples = [{'id': '1', 'study_ids': [sids[0]]},
    #                {'id': '2', 'study_ids': [sids[0], sids[1]]},
    #                {'id': '3', 'study_ids': [sids[1], sids[2]]}]
    #     db.create_samples(samples)
    #     obs = db.get_samples_by_study(sids[0])
    #     exp = {'1': False, '2': True}
    #     self.assertDictEqual(obs, exp)
    #     obs = db.get_samples_by_study(sids[1])
    #     exp = {'2': True, '3': True}
    #     self.assertDictEqual(obs, exp)
    #     obs = db.get_samples_by_study(sids[2])
    #     exp = {'3': True}
    #     self.assertDictEqual(obs, exp)
    #     # Read an empty study
    #     db.delete_samples(['3'])
    #     obs = db.get_samples_by_study(sids[2])
    #     self.assertDictEqual(obs, {})
    #     # Attempt to read a non-existing study
    #     db.delete_samples(['1', '2'])
    #     for sid in sids:
    #         db.delete_study(sid)
    #     with self.assertRaises(ValueError) as context:
    #         db.get_samples_by_study(sids[0])
    #     err = 'Study ID %s does not exist.' % sids[0]
    #     self.assertEqual(str(context.exception), err)
    #
    # def test_create_sample_plate(self):
    #     # Create a sample plate
    #     sql = """SELECT plate_type_id FROM pm.plate_type LIMIT 1"""
    #     ptid = db._con.execute_fetchone(sql)[0]
    #     sql = """SELECT email FROM ag.labadmin_users LIMIT 1"""
    #     email = db._con.execute_fetchone(sql)[0]
    #     created_on = datetime.datetime.combine(datetime.date.today(),
    #                                            datetime.time.min)
    #     spinfo = {'name': 'test_plate',
    #               'plate_type_id': ptid,
    #               'email': email,
    #               'created_on': created_on,
    #               'notes': 'Hi!'}
    #     spid = db.create_sample_plate(**spinfo)
    #     self.assertGreater(spid, 0)
    #     obs = db.read_sample_plate(spid)
    #     self.assertDictEqual(obs, spinfo)
    #     # Create a sample plate with the default plate type
    #     spid2 = db.create_sample_plate('test_plate_2', ptid)
    #     self.assertGreater(spid2, 0)
    #     obs = db.read_sample_plate(spid2)
    #     exp = {'name': 'test_plate_2',
    #            'plate_type_id': ptid,
    #            'email': None,
    #            'created_on': None,
    #            'notes': None}
    #     self.assertDictEqual(obs, exp)
    #     db.delete_sample_plate(spid2)
    #     # Attempt to create a sample plate with a duplicate name
    #     with self.assertRaises(ValueError) as context:
    #         db.create_sample_plate('test_plate', ptid)
    #     err = ('Name \'test_plate\' conflicts with exisiting sample plate %s.'
    #            % spid)
    #     self.assertEqual(str(context.exception), err)
    #     # Attempt to create a sample plate with an invalid email
    #     with self.assertRaises(ValueError) as context:
    #         db.create_sample_plate('test_plate_2', ptid, email='not-an-email')
    #     err = 'Email not-an-email does not exist.'
    #     self.assertEqual(str(context.exception), err)
    #     # Attempt to create a sample plate with an invalid plate type
    #     with self.assertRaises(ValueError) as context:
    #         db.create_sample_plate('test_plate_2', 12345)
    #     err = 'Plate type ID 12345 does not exist.'
    #     self.assertEqual(str(context.exception), err)
    #     db.delete_sample_plate(spid)
    #
    # def test_edit_sample_plate(self):
    #     # Assign properties to a sample plate
    #     sql = """SELECT plate_type_id FROM pm.plate_type LIMIT 1"""
    #     ptid = db._con.execute_fetchone(sql)[0]
    #     spid = db.create_sample_plate('test_plate', ptid)
    #     obs = db.read_sample_plate(spid)
    #     exp = {'name': 'test_plate',
    #            'plate_type_id': ptid,
    #            'email': None,
    #            'created_on': None,
    #            'notes': None}
    #     self.assertDictEqual(obs, exp)
    #     sql = """SELECT email FROM ag.labadmin_users LIMIT 1"""
    #     email = db._con.execute_fetchone(sql)[0]
    #     created_on = datetime.datetime(2016, 8, 15, 0, 0)
    #     spinfo = {'name': 'test_plate',
    #               'plate_type_id': ptid,
    #               'email': email,
    #               'created_on': created_on,
    #               'notes': 'Hi!'}
    #     db.edit_sample_plate(spid, **spinfo)
    #     obs = db.read_sample_plate(spid)
    #     self.assertDictEqual(obs, spinfo)
    #     # Attempt to assign a duplicate name to a sample plate
    #     spid2 = db.create_sample_plate('test_plate_2', ptid)
    #     with self.assertRaises(ValueError) as context:
    #         db.edit_sample_plate(spid, 'test_plate_2', ptid)
    #     err = ('Name \'test_plate_2\' conflicts with exisiting sample plate %s'
    #            '.' % spid2)
    #     self.assertEqual(str(context.exception), err)
    #     db.delete_sample_plate(spid2)
    #     # Attempt to assign an invalid email to a sample plate
    #     with self.assertRaises(ValueError) as context:
    #         db.edit_sample_plate(spid, 'test_plate', ptid,
    #                              email='not-an-email')
    #     err = 'Email not-an-email does not exist.'
    #     self.assertEqual(str(context.exception), err)
    #     # Attempt to edit a sample plate that does not exist
    #     db.delete_sample_plate(spid)
    #     with self.assertRaises(ValueError) as context:
    #         db.edit_sample_plate(spid, **spinfo)
    #     err = 'Sample plate ID %s does not exist.' % spid
    #     self.assertEqual(str(context.exception), err)
    #
    # def test_read_sample_plate(self):
    #     # Read properties of a sample plate
    #     sql = """SELECT plate_type_id FROM pm.plate_type LIMIT 1"""
    #     ptid = db._con.execute_fetchone(sql)[0]
    #     sql = """SELECT email FROM ag.labadmin_users LIMIT 1"""
    #     email = db._con.execute_fetchone(sql)[0]
    #     created_on = datetime.datetime(2016, 8, 15, 0, 0)
    #     spinfo = {'name': 'test_plate',
    #               'plate_type_id': ptid,
    #               'email': email,
    #               'created_on': created_on,
    #               'notes': 'Hi!'}
    #     spid = db.create_sample_plate(**spinfo)
    #     obs = db.read_sample_plate(spid)
    #     self.assertDictEqual(obs, spinfo)
    #     # Attempt to read a sample plate that does not exist
    #     db.delete_sample_plate(spid)
    #     with self.assertRaises(ValueError) as context:
    #         db.read_sample_plate(spid)
    #     err = 'Sample plate ID %s does not exist.' % spid
    #     self.assertEqual(str(context.exception), err)
    #
    # def test_write_sample_plate_layout(self):
    #     # Populate a sample plate with two samples
    #     sid = db.create_study(title='study')
    #     samples = [{'id': x, 'study_ids': [sid]} for x in ('1', '2', '3')]
    #     db.create_samples(samples)
    #     sql = """SELECT plate_type_id FROM pm.plate_type LIMIT 1"""
    #     ptid = db._con.execute_fetchone(sql)[0]
    #     spid = db.create_sample_plate('test_plate', ptid)
    #     splayout = [
    #         {'sample_id': '1', 'col': 1, 'row': 1},
    #         {'sample_id': '2', 'col': 1, 'row': 2, 'name': 'B'}
    #     ]
    #     db.write_sample_plate_layout(spid, splayout)
    #     obs = db.read_sample_plate_layout(spid)
    #     exp = [
    #         {'sample_id': '1', 'col': 1, 'row': 1, 'name': None,
    #          'notes': None},
    #         {'sample_id': '2', 'col': 1, 'row': 2, 'name': 'B',
    #          'notes': None}
    #     ]
    #     self.assertListEqual(obs, exp)
    #     # Clear the exisiting layout and add one sample
    #     splayout = [{'sample_id': '3', 'col': 1, 'row': 3, 'notes': 'Hi!'}]
    #     db.write_sample_plate_layout(spid, splayout)
    #     obs = db.read_sample_plate_layout(spid)
    #     exp = [{'sample_id': '3', 'col': 1, 'row': 3, 'name': None,
    #             'notes': 'Hi!'}]
    #     self.assertListEqual(obs, exp)
    #     # Attempt to populate a sample plate with a non-existing sample
    #     splayout = [{'sample_id': '4', 'col': 2, 'row': 1}]
    #     with self.assertRaises(ValueError) as context:
    #         db.write_sample_plate_layout(spid, splayout)
    #     err = 'Sample ID 4 does not exist.'
    #     self.assertEqual(str(context.exception), err)
    #     # Attempt to populate a sample plate that does not exist
    #     db.delete_sample_plate(spid)
    #     with self.assertRaises(ValueError) as context:
    #         db.write_sample_plate_layout(spid, splayout)
    #     err = 'Sample plate ID %s does not exist.' % spid
    #     self.assertEqual(str(context.exception), err)
    #     db.delete_samples([x['id'] for x in samples])
    #     db.delete_study(sid)
    #
    # def test_read_sample_plate_layout(self):
    #     # Read a sample plate's layout containing three sample
    #     sid = db.create_study(title='study')
    #     samples = [{'id': x, 'study_ids': [sid]} for x in ('1', '2', '3')]
    #     db.create_samples(samples)
    #     sql = """SELECT plate_type_id FROM pm.plate_type LIMIT 1"""
    #     ptid = db._con.execute_fetchone(sql)[0]
    #     spid = db.create_sample_plate('test_plate', ptid)
    #     splayout = [
    #         {'sample_id': '1', 'col': 1, 'row': 1},
    #         {'sample_id': '2', 'col': 1, 'row': 2, 'name': 'B'},
    #         {'sample_id': '3', 'col': 1, 'row': 3, 'notes': 'Hi!'}
    #     ]
    #     db.write_sample_plate_layout(spid, splayout)
    #     obs = db.read_sample_plate_layout(spid)
    #     exp = [
    #         {'sample_id': '1', 'col': 1, 'row': 1, 'name': None,
    #          'notes': None},
    #         {'sample_id': '2', 'col': 1, 'row': 2, 'name': 'B',
    #          'notes': None},
    #         {'sample_id': '3', 'col': 1, 'row': 3, 'name': None,
    #          'notes': 'Hi!'}
    #     ]
    #     self.assertListEqual(obs, exp)
    #     # Read a sample plate's layout that is clear
    #     db._clear_sample_plate_layout(spid)
    #     obs = db.read_sample_plate_layout(spid)
    #     self.assertListEqual(obs, [])
    #     # Attempt to read layout of a non-existing sample plate
    #     db.delete_sample_plate(spid)
    #     with self.assertRaises(ValueError) as context:
    #         db.write_sample_plate_layout(spid, splayout)
    #     err = 'Sample plate ID %s does not exist.' % spid
    #     self.assertEqual(str(context.exception), err)
    #     db.delete_samples([x['id'] for x in samples])
    #     db.delete_study(sid)
    #
    # def test_delete_sample_plate(self):
    #     # Delete a sample plate and its layout
    #     sql = """SELECT plate_type_id FROM pm.plate_type LIMIT 1"""
    #     ptid = db._con.execute_fetchone(sql)[0]
    #     spid = db.create_sample_plate('test_plate', ptid)
    #     obs = db.read_sample_plate(spid)
    #     self.assertIsNotNone(obs)
    #     sid = db.create_study(title='study')
    #     db.create_samples([{'id': '1', 'study_ids': [sid]}])
    #     splayout = [{'sample_id': '1', 'col': 1, 'row': 1}]
    #     db.write_sample_plate_layout(spid, splayout)
    #     obs = db.read_sample_plate_layout(spid)
    #     self.assertTrue(obs)
    #     db.delete_sample_plate(spid)
    #     with self.assertRaises(ValueError) as context:
    #         db.read_sample_plate(spid)
    #     err = 'Sample plate ID %s does not exist.' % spid
    #     self.assertEqual(str(context.exception), err)
    #     obs = db._sample_plate_layout_exists(spid)
    #     self.assertFalse(obs)
    #     db.delete_samples(['1'])
    #     db.delete_study(sid)
    #     # Attempt to delete a sample plate that does not exist
    #     with self.assertRaises(ValueError) as context:
    #         db.delete_sample_plate(spid)
    #     err = 'Sample plate ID %s does not exist.' % spid
    #     self.assertEqual(str(context.exception), err)
    #
    # def test_get_property_options(self):
    #     # Get available extraction robots
    #     obs = db.get_property_options("extraction_robot")
    #     exp = [{'id': 1, 'name': 'HOWE_KF1', 'notes': None},
    #            {'id': 2, 'name': 'HOWE_KF2', 'notes': None},
    #            {'id': 3, 'name': 'HOWE_KF3', 'notes': None},
    #            {'id': 4, 'name': 'HOWE_KF4', 'notes': None}]
    #     self.assertListEqual(obs, exp)
    #
    # def test_get_plate_types(self):
    #     # Get available plate types
    #     obs = db.get_plate_types()
    #     exp = [{'id': 1, 'name': '96-well', 'notes': 'Standard 96-well plate',
    #             'cols': 12, 'rows': 8}]
    #     self.assertListEqual(obs, exp)
    #
    # def test_get_emails(self):
    #     # Get available emails
    #     obs = db.get_emails()
    #     exp = ['test']
    #     self.assertListEqual(obs, exp)
    #
    # def test_get_sample_plate_ids(self):
    #     sql = """SELECT plate_type_id FROM pm.plate_type LIMIT 1"""
    #     ptid = db._con.execute_fetchone(sql)[0]
    #     spid = db.create_sample_plate('test_plate', ptid)
    #     obs = db.get_sample_plate_ids()[-1]
    #     self.assertEqual(obs, spid)
    #     db.delete_sample_plate(spid)
    #
    # def test_get_sample_plate_list(self):
    #     # Create a sample plate
    #     sql = """SELECT plate_type_id FROM pm.plate_type LIMIT 1"""
    #     ptid = db._con.execute_fetchone(sql)[0]
    #     sql = """SELECT email FROM ag.labadmin_users LIMIT 1"""
    #     email = db._con.execute_fetchone(sql)[0]
    #     created_on = datetime.datetime.combine(datetime.date.today(),
    #                                            datetime.time.min)
    #     spinfo = {'name': 'test_plate',
    #               'plate_type_id': ptid,
    #               'email': email,
    #               'created_on': created_on,
    #               'notes': 'A test plate'}
    #     spid = db.create_sample_plate(**spinfo)
    #     sid = db.create_study(title='test_study')
    #     samples = [{'id': x, 'study_ids': [sid]} for x in ('1', '2', '3')]
    #     db.create_samples(samples)
    #     splayout = [{'sample_id': str(x), 'col': 1, 'row': x}
    #                 for x in (1, 2, 3)]
    #     db.write_sample_plate_layout(spid, splayout)
    #     obs = db.get_sample_plate_list()[-1]
    #     exp = {'id': spid,
    #            'name': 'test_plate',
    #            'type': ['96-well', 96],
    #            'person': email,
    #            'date': created_on.strftime('%m/%d/%Y'),
    #            'fill': [3, 0.031],
    #            'study': [1, sid, None, 'test_study']}
    #     self.assertDictEqual(obs, exp)
    #     db.delete_sample_plate(spid)
    #     db.delete_samples(['1', '2', '3'])
    #     db.delete_study(sid)


if __name__ == "__main__":
    main()

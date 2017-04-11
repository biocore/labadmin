from unittest import TestCase, main
from os.path import join, dirname, realpath
from six import StringIO
from functools import partial
from traceback import format_exc
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
                      "affected by this! Reason: %s" % format_exc(e))

    def _create_test_data_targeted_plate(self):
        # Create a study
        db.create_study(9999, title='LabAdmin test project', alias='LTP',
                        jira_id='KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))

        # Create some sample plates
        pt = db.get_plate_types()[0]
        plate_id = db.create_sample_plate('Test plate', pt['id'], 'test',
                                          [9999])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id))
        plate_id_2 = db.create_sample_plate('Test plate 2', pt['id'], 'test',
                                            [9999])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id_2))

        # Plate some samples
        # Add samples to the study
        samples = ['9999.Sample_1', '9999.Sample_2', '9999.Sample_3',
                   '9999.Sample_3']
        db.set_study_samples(9999, samples)

        # Create the layout
        layout = []
        row = []
        for i in range(pt['rows']):
            for j in range(pt['cols']):
                row.append({'sample_id': None, 'name': None, 'notes': None})
            layout.append(row)
            row = []
        layout[0][0]['sample_id'] = samples[0]
        layout[0][1]['sample_id'] = samples[1]
        layout[0][2]['sample_id'] = samples[2]
        db.write_sample_plate_layout(plate_id, layout)
        layout[0][3]['sample_id'] = samples[3]
        db.write_sample_plate_layout(plate_id_2, layout)

        # Create DNA plates
        dna_plate_ids = db.extract_sample_plates(
            [plate_id, plate_id_2], 'test', 'HOWE_KF1', 'PM16B11', '108379Z')
        for p_id in dna_plate_ids:
            self._clean_up_funcs.insert(
                0, partial(db.delete_dna_plate, p_id))

        # Create the target gene plates
        plate_links = [
            {'dna_plate_id': dna_plate_ids[0], 'primer_plate_id': 1},
            {'dna_plate_id': dna_plate_ids[1], 'primer_plate_id': 2}]
        targeted_plate_ids = db.prepare_targeted_libraries(
            plate_links, 'test', 'ROBE', '208484Z', '108364Z', '14459',
            'RNBD9959')

        for p_id in targeted_plate_ids:
            self._clean_up_funcs.insert(
                0, partial(db.delete_targeted_plate, p_id))

        return targeted_plate_ids

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
               'sample_barcode_file_md5': None}}
        participant_names = db.ut_get_participant_names_from_ag_login_id(
            ag_login_id)
        for key in obs:
            del(obs[key]['registered_on'])
            # only look at those fields, that are not subject to scrubbing
            self.assertEqual({k: obs[key][k] for k in exp[key]}, exp[key])
            self.assertIn(obs[key]['participant_name'], participant_names)

    def test_list_ag_surveys(self):
        truth = [(-1, 'Personal Information', True),
                 (-2, 'Pet Information', True),
                 (-3, 'Fermented Foods', True),
                 (-4, 'Surfers', True),
                 (-5, 'Personal_Microbiome', True)]
        self.assertItemsEqual(db.list_ag_surveys(), truth)

        truth = [(-1, 'Personal Information', False),
                 (-2, 'Pet Information', True),
                 (-3, 'Fermented Foods', False),
                 (-4, 'Surfers', True),
                 (-5, 'Personal_Microbiome', False)]
        self.assertItemsEqual(db.list_ag_surveys([-2, -4]), truth)

    # - PlateMapper functions tests - #
    def test_get_studies(self):
        obs = db.get_studies()
        self.assertEqual(obs, [])

        db.create_study(9999, 'LabAdmin test project', 'LTP', 'KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))

        # Cast the DictCursor list to a dict list so assertEqual works
        obs = map(dict, db.get_studies())
        exp = [{'study_id': 9999, 'title': 'LabAdmin test project',
               'alias': 'LTP', 'jira_id': 'KL9999'}]
        self.assertEqual(obs, exp)

        db.create_study(9998, 'Understanding the Cannabis Microbiome',
                        'Cannabis Soils', 'KL9999998')
        self._clean_up_funcs.append(partial(db.delete_study, 9998))

        obs = map(dict, db.get_studies())
        exp = [{'study_id': 9998,
                'title': 'Understanding the Cannabis Microbiome',
                'alias': 'Cannabis Soils', 'jira_id': 'KL9999998'},
               {'study_id': 9999, 'title': 'LabAdmin test project',
                'alias': 'LTP', 'jira_id': 'KL9999'}]
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
               'alias': 'LTP', 'jira_id': 'KL9999'}
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
               'alias': 'LTP', 'jira_id': 'KL9999'}
        self.assertEqual(obs, exp)
        db.edit_study(9999, title='Test study 2', alias='the study')
        obs = db.read_study(9999)
        exp = {'study_id': 9999, 'title': 'Test study 2',
               'alias': 'the study', 'jira_id': 'KL9999'}
        self.assertEqual(obs, exp)

        # Test success changing only one of the values
        db.edit_study(9999, title='LabAdmin test project')
        obs = db.read_study(9999)
        exp = {'study_id': 9999, 'title': 'LabAdmin test project',
               'alias': 'the study', 'jira_id': 'KL9999'}
        self.assertEqual(obs, exp)

        db.edit_study(9999, alias='LTP')
        obs = db.read_study(9999)
        exp = {'study_id': 9999, 'title': 'LabAdmin test project',
               'alias': 'LTP', 'jira_id': 'KL9999'}
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
                        alias='LTP', jira_id='KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))
        obs = db.read_study(9999)
        exp = {'study_id': 9999, 'title': 'LabAdmin test project',
               'alias': 'LTP', 'jira_id': 'KL9999'}
        self.assertEqual(obs, exp)

        # Attempt to read properties of a non-existing study
        with self.assertRaises(ValueError) as ctx:
            db.read_study(0)
        self.assertEqual(ctx.exception.message,
                         'Study ID 0 does not exist.')

    def test_delete_study(self):
        # Delete a study without samples
        db.create_study(9999, title='LabAdmin test project',
                        alias='LTP', jira_id='KL9999')
        db.delete_study(9999)
        # Check that the study has been deleted by trying to delete it again
        with self.assertRaises(ValueError) as ctx:
            db.delete_study(9999)
        self.assertEqual(ctx.exception.message,
                         'Study ID 9999 does not exist.')

        # Delete a study with three samples associated
        db.create_study(9999, title='LabAdmin test project',
                        alias='LTP', jira_id='KL9999')
        db.set_study_samples(9999, ['9999.sample1', '9999.sample2',
                                    '9999.sample3'])
        db.delete_study(9999)
        with self.assertRaises(ValueError) as ctx:
            db.delete_study(9999)
        self.assertEqual(ctx.exception.message,
                         'Study ID 9999 does not exist.')

        # Raises an error when trying to delete a study with samples plated
        db.create_study(9999, title='LabAdmin test project',
                        alias='LTP', jira_id='KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))
        # Add samples to the study
        samples = ['9999.Sample_1', '9999.Sample_2', '9999.Sample_3']
        db.set_study_samples(9999, samples)

        # Create a plate
        pt = db.get_plate_types()[0]
        plate_id = db.create_sample_plate('Test plate', pt['id'],
                                          'test', [9999])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id))
        # Create the layout
        layout = []
        row = []
        for i in range(pt['rows']):
            for j in range(pt['cols']):
                row.append({'sample_id': None, 'name': None, 'notes': None})
            layout.append(row)
            row = []
        layout[0][0]['sample_id'] = samples[0]
        layout[0][1]['sample_id'] = samples[1]
        layout[0][2]['sample_id'] = samples[2]
        db.write_sample_plate_layout(plate_id, layout)

        with self.assertRaises(ValueError) as ctx:
            db.delete_study(9999)
        self.assertEqual(ctx.exception.message,
                         "Can't remove study 9999, samples have been plated. "
                         "Try removing the plates first.")

    def test_set_study_samples(self):
        # Create a study
        db.create_study(9999, title='LabAdmin test project', alias='LTP',
                        jira_id='KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))

        # Add samples to an empty study
        samples = ['9999.sample1', '9999.sample2']
        db.set_study_samples(9999, samples)
        obs = db.get_study_samples(9999)
        self.assertItemsEqual(obs, samples)

        # Add more samples
        samples.append('9999.sample3')
        db.set_study_samples(9999, samples)
        obs = db.get_study_samples(9999)
        self.assertItemsEqual(obs, samples)

        # Remove one sample
        samples.remove('9999.sample3')
        db.set_study_samples(9999, samples)
        obs = db.get_study_samples(9999)
        self.assertItemsEqual(obs, samples)

        # Try to remove a sample that has been plated
        # Create a plate
        pt = db.get_plate_types()[0]
        plate_id = db.create_sample_plate('Test plate', pt['id'],
                                          'test', [9999])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id))
        # Create the layout
        layout = []
        row = []
        for i in range(pt['rows']):
            for j in range(pt['cols']):
                row.append({'sample_id': None, 'name': None, 'notes': None})
            layout.append(row)
            row = []
        layout[0][0]['sample_id'] = '9999.sample1'
        layout[0][1]['sample_id'] = '9999.sample2'
        db.write_sample_plate_layout(plate_id, layout)

        with self.assertRaises(ValueError) as ctx:
            db.delete_study(9999)
        self.assertEqual(ctx.exception.message,
                         "Can't remove study 9999, samples have been plated. "
                         "Try removing the plates first.")

        # Try to add samples to a study that does not exist
        with self.assertRaises(ValueError) as ctx:
            db.set_study_samples(9998, ['9998.sample1', '9998.sample2'])
        self.assertEqual(ctx.exception.message,
                         'Study ID 9998 does not exist.')

    def test_get_study_plated_samples(self):
        # Create a study
        db.create_study(9999, title='LabAdmin test project', alias='LTP',
                        jira_id='KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))

        # Retrieve plated samples from an empty study
        self.assertEqual(db.get_study_plated_samples(9999), {})

        # Retrieve plated samples from a study with no samples plated
        db.set_study_samples(
            9999, ['9999.sample1', '9999.sample2', '9999.sample3'])
        self.assertEqual(db.get_study_plated_samples(9999), {})

        # Put samples in a couple of plates
        # Create a plate
        pt = db.get_plate_types()[0]
        plate_id = db.create_sample_plate('Test plate', pt['id'],
                                          'test', [9999])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id))
        plate_id_2 = db.create_sample_plate('Test plate 2', pt['id'],
                                            'test', [9999])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id_2))
        # Create the layout
        layout = []
        row = []
        for i in range(pt['rows']):
            for j in range(pt['cols']):
                row.append({'sample_id': None, 'name': None, 'notes': None})
            layout.append(row)
            row = []
        layout[0][0]['sample_id'] = '9999.sample1'
        layout[0][1]['sample_id'] = '9999.sample2'
        layout[0][2]['sample_id'] = '9999.sample1'
        db.write_sample_plate_layout(plate_id, layout)
        layout[0][1]['sample_id'] = '9999.sample3'
        db.write_sample_plate_layout(plate_id_2, layout)

        exp = {plate_id: ['9999.sample1', '9999.sample2'],
               plate_id_2: ['9999.sample1', '9999.sample3']}
        self.assertEqual(db.get_study_plated_samples(9999), exp)

        # Try to get plated samples from a study that does not exist
        with self.assertRaises(ValueError) as ctx:
            db.get_study_plated_samples(9998)
        self.assertEqual(ctx.exception.message,
                         'Study ID 9998 does not exist.')

    def test_get_study_samples(self):
        # Create a study
        db.create_study(9999, title='LabAdmin test project', alias='LTP',
                        jira_id='KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))

        # Retrieve samples from an empty study
        self.assertEqual(db.get_study_samples(9999), [])

        # Retrieve samples
        samples = ['9999.sample1', '9999.sample2']
        db.set_study_samples(9999, samples)
        obs = db.get_study_samples(9999)
        self.assertItemsEqual(obs, samples)

        # Try to access to a study that doesn't exist
        with self.assertRaises(ValueError) as ctx:
            db.get_study_samples(9998)
        self.assertEqual(ctx.exception.message,
                         'Study ID 9998 does not exist.')

    def test_sample_plate_name_exists(self):
        self.assertFalse(db.sample_plate_name_exists('Test plate'))
        # Create a study
        db.create_study(9999, title='LabAdmin test project',
                        alias='LTP', jira_id='KL9999')
        # Create a new plate
        # Magic number 0 -> we just want to get on plate type, so whatever
        # is first works for us
        pt_id = db.get_plate_types()[0]['id']
        plate_id = db.create_sample_plate('Test plate', pt_id, 'test', [9999])
        self._clean_up_funcs.append(partial(db.delete_sample_plate, plate_id))
        self._clean_up_funcs.append(partial(db.delete_study, 9999))
        self.assertTrue(db.sample_plate_name_exists('Test plate'))
        self.assertFalse(db.sample_plate_name_exists('Test plate 2'))

    def test_create_sample_plate(self):
        # Create a study
        db.create_study(9999, title='LabAdmin test project',
                        alias='LTP', jira_id='KL9999')
        # Magic number 0 -> we just want to get on plate type, so whatever
        # is first works for us
        pt_id = db.get_plate_types()[0]['id']
        before = datetime.datetime.now()
        plate_id = db.create_sample_plate('Test plate', pt_id, 'test', [9999])
        self._clean_up_funcs.append(partial(db.delete_sample_plate, plate_id))
        self._clean_up_funcs.append(partial(db.delete_study, 9999))
        after = datetime.datetime.now()
        obs = db.read_sample_plate(plate_id)
        self.assertTrue(before < obs.pop('created_on') < after)
        exp = {'name': 'Test plate', 'plate_type_id': pt_id, 'email': 'test',
               'notes': None, 'studies': [9999]}
        self.assertEqual(obs, exp)

        # Attempt to create a sample plate with a duplicate name
        with self.assertRaises(ValueError) as context:
            db.create_sample_plate('Test plate', pt_id, 'test', [9999])
        err = ('Name \'Test plate\' conflicts with exisiting sample '
               'plate %s.' % plate_id)
        self.assertEqual(context.exception.message, err)

        # Attempt to create a sample plate with an invalid email
        with self.assertRaises(ValueError) as context:
            db.create_sample_plate('Plate 2', pt_id, 'not-an-email', [9999])
        err = 'Email not-an-email does not exist.'
        self.assertEqual(context.exception.message, err)

        # Attempt to create a sample plate with an invalid plate type
        with self.assertRaises(ValueError) as context:
            db.create_sample_plate('Plate 2', 12345, 'test', [9999])
        err = 'Plate type ID 12345 does not exist.'
        self.assertEqual(context.exception.message, err)

    def test_edit_sample_plate(self):
        # Create a study
        db.create_study(9999, title='LabAdmin test project',
                        alias='LTP', jira_id='KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))

        # Create a plate
        pt = db.get_plate_types()[0]
        plate_id = db.create_sample_plate('Test plate', pt['id'],
                                          'test', [9999])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id))

        obs = db.read_sample_plate(plate_id)
        # Remove created_on since it is not deterministic and its correctness
        # have been tested elsewhere
        del obs['created_on']
        exp = {'name': 'Test plate', 'plate_type_id': pt['id'],
               'email': 'test', 'notes': None, 'studies': [9999]}
        self.assertEqual(obs, exp)

        # Update some attributes of the plate
        exp_date = datetime.datetime.now()
        db.edit_sample_plate(plate_id, name='Test Plate 2',
                             created_on=exp_date, notes='Testing notes')
        obs = db.read_sample_plate(plate_id)
        exp = {'name': 'Test Plate 2', 'plate_type_id': pt['id'],
               'email': 'test', 'notes': 'Testing notes', 'studies': [9999],
               'created_on': exp_date}
        self.assertEqual(obs, exp)

        # Raises an error when no attribute is being updated
        with self.assertRaises(ValueError) as ctx:
            db.edit_sample_plate(plate_id)
        self.assertEqual(ctx.exception.message,
                         'At least one of name, plate_type_id, email, '
                         'created_on or notes sould be provided')

        # Raises an error when the plate does not exists
        with self.assertRaises(ValueError) as ctx:
            db.edit_sample_plate(plate_id + 1, name='test')
        self.assertEqual(ctx.exception.message,
                         'Sample plate ID %s does not exist.' % (plate_id + 1))

        # Raises an error when sample plate name is not unique
        dup_id = db.create_sample_plate('Test plate', pt['id'], 'test', [9999])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, dup_id))
        with self.assertRaises(ValueError) as ctx:
            db.edit_sample_plate(plate_id, name='Test plate')
        self.assertEqual(ctx.exception.message,
                         "Name 'Test plate' conflicts with exisiting sample "
                         "plate %s." % dup_id)

        # Raises an error when sample plate type does not exist
        with self.assertRaises(ValueError) as ctx:
            db.edit_sample_plate(plate_id, plate_type_id=0)
        self.assertEqual(ctx.exception.message,
                         'Plate type ID 0 does not exist.')

        # Raises an error when plate_type_id is provided and samples have been
        # already plated
        # Add samples to the study
        samples = ['9999.Sample_1', '9999.Sample_2', '9999.Sample_3']
        db.set_study_samples(9999, samples)

        # Create the layout
        layout = []
        row = []
        for i in range(pt['rows']):
            for j in range(pt['cols']):
                row.append({'sample_id': None, 'name': None, 'notes': None})
            layout.append(row)
            row = []
        layout[0][0]['sample_id'] = samples[0]
        layout[0][1]['sample_id'] = samples[1]
        layout[0][2]['sample_id'] = samples[2]
        db.write_sample_plate_layout(plate_id, layout)

        # Raises an error when the email does not exists
        with self.assertRaises(ValueError) as ctx:
            db.edit_sample_plate(plate_id, email='does@not.exist')
        self.assertEqual(ctx.exception.message,
                         'Email does@not.exist does not exist.')

    def test_read_sample_plate(self):
        # Create a study
        db.create_study(9999, title='LabAdmin test project',
                        alias='LTP', jira_id='KL9999')
        # Magic number 0 -> we just want to get on plate type, so whatever
        # is first works for us
        pt_id = db.get_plate_types()[0]['id']
        before = datetime.datetime.now()
        plate_id = db.create_sample_plate('Test plate', pt_id, 'test', [9999])
        self._clean_up_funcs.append(partial(db.delete_sample_plate, plate_id))
        self._clean_up_funcs.append(partial(db.delete_study, 9999))
        after = datetime.datetime.now()
        obs = db.read_sample_plate(plate_id)
        self.assertTrue(before < obs.pop('created_on') < after)
        exp = {'name': 'Test plate', 'plate_type_id': pt_id, 'email': 'test',
               'notes': None, 'studies': [9999]}
        self.assertEqual(obs, exp)

        # Attempt to read a sample plate that does not exist
        with self.assertRaises(ValueError) as context:
            db.read_sample_plate(1000)
        err = 'Sample plate ID 1000 does not exist.'
        self.assertEqual(context.exception.message, err)

    def test_write_sample_plate_layout(self):
        # Create a study
        db.create_study(9999, title='LabAdmin test project',
                        alias='LTP', jira_id='KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))

        # Create a plate
        plate_type = db.get_plate_types()[0]
        plate_id = db.create_sample_plate('Test plate', plate_type['id'],
                                          'test', [9999])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id))

        # Add samples to the study
        samples = ['Sample_%d_%d' % (i, j)
                   for i in range(plate_type['rows'])
                   for j in range(plate_type['cols'])]
        db.set_study_samples(9999, samples)

        # Create the layout
        layout = []
        row = []
        for i in range(plate_type['rows']):
            for j in range(plate_type['cols']):
                row.append({'sample_id': samples[i * plate_type['cols'] + j],
                            'name': "%d_%d" % (i, j), 'notes': None})
            layout.append(row)
            row = []

        db.write_sample_plate_layout(plate_id, layout)
        obs = db.read_sample_plate_layout(plate_id)
        self.assertEqual(obs, layout)

        # Update a value
        layout[0][0]['sample_id'] = samples[-1]
        db.write_sample_plate_layout(plate_id, layout)
        obs = db.read_sample_plate_layout(plate_id)
        self.assertEqual(obs, layout)

        # Store an incomplete plate, either by providing None one everything...
        layout[0][0]['sample_id'] = None
        layout[0][0]['name'] = None
        layout[0][0]['notes'] = None
        db.write_sample_plate_layout(plate_id, layout)
        obs = db.read_sample_plate_layout(plate_id)
        self.assertEqual(obs, layout)

        # ... or by providing an empty dict (easier for GUI interaction)
        layout[0][0] = {}
        db.write_sample_plate_layout(plate_id, layout)
        obs = db.read_sample_plate_layout(plate_id)
        layout[0][0]['sample_id'] = None
        layout[0][0]['name'] = None
        layout[0][0]['notes'] = None
        self.assertEqual(obs, layout)

        # Attempt to write the layout of a sample plate that doesn't exist
        with self.assertRaises(ValueError) as ctx:
            db.write_sample_plate_layout(1000, layout)
        self.assertEqual(ctx.exception.message,
                         'Sample plate ID 1000 does not exist.')

        # Make one row shorter than the others
        layout[0] = layout[0][:-2]
        with self.assertRaises(ValueError) as ctx:
            db.write_sample_plate_layout(plate_id, layout)
        self.assertEqual(ctx.exception.message,
                         "The given layout doesn't form a valid plate map "
                         "because not all rows have the same number of "
                         "columns")

        # Attempt to add a layout with different dimensions
        layout.remove(layout[0])
        with self.assertRaises(ValueError) as ctx:
            db.write_sample_plate_layout(plate_id, layout)
        self.assertEqual(ctx.exception.message,
                         "The given layout doesn't match the plate type "
                         "dimensions. Plate type: (%d, %d). Layout: (%d, %d)"
                         % (plate_type['rows'], plate_type['cols'],
                            plate_type['rows'] - 1, plate_type['cols']))

    def test_read_sample_plate_layout(self):
        # We are not going to test here that this function reads a complete
        # layout correctly, that is implicitly tested on the function
        # test_write_sample_plate_layout

        # Create a study
        db.create_study(9999, title='LabAdmin test project',
                        alias='LTP', jira_id='KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))

        # Create a plate
        plate_type = db.get_plate_types()[0]
        plate_id = db.create_sample_plate('Test plate', plate_type['id'],
                                          'test', [9999])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id))

        # Test that if the layout doesn't exist it returns an empty list
        self.assertEqual(db.read_sample_plate_layout(plate_id), [])

        # Attempt to read a layout of a plate that doesn't exist
        with self.assertRaises(ValueError) as ctx:
            db.read_sample_plate_layout(1000)
        self.assertEqual(ctx.exception.message,
                         'Sample plate ID 1000 does not exist.')

    def test_delete_sample_plate(self):
        # Create a study
        db.create_study(9999, title='LabAdmin test project',
                        alias='LTP', jira_id='KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))
        # Magic number 0 -> we just want to get on plate type, so whatever
        # is first works for us
        pt_id = db.get_plate_types()[0]['id']
        plate_id = db.create_sample_plate('Test plate', pt_id, 'test', [9999])
        obs = db.read_sample_plate(plate_id)
        self.assertIsNotNone(obs)
        db.delete_sample_plate(plate_id)
        # Attempt to delete a sample plate that does not exist, this way
        # we also check that the plate has been removed correctly
        with self.assertRaises(ValueError) as context:
            db.delete_sample_plate(plate_id)
        err = 'Sample plate ID %s does not exist.' % plate_id
        self.assertEqual(str(context.exception), err)

    def test_get_property_options(self):
        # Get available extraction robots
        obs = db.get_property_options("extraction_robot")
        exp = [{'id': 1, 'name': 'HOWE_KF1', 'notes': None},
               {'id': 2, 'name': 'HOWE_KF2', 'notes': None},
               {'id': 3, 'name': 'HOWE_KF3', 'notes': None},
               {'id': 4, 'name': 'HOWE_KF4', 'notes': None}]
        self.assertListEqual(obs, exp)

    def test_get_or_create_property_option_id(self):
        existing = db.get_property_options("extraction_robot")

        # Correctly retrieves an option that already exists
        obs = db.get_or_create_property_option_id(
            "extraction_robot", existing[0]['name'])
        self.assertEqual(obs, existing[0]['id'])

        # Test that it creates the property option correctly
        obs = db.get_or_create_property_option_id(
            "extraction_robot", 'LabAdminTest')
        self._clean_up_funcs.append(
            partial(db.delete_property_option, "extraction_robot", obs))
        self.assertTrue(obs > max([e['id'] for e in existing]))

    def test_delete_property_option(self):
        obs = db.get_or_create_property_option_id("extraction_robot",
                                                  "LabAdminTest")
        exp = {'id': obs, 'name': 'LabAdminTest', 'notes': None}
        self.assertIn(exp, db.get_property_options("extraction_robot"))
        db.delete_property_option("extraction_robot", obs)
        self.assertNotIn(exp, db.get_property_options("extraction_robot"))

    def test_get_plate_types(self):
        # Get available plate types
        obs = db.get_plate_types()
        exp = [{'id': 1, 'name': '96-well',
                'notes': 'Standard 96-well plate',
                'cols': 12, 'rows': 8}]
        self.assertEqual(obs, exp)

    def test_read_plate_type(self):
        obs = db.read_plate_type(1)
        exp = {'plate_type_id': 1, 'name': '96-well',
               'notes': 'Standard 96-well plate',
               'cols': 12, 'rows': 8}
        self.assertEqual(dict(obs), exp)
        with self.assertRaises(ValueError) as ctx:
            db.read_plate_type(100)
        self.assertEqual(ctx.exception.message, "Plate type 100 doesn't exist")

    def test_get_emails(self):
        # Get available emails
        obs = db.get_emails()
        exp = ['test']
        self.assertListEqual(obs, exp)

    def test_get_sample_plate_ids(self):
        self.assertEqual(db.get_sample_plate_ids(), [])

        # Create a study
        db.create_study(9999, title='LabAdmin test project',
                        alias='LTP', jira_id='KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))
        # Magic number 0 -> we just want to get on plate type, so whatever
        # is first works for us
        pt_id = db.get_plate_types()[0]['id']
        plate_id = db.create_sample_plate('Test plate', pt_id, 'test', [9999])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id))
        self.assertEqual(db.get_sample_plate_ids(), [plate_id])

        plate_id_2 = db.create_sample_plate('Test plate 2', pt_id,
                                            'test', [9999])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id_2))
        self.assertEqual(db.get_sample_plate_ids(), [plate_id, plate_id_2])

    def test_get_sample_plate_list(self):
        self.assertEqual(db.get_sample_plate_list(), [])

        # Create a couple of studies
        db.create_study(9999, title='LabAdmin test project', alias='LTP',
                        jira_id='KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))
        db.create_study(9998, title='LabAdmin test project 2', alias='LTP2',
                        jira_id='KL9998')
        self._clean_up_funcs.append(partial(db.delete_study, 9998))
        # Magic number 0 -> we just want to get on plate type, so whatever
        # is first works for us
        pt = db.get_plate_types()[0]

        plate_id = db.create_sample_plate('Test plate', pt['id'],
                                          'test', [9999])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id))

        plate_id_2 = db.create_sample_plate('Test plate 2', pt['id'], 'test',
                                            [9998])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id_2))

        plate_id_3 = db.create_sample_plate('Test plate 3', pt['id'], 'test',
                                            [9999, 9998])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id_3))

        # Try first with an empty plate
        pt_name = pt['name']
        pt_wells = pt['rows'] * pt['cols']
        date = datetime.date.today()
        obs = db.get_sample_plate_list()
        exp = [{'id': plate_id, 'name': 'Test plate',
                'type': [pt_name, pt_wells], 'person': 'test',
                'date': date, 'fill': [0, 0.000],
                'studies': ['LabAdmin test project']},
               {'id': plate_id_2, 'name': 'Test plate 2',
                'type': [pt_name, pt_wells], 'person': 'test',
                'date': date, 'fill': [0, 0.000],
                'studies': ['LabAdmin test project 2']},
               {'id': plate_id_3, 'name': 'Test plate 3',
                'type': [pt_name, pt_wells], 'person': 'test',
                'date': date, 'fill': [0, 0.000],
                'studies': ['LabAdmin test project',
                            'LabAdmin test project 2']}]
        self.assertEqual(obs, exp)

        # Plate some samples and check the output again
        # Add samples to the study
        samples = ['9999.Sample_1', '9999.Sample_2', '9999.Sample_3']
        db.set_study_samples(9999, samples)

        # Create the layout
        layout = []
        row = []
        for i in range(pt['rows']):
            for j in range(pt['cols']):
                row.append({'sample_id': None, 'name': None, 'notes': None})
            layout.append(row)
            row = []
        layout[0][0]['sample_id'] = samples[0]
        layout[0][1]['sample_id'] = samples[1]
        layout[0][2]['sample_id'] = samples[2]
        db.write_sample_plate_layout(plate_id, layout)

        obs = db.get_sample_plate_list()
        exp = [{'id': plate_id, 'name': 'Test plate',
                'type': [pt_name, pt_wells], 'person': 'test',
                'date': date, 'fill': [3, round(3 / pt_wells, 3)],
                'studies': ['LabAdmin test project']},
               {'id': plate_id_2, 'name': 'Test plate 2',
                'type': [pt_name, pt_wells], 'person': 'test',
                'date': date, 'fill': [0, 0.000],
                'studies': ['LabAdmin test project 2']},
               {'id': plate_id_3, 'name': 'Test plate 3',
                'type': [pt_name, pt_wells], 'person': 'test',
                'date': date, 'fill': [0, 0.000],
                'studies': ['LabAdmin test project',
                            'LabAdmin test project 2']}]
        self.assertEqual(obs, exp)

    def test_extract_sample_plates(self):
        # Create a study
        db.create_study(9999, title='LabAdmin test project', alias='LTP',
                        jira_id='KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))

        # Create a sample plate
        pt = db.get_plate_types()[0]
        plate_id = db.create_sample_plate('Test plate', pt['id'],
                                          'test', [9999])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id))

        exp_robot = db.get_property_options("extraction_robot")[0]
        exp_kit = db.get_property_options("extraction_kit_lot")[0]
        exp_tool = db.get_property_options("extraction_tool")[0]
        before = datetime.datetime.now()
        obs = db.extract_sample_plates(
            [plate_id], 'test', exp_robot['name'], exp_kit['name'],
            exp_tool['name'])
        self._clean_up_funcs.insert(0, partial(db.delete_dna_plate, obs[0]))
        after = datetime.datetime.now()
        self.assertEqual(len(obs), 1)
        obs_info = db.read_dna_plate(obs[0])
        obs_created = obs_info.pop('created_on')
        self.assertTrue(before <= obs_created <= after)
        exp = {'id': obs[0], 'name': 'Test plate', 'email': 'test',
               'sample_plate_id': plate_id,
               'extraction_robot': exp_robot['name'],
               'extraction_kit_lot': exp_kit['name'],
               'extraction_tool': exp_tool['name'],
               'notes': None}
        self.assertEqual(obs_info, exp)

    def test_read_dna_plate(self):
        # Success is already tested in "test_extract_sample_plates"
        with self.assertRaises(ValueError) as ctx:
            db.read_dna_plate(0)
        self.assertEqual(ctx.exception.message, "DNA plate 0 does not exist")

    def test_delete_dna_plate(self):
        # Success is already tested in "test_extract_sample_plates" cleanup
        with self.assertRaises(ValueError) as ctx:
            db.delete_dna_plate(0)
        self.assertEqual(ctx.exception.message, "DNA plate 0 does not exist")

    def test_get_dna_plate_list(self):
        self.assertEqual(db.get_dna_plate_list(), [])

        # Create a study
        db.create_study(9999, title='LabAdmin test project', alias='LTP',
                        jira_id='KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))
        # Create a sample plate
        pt = db.get_plate_types()[0]
        plate_id = db.create_sample_plate('Test plate', pt['id'],
                                          'test', [9999])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id))

        # Create a dna plate
        exp_robot = db.get_property_options("extraction_robot")[0]
        exp_kit = db.get_property_options("extraction_kit_lot")[0]
        exp_tool = db.get_property_options("extraction_tool")[0]
        obs = db.extract_sample_plates(
            [plate_id], 'test', exp_robot['name'], exp_kit['name'],
            exp_tool['name'])
        self._clean_up_funcs.insert(0, partial(db.delete_dna_plate, obs[0]))

        exp = [{'id': obs[0], 'name': 'Test plate',
                'date': datetime.date.today()}]
        self.assertEqual(db.get_dna_plate_list(), exp)

    def test_get_targeted_primer_plates(self):
        exp = [{'id': 1, 'name': 'Primer plate 1', 'notes': None,
                'linker_primer_sequence': 'GTGTGCCAGCMGCCGCGGTAA',
                'target_gene': '16S', 'target_subfragment': 'V4'},
               {'id': 2, 'name': 'Primer plate 2', 'notes': None,
                'linker_primer_sequence': 'GTGTGCCAGCMGCCGCGGTAA',
                'target_gene': '16S', 'target_subfragment': 'V4'},
               {'id': 3, 'name': 'Primer plate 3', 'notes': None,
                'linker_primer_sequence': 'GTGTGCCAGCMGCCGCGGTAA',
                'target_gene': '16S', 'target_subfragment': 'V4'},
               {'id': 4, 'name': 'Primer plate 4', 'notes': None,
                'linker_primer_sequence': 'GTGTGCCAGCMGCCGCGGTAA',
                'target_gene': '16S', 'target_subfragment': 'V4'},
               {'id': 5, 'name': 'Primer plate 5', 'notes': None,
                'linker_primer_sequence': 'GTGTGCCAGCMGCCGCGGTAA',
                'target_gene': '16S', 'target_subfragment': 'V4'},
               {'id': 6, 'name': 'Primer plate 6', 'notes': None,
                'linker_primer_sequence': 'GTGTGCCAGCMGCCGCGGTAA',
                'target_gene': '16S', 'target_subfragment': 'V4'},
               {'id': 7, 'name': 'Primer plate 7', 'notes': None,
                'linker_primer_sequence': 'GTGTGCCAGCMGCCGCGGTAA',
                'target_gene': '16S', 'target_subfragment': 'V4'},
               {'id': 8, 'name': 'Primer plate 8', 'notes': None,
                'linker_primer_sequence': 'GTGTGCCAGCMGCCGCGGTAA',
                'target_gene': '16S', 'target_subfragment': 'V4'}]
        self.assertEqual(db.get_targeted_primer_plates(), exp)

    def test_prepare_targeted_libraries(self):
        # Create a study
        db.create_study(9999, title='LabAdmin test project', alias='LTP',
                        jira_id='KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))

        # Create some sample plates
        pt = db.get_plate_types()[0]
        plate_id = db.create_sample_plate('Test plate', pt['id'], 'test',
                                          [9999])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id))
        plate_id_2 = db.create_sample_plate('Test plate 2', pt['id'], 'test',
                                            [9999])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id_2))

        # Create DNA plates
        dna_plate_ids = db.extract_sample_plates(
            [plate_id, plate_id_2], 'test', 'HOWE_KF1', 'PM16B11', '108379Z')
        for p_id in dna_plate_ids:
            self._clean_up_funcs.insert(
                0, partial(db.delete_dna_plate, p_id))

        # Create the target gene plates
        plate_links = [
            {'dna_plate_id': dna_plate_ids[0], 'primer_plate_id': 1},
            {'dna_plate_id': dna_plate_ids[1], 'primer_plate_id': 2}]
        before = datetime.datetime.now()
        obs_ids = db.prepare_targeted_libraries(
            plate_links, 'test', 'ROBE', '208484Z', '108364Z', '14459',
            'RNBD9959')
        after = datetime.datetime.now()

        for o_id in obs_ids:
            self._clean_up_funcs.insert(
                0, partial(db.delete_targeted_plate, o_id))

        self.assertEqual(len(obs_ids), 2)
        exp = [
            {'id': obs_ids[0], 'name': 'Test plate', 'email': 'test',
             'dna_plate_id': dna_plate_ids[0], 'primer_plate_id': 1,
             'master_mix_lot': '14459', 'robot': 'ROBE',
             'tm300_8_tool': '208484Z', 'tm50_8_tool': '108364Z',
             'water_lot': 'RNBD9959'},
            {'id': obs_ids[1], 'name': 'Test plate 2', 'email': 'test',
             'dna_plate_id': dna_plate_ids[1], 'primer_plate_id': 2,
             'master_mix_lot': '14459', 'robot': 'ROBE',
             'tm300_8_tool': '208484Z', 'tm50_8_tool': '108364Z',
             'water_lot': 'RNBD9959'}]
        for obs_id, exp in zip(obs_ids, exp):
            obs = db.read_targeted_plate(obs_id)
            self.assertTrue(before <= obs.pop('created_on') <= after)
            self.assertEqual(obs, exp)

    def test_read_targeted_plate(self):
        # Success is already tested in "test_prepare_targeted_libraries"
        with self.assertRaises(ValueError) as ctx:
            db.read_targeted_plate(0)
        self.assertEqual(ctx.exception.message,
                         "Target Gene plate 0 does not exist")

    def test_delete_targeted_plate(self):
        # Success is already tested in "test_prepare_targeted_libraries"
        with self.assertRaises(ValueError) as ctx:
            db.delete_targeted_plate(0)
        self.assertEqual(ctx.exception.message,
                         "Target Gene plate 0 does not exist")

    def test_get_targeted_plate_list(self):
        targeted_plate_ids = self._create_test_data_targeted_plate()

        exp = [{'id': targeted_plate_ids[0], 'name': 'Test plate',
                'date': datetime.date.today(), 'num_samples': 3},
               {'id': targeted_plate_ids[1], 'name': 'Test plate 2',
                'date': datetime.date.today(), 'num_samples': 4}]
        self.assertEqual(db.get_targeted_plate_list(), exp)

    def test_pool_plates(self):
        targeted_plate_ids = self._create_test_data_targeted_plate()

        # Pool samples
        pools = [
            {'targeted_plate_id': targeted_plate_ids[0], 'volume': 240,
             'percentage': 50},
            {'targeted_plate_id': targeted_plate_ids[1], 'volume': 240,
             'percentage': 50}]
        pool_id = db.pool_plates(pools, 'LabAdmin test pool', 5)
        self._clean_up_funcs.insert(0, partial(db.delete_pool, pool_id))
        obs = db.read_pool(pool_id)
        exp = {'id': pool_id, 'name': 'LabAdmin test pool',
               'volume': 5, 'notes': None,
               'targeted_pools': [
                {'name': 'Test plate', 'volume': 240, 'percentage': 50,
                 'targeted_plate_id': targeted_plate_ids[0]},
                {'name': 'Test plate 2', 'volume': 240, 'percentage': 50,
                 'targeted_plate_id': targeted_plate_ids[1]}]}

        self.assertAlmostEqual(obs.pop('volume'), exp.pop('volume'))
        for o, e in zip(obs['targeted_pools'], exp['targeted_pools']):
            # Remove the id from the targeted pools since it will different
            # in every run
            o.pop('id')
            self.assertAlmostEqual(o.pop('volume'), e.pop('volume'))
            self.assertAlmostEqual(o.pop('percentage'), e.pop('percentage'))
            self.assertEqual(o, e)

        with self.assertRaises(ValueError) as ctx:
            pool_id = db.pool_plates([], 'LabAdmin test pool', 5)
        self.assertEqual(ctx.exception.message,
                         "Provide at least on plate to pool.")

    def test_read_pool(self):
        # Success is already tested in "test_pool_plates"
        with self.assertRaises(ValueError) as ctx:
            db.read_pool(0)
        self.assertEqual(ctx.exception.message, "Pool 0 does not exist")

    def test_delete_pool(self):
        # Success is already tested in "test_pool_plates"
        with self.assertRaises(ValueError) as ctx:
            db.delete_pool(0)
        self.assertEqual(ctx.exception.message, "Pool 0 does not exist")


if __name__ == "__main__":
    main()

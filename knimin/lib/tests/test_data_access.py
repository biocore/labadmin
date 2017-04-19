from unittest import TestCase, main
from os.path import join, dirname, realpath
from six import StringIO
from functools import partial
from traceback import format_exc
from copy import deepcopy
import datetime
from random import choice

import pandas as pd
import numpy.testing as npt
import numpy as np

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

        # reseting DB, iTru is 3
        sql = """UPDATE pm.shotgun_index_tech
                 SET last_index_idx = 0
                 WHERE shotgun_index_tech_id = 3"""
        db._con.execute(sql)

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

    def _create_test_data_pool(self):
        targeted_plate_ids = self._create_test_data_targeted_plate()

        # Pool samples
        pools = [
            {'targeted_plate_id': targeted_plate_ids[0], 'volume': 240,
             'percentage': 100}]
        pool_id = db.pool_plates(pools, 'LabAdmin test pool', 5)
        pools = [
            {'targeted_plate_id': targeted_plate_ids[1], 'volume': 240,
             'percentage': 100}]
        pool_id_2 = db.pool_plates(pools, 'LabAdmin test pool 2', 5)
        self._clean_up_funcs.insert(0, partial(db.delete_pool, pool_id))
        self._clean_up_funcs.insert(0, partial(db.delete_pool, pool_id_2))

        return [pool_id, pool_id_2]

    def _create_test_echo(self):
        echo_id = db.get_or_create_property_option_id('echo',
                                                      'a valid echo name')
        f = partial(db.delete_property_option, 'echo', echo_id)
        self._clean_up_funcs.append(f)

    def _create_test_shotgun_plate(self):
        # study creation
        db.create_study(9999, title='LabAdmin test project',
                        alias='LTP', jira_id='KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))

        # plates creation
        dna_plates = []
        exp_robot = db.get_property_options("extraction_robot")[0]
        exp_kit = db.get_property_options("extraction_kit_lot")[0]
        exp_tool = db.get_property_options("extraction_tool")[0]
        for i in range(4):
            pid = db.create_sample_plate('Test %s' % i, 2, 'test', [9999])
            self._clean_up_funcs.insert(
                0, partial(db.delete_sample_plate, pid))

            dp_pid = db.extract_sample_plates(
                [pid], 'test', exp_robot['name'], exp_kit['name'],
                exp_tool['name'])[0]
            self._clean_up_funcs.insert(
                0, partial(db.delete_dna_plate, dp_pid))
            dna_plates.append((dp_pid, i))

        email = 'test'
        name = "full plate"
        robot = 'HOWE_KF1'
        plate_type = 2L
        volume = 0.22
        cid = db.condense_dna_plates(dna_plates, name, email,
                                     robot, plate_type, volume)
        self._clean_up_funcs.insert(0, partial(db.delete_shotgun_plate, cid))
        return cid

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
    def test_get_blanks(self):
        obs = db.get_blanks()
        self.assertItemsEqual(obs, ['BLANK', 'SWAB', 'PCRCONTROL'])

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

    def test_get_blanks_from_sample_plate(self):
        # Create a study
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

        # plate some samples
        layout = [[{}] * pt['cols']] * pt['rows']
        # Set the first column and 3rd column to be all blanks. Is a bit subtle
        # but this is happening because in all the rows we have the same list
        # given how we have constructed the layout
        layout[0][0] = {'sample_id': 'BLANK'}
        layout[0][1] = {'sample_id': '9999.Sample_1'}
        layout[0][2] = {'sample_id': '9999.Sample_2'}
        layout[0][3] = {'sample_id': 'BLANK'}
        db.write_sample_plate_layout(plate_id, layout)

        obs = db.get_blanks_from_sample_plate(plate_id)
        exp = [['BLANK', 0, 0], ['BLANK', 0, 3],
               ['BLANK', 1, 0], ['BLANK', 1, 3],
               ['BLANK', 2, 0], ['BLANK', 2, 3],
               ['BLANK', 3, 0], ['BLANK', 3, 3],
               ['BLANK', 4, 0], ['BLANK', 4, 3],
               ['BLANK', 5, 0], ['BLANK', 5, 3],
               ['BLANK', 6, 0], ['BLANK', 6, 3],
               ['BLANK', 7, 0], ['BLANK', 7, 3]]
        self.assertEqual(obs, exp)

    def test_get_replicates_from_sample_plate(self):
        # Create two study
        db.create_study(9999, title='LabAdmin test project',
                        alias='LTP', jira_id='KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))
        db.create_study(9998, title='LabAdmin test project 2', alias='LTP',
                        jira_id='KL9998')
        self._clean_up_funcs.append(partial(db.delete_study, 9998))

        # Add samples to the studies
        samples = ['9999.Sample_1', '9999.Sample_2', '9999.Sample_3']
        db.set_study_samples(9999, samples)
        samples = ['9998.Sample_1', '9998.Sample_2', '9998.Sample_3']
        db.set_study_samples(9998, samples)

        # Create a plate
        pt = db.get_plate_types()[0]
        plate_id = db.create_sample_plate('Test plate', pt['id'],
                                          'test', [9999, 9998])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id))

        # plate some samples
        layout = [[{}] * pt['cols']] * pt['rows']
        # Set the first column and 3rd column to be all blanks. Is a bit subtle
        # but this is happening because in all the rows we have the same list
        # given how we have constructed the layout. Similarly, the second
        # column has the sample sample in all rows
        layout[0][0] = {'sample_id': 'BLANK'}
        layout[0][1] = {'sample_id': '9999.Sample_1'}
        layout[0][2] = {'sample_id': '9999.Sample_2'}
        layout[0][3] = {'sample_id': 'BLANK'}
        layout[0][4] = {'sample_id': '9998.Sample_1'}
        layout[0][5] = {'sample_id': '9998.Sample_2'}
        layout[1] = [{}] * pt['cols']
        layout[1][6] = {'sample_id': '9998.Sample_3'}
        db.write_sample_plate_layout(plate_id, layout)

        obs = db.get_replicates_from_sample_plate(plate_id)
        exp = {'9999.Sample_1': [(0, 1), (2, 1), (3, 1), (4, 1),
                                 (5, 1), (6, 1), (7, 1)],
               '9999.Sample_2': [(0, 2), (2, 2), (3, 2), (4, 2),
                                 (5, 2), (6, 2), (7, 2)],
               '9998.Sample_1': [(0, 4), (2, 4), (3, 4), (4, 4),
                                 (5, 4), (6, 4), (7, 4)],
               '9998.Sample_2': [(0, 5), (2, 5), (3, 5), (4, 5),
                                 (5, 5), (6, 5), (7, 5)]}
        # This tests that the keys are the same
        self.assertItemsEqual(obs, exp)
        for sample in exp:
            self.assertItemsEqual(obs[sample], exp[sample])

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

    def test_read_sample(self):
        # Create a study
        db.create_study(9999, title='LabAdmin test project',
                        alias='LTP', jira_id='KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))
        samples = ['9999.Sample_1', '9999.Sample_2', '9999.Sample_3']
        db.set_study_samples(9999, samples)

        exp = {'sample_id': '9999.Sample_1', 'is_blank': False,
               'details': None, 'study_id': 9999}
        self.assertEqual(db.read_sample('9999.Sample_1'), exp)
        exp = {'sample_id': 'BLANK', 'is_blank': True,
               'details': None, 'study_id': None}
        self.assertEqual(db.read_sample('BLANK'), exp)

        # Attempt to read a leayout of a plate that doesn't exist
        with self.assertRaises(ValueError) as ctx:
            db.read_sample('NOTASAMPLE')
        self.assertEqual(ctx.exception.message,
                         "Sample NOTASAMPLE does not exist")

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
                'cols': 12, 'rows': 8},
               {'id': 2, 'name': '384-well',
                'notes': 'Standard 384-well plate',
                'cols': 24, 'rows': 16}]
        self.assertItemsEqual(obs, exp)

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

    def test_normalize_shotgun_plate_bad_id(self):
        with self.assertRaisesRegexp(ValueError, "shotgun plate"):
            db.normalize_shotgun_plate(99999999, 'test', 'a valid echo name',
                                       np.zeros((16, 24)), np.zeros((16, 24)))

    def test_normalize_shotgun_plate_bad_water_shape(self):
        # this test assumes that the plate is a 384 well format, so we'll
        # specify a water matrix in 96 well format
        self._create_test_echo()
        cid = self._create_test_shotgun_plate()
        with self.assertRaisesRegexp(ValueError, "plate_normalization_water"):
            db.normalize_shotgun_plate(cid, 'test', 'a valid echo name',
                                       np.zeros((16, 24)), np.zeros((8, 12)))

    def test_normalize_shotgun_plate_bad_sample_shape(self):
        # this test assumes that the plate is a 384 well format, so we'll
        # specify a sample matrix in 96 well format
        self._create_test_echo()
        cid = self._create_test_shotgun_plate()
        with self.assertRaisesRegexp(ValueError, "plate_normalization_sample"):
            db.normalize_shotgun_plate(cid, 'test', 'a valid echo name',
                                       np.zeros((8, 12)), np.zeros((16, 24)))

    def test_normalize_shotgun_plate_bad_echo_name(self):
        cid = self._create_test_shotgun_plate()
        with self.assertRaisesRegexp(ValueError, "echo machine"):
            db.normalize_shotgun_plate(cid, 'test', 'does not exist',
                                       np.zeros((16, 24)), np.zeros((16, 24)))

    def _basic_test_steps_for_normalized_shotgun_plate(self, before, after,
                                                       obs, exp_rnsp):
        "helper function to avoid duplication"
        self.assertEqual(set(obs.keys()), set(exp_rnsp.keys()))
        self.assertTrue(before <= obs.pop('created_on') <= after)
        npt.assert_almost_equal(obs['plate_normalization_water'],
                                exp_rnsp['plate_normalization_water'],
                                decimal=5)
        npt.assert_almost_equal(obs['plate_normalization_sample'],
                                exp_rnsp['plate_normalization_sample'],
                                decimal=5)
        if exp_rnsp['plate_qpcr_concentrations'] is None:
            self.assertIsNone(obs['plate_qpcr_concentrations'])
        else:
            npt.assert_almost_equal(obs['plate_qpcr_concentrations'],
                                    exp_rnsp['plate_qpcr_concentrations'],
                                    decimal=5)
        if exp_rnsp['plate_qpcr_cps'] is None:
            self.assertIsNone(obs['plate_qpcr_cps'])
        else:
            npt.assert_almost_equal(obs['plate_qpcr_cps'],
                                    exp_rnsp['plate_qpcr_cps'], decimal=5)
        for k in set(obs.keys()) - set(['plate_normalization_water',
                                        'created_on',
                                        'plate_qpcr_concentrations',
                                        'plate_qpcr_cps',
                                        'plate_normalization_sample']):

            self.assertEqual(obs[k], exp_rnsp[k])

    def test_generate_i5_i7_indexes(self):
        # these tests will depend on what's in the db, which are added
        # just below -- Add shotgun_index valid values

        # generate 10 and check the values are just fine
        obs = db.generate_i5_i7_indexes('iTru', 10)
        exp = [1L, 2L, 3L, 4L, 5L, 6L, 7L, 8L, 9L, 10L]
        self.assertEqual(obs, exp)

        # ask for another 10 and make sure it starts where it should be
        obs = db.generate_i5_i7_indexes('iTru', 10)
        exp = [11L, 12L, 13L, 14L, 15L, 16L, 17L, 18L, 19L, 20L]
        self.assertEqual(obs, exp)

        # test that we reset index correctly
        # iTru is 3 and we have 1360 valid barcodes
        sql = """UPDATE pm.shotgun_index_tech
                 SET last_index_idx = 1358
                 WHERE shotgun_index_tech_id = 3"""
        db._con.execute(sql)

        obs = db.generate_i5_i7_indexes('iTru', 10)
        exp = [1359L, 1360L, 1L, 2L, 3L, 4L, 5L, 6L, 7L, 8L]
        self.assertEqual(obs, exp)

        # testing errors

        with self.assertRaises(ValueError) as ctx:
            db.generate_i5_i7_indexes('Should Error', 10)
        self.assertEqual(
            ctx.exception.message, "Not a valid shotgun index technology: "
            "Should Error")

        with self.assertRaises(ValueError) as ctx:
            db.generate_i5_i7_indexes('BiooNEXTflex-HT', 10)
        self.assertEqual(ctx.exception.message,
                         "'BiooNEXTflex-HT' doesn't have any barcodes")

    def test_get_shotgun_index_information(self):
        obs = db.get_shotgun_index_information(100)
        exp = {'shotgun_index_id': 100L, 'i7_row': 3, 'name': 'iTru',
               'i7_bases': 'TCGGTTAC', 'i7_name': 'iTru7_109_04',
               'i5_i7_sameplate': False, 'last_index_idx': 0,
               'dual_index': True, 'i5_name': 'iTru5_01_F', 'i7_col': 21,
               'i5_row': 5, 'i5_bases': 'GTGAGACT', 'i5_col': 0}
        self.assertEqual(obs, exp)

        # testing errors

        with self.assertRaises(ValueError) as ctx:
            db.get_shotgun_index_information(100000000000000)
        self.assertEqual(ctx.exception.message,
                         "100000000000000 shotgun_index_id doesn't exist")

    def test_normalize_shotgun_plate(self):
        before = datetime.datetime.now()
        self._create_test_echo()
        cid = self._create_test_shotgun_plate()
        email = 'test'
        nid = db.normalize_shotgun_plate(cid, email, 'a valid echo name',
                                         np.arange(384).reshape(16, 24),
                                         np.arange(384).reshape(16, 24) * 10)
        after = datetime.datetime.now()
        exp_sample = np.arange(384).reshape(16, 24)
        exp_water = np.arange(384).reshape(16, 24) * 10
        exp_qpcr_con = np.zeros((16, 24))
        exp_qpcr_cp = np.zeros((16, 24))
        exp_qpcr_con = None
        exp_qpcr_cp = None
        shotgun_index = None

        exp_rnsp = {'created_on': datetime.date.today(),
                    'email': email,
                    'echo': 'a valid echo name',
                    'lp_date': None,
                    'lp_email': None,
                    'mosquito': None,
                    'shotgun_plate_id': cid,
                    'shotgun_normalized_plate_id': nid,
                    'shotgun_library_prep_kit': None,
                    'shotgun_adapter_aliquot': None,
                    'qpcr_date': None,
                    'qpcr_email': None,
                    'qpcr_std_ladder': None,
                    'qpcr': None,
                    'shotgun_index': shotgun_index,
                    'discarded': False,
                    'plate_normalization_water': exp_water,
                    'plate_normalization_sample': exp_sample,
                    'plate_qpcr_concentrations': exp_qpcr_con,
                    'plate_qpcr_cps': exp_qpcr_cp}

        obs = db.read_normalized_shotgun_plate(nid)
        self._basic_test_steps_for_normalized_shotgun_plate(
            before, after, obs, exp_rnsp)

        # tests for prepare_shotgun_libraries
        # the mosquito values are set 1: Mosquito1
        mosquito = 'Mosquito1'
        mosquito_id = 1
        shotgun_library_prep_kit = 'new library_prep_kit'
        # as we need to insert a new index aliquot for testing, let's also
        # test the retrival
        shotgun_index_aliquot_id = db.add_shotgun_index_aliquot(
            'new index_aliquot_id', 'This is our newest index aliquot', 100)
        self._clean_up_funcs.append(
            partial(db.delete_shotgun_index_aliquot, shotgun_index_aliquot_id))
        obs = db.read_shotgun_index_aliquot()
        exp = [{'notes': 'This is our newest index aliquot',
                'shotgun_index_aliquot_id': shotgun_index_aliquot_id,
                'name': 'new index_aliquot_id',
                'limit_freeze_thaw_cycles': 100L}]
        self.assertEqual(obs, exp)

        _ids = range(1, 10)
        barcode_layout = [[choice(_ids) for c in range(24)] for r in range(16)]
        db.prepare_shotgun_libraries(
            nid, email, mosquito, shotgun_library_prep_kit,
            shotgun_index_aliquot_id, barcode_layout)
        obs = db.read_normalized_shotgun_plate(nid)
        exp_rnsp['mosquito'] = mosquito_id
        exp_rnsp['shotgun_library_prep_kit'] = shotgun_library_prep_kit
        exp_rnsp['shotgun_index'] = barcode_layout
        self._basic_test_steps_for_normalized_shotgun_plate(
            before, after, obs, exp_rnsp)

        # testing errors for prepare_shotgun_libraries
        barcode_layout = np.random.rand(7, 7)
        with self.assertRaises(ValueError) as ctx:
            db.prepare_shotgun_libraries(
                nid, email, mosquito, shotgun_library_prep_kit,
                shotgun_index_aliquot_id, barcode_layout)
        self.assertEqual(
            ctx.exception.message, "barcode_layout wrong shape, should be: "
            "(16, 24) but is: (7, 7)")

        # tests for qpcr_shotgun
        # [0] only one result and [name] we just want the name
        qpcr = db.get_property_options("qpcr")[0]['name']
        qpcr_ladder = 'This is my ladder text'
        qpcr_cp_values = np.random.rand(16, 24)
        qpcr_lib_concentration_values = np.random.rand(16, 24)
        db.qpcr_shotgun(nid, email, qpcr, qpcr_ladder, qpcr_cp_values,
                        qpcr_lib_concentration_values)
        obs = db.read_normalized_shotgun_plate(nid)
        exp_rnsp['qpcr'] = qpcr
        exp_rnsp['qpcr_std_ladder'] = qpcr_ladder
        exp_rnsp['plate_qpcr_cps'] = qpcr_cp_values
        exp_rnsp['plate_qpcr_concentrations'] = qpcr_lib_concentration_values
        self._basic_test_steps_for_normalized_shotgun_plate(
            before, after, obs, exp_rnsp)

        # testing errors for qpcr_shotgun
        qpcr_lib_concentration_values = np.random.rand(8, 12)
        with self.assertRaises(ValueError) as ctx:
            db.qpcr_shotgun(nid, email, qpcr, qpcr_ladder, qpcr_cp_values,
                            qpcr_lib_concentration_values)
        self.assertEqual(
            ctx.exception.message, "qpcr_lib_concentration_values wrong "
            "shape, should be: (16, 24) but is: (8, 12)")
        qpcr_cp_values = np.random.rand(8, 12)
        with self.assertRaises(ValueError) as ctx:
            db.qpcr_shotgun(nid, email, qpcr, qpcr_ladder, qpcr_cp_values,
                            qpcr_lib_concentration_values)
        self.assertEqual(
            ctx.exception.message, "qpcr_cp_values wrong "
            "shape, should be: (16, 24) but is: (8, 12)")

    def test_add_shotgun_adaptor_aliquot(self):
        "testing here as we don't have an specific pipeline to test in"
        shotgun_index_adaptor_id = db.add_shotgun_adapter_aliquot(
            'new adaptor_aliquot_id', 'This is our newest adaptor aliquot', 10)
        self._clean_up_funcs.append(partial(
            db.delete_shotgun_adapter_aliquot, shotgun_index_adaptor_id))
        obs = db.read_shotgun_adapter_aliquot()
        exp = [{'notes': 'This is our newest adaptor aliquot',
                'shotgun_adapter_aliquot_id': shotgun_index_adaptor_id,
                'name': 'new adaptor_aliquot_id',
                'limit_freeze_thaw_cycles': 10}]
        self.assertEqual(obs, exp)

    def test_read_normalized_shotgun_plate_bad_id(self):
        with self.assertRaises(ValueError):
            db.read_normalized_shotgun_plate(99999999)

    def test_delete_normalized_shotgun_plate_bad_id(self):
        with self.assertRaises(ValueError):
            db.delete_normalized_shotgun_plate(99999999)

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
             'raw_concentration': None, 'mod_concentration': None,
             'water_lot': 'RNBD9959'},
            {'id': obs_ids[1], 'name': 'Test plate 2', 'email': 'test',
             'dna_plate_id': dna_plate_ids[1], 'primer_plate_id': 2,
             'master_mix_lot': '14459', 'robot': 'ROBE',
             'tm300_8_tool': '208484Z', 'tm50_8_tool': '108364Z',
             'raw_concentration': None, 'mod_concentration': None,
             'water_lot': 'RNBD9959'}]
        for obs_id, exp in zip(obs_ids, exp):
            obs = db.read_targeted_plate(obs_id)
            self.assertTrue(before <= obs.pop('created_on') <= after)
            for k in obs:
                self.assertEqual(obs[k], exp[k])
            self.assertEqual(obs, exp)

        # testing quantify_targeted_plate on only one of the plates
        pid = obs_ids[0]
        vals = np.random.rand(8, 12)
        # this shouldn't change anything as raw_concentration should be first
        db.quantify_targeted_plate(pid, 'mod_concentration', vals)
        obs = db.read_targeted_plate(pid)
        self.assertIsNone(obs['raw_concentration'])
        self.assertIsNone(obs['mod_concentration'])
        # this should change only raw_concentration
        db.quantify_targeted_plate(pid, 'raw_concentration', vals)
        obs = db.read_targeted_plate(pid)
        npt.assert_almost_equal(obs['raw_concentration'], vals, decimal=5)
        self.assertIsNone(obs['mod_concentration'])
        # now changing mod_concentration
        vals_mod = np.random.rand(8, 12)
        db.quantify_targeted_plate(pid, 'mod_concentration', vals_mod)
        obs = db.read_targeted_plate(pid)
        npt.assert_almost_equal(obs['raw_concentration'], vals, decimal=5)
        npt.assert_almost_equal(obs['mod_concentration'], vals_mod, decimal=5)

        # testing errors
        with self.assertRaises(ValueError) as ctx:
            db.quantify_targeted_plate(obs_ids[0], 'should fail', vals)
        self.assertEqual(
            ctx.exception.message, "Not valid data value: should fail, should "
            "be: [u'raw_concentration', u'mod_concentration']")

        vals = np.random.rand(16, 24)
        with self.assertRaises(ValueError) as ctx:
            db.quantify_targeted_plate(obs_ids[0], 'raw_concentration', vals)
        self.assertEqual(
            ctx.exception.message, 'values wrong shape, should be: (8, 12) '
            'but is: (16, 24)')

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
        self.assertItemsEqual(db.get_targeted_plate_list(), exp)

    def test_get_quantified_targeted_plate_list(self):
        targeted_plate_ids = self._create_test_data_targeted_plate()
        self.assertItemsEqual(db.get_quantified_targeted_plate_list(), [])

        vals = np.zeros((8, 12))
        db.quantify_targeted_plate(targeted_plate_ids[0],
                                   'raw_concentration', vals)
        db.quantify_targeted_plate(targeted_plate_ids[0],
                                   'mod_concentration', vals)
        vals[0][0] = 1.0
        vals[0][1] = 2.0
        vals[0][2] = 0.001
        db.quantify_targeted_plate(targeted_plate_ids[1],
                                   'raw_concentration', vals)
        db.quantify_targeted_plate(targeted_plate_ids[1],
                                   'mod_concentration', vals)

        exp = [{'id': targeted_plate_ids[1], 'name': 'Test plate 2',
                'date': datetime.date.today(), 'num_samples': 3}]
        self.assertItemsEqual(db.get_quantified_targeted_plate_list(), exp)

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

    def _generate_condense_dna_plates(self, just_one_plate=False):
        # study creation
        study_id = 9999
        db.create_study(study_id, title='LabAdmin test project',
                        alias='LTP', jira_id='KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, study_id))

        # plates creation
        dna_plates = []
        exp_robot = db.get_property_options("extraction_robot")[0]
        exp_kit = db.get_property_options("extraction_kit_lot")[0]
        exp_tool = db.get_property_options("extraction_tool")[0]
        samples = []
        pids = []
        # gonna create the 4 color plates
        for i, color in enumerate(['b', 'r', 'y', 'g']):
            pid = db.create_sample_plate('Test %s' % color, 1, 'test',
                                         [study_id])
            self._clean_up_funcs.insert(
                0, partial(db.delete_sample_plate, pid))
            layout = []
            for r in range(8):
                row = []
                for c in range(12):
                    # creating sample names
                    sample = '%d.%s.%s.%s' % (study_id, color, r, c)
                    samples.append(sample)
                    row.append({'sample_id': sample, 'name': None,
                                'notes': None})
                layout.append(row)
            db.set_study_samples(study_id, samples)
            db.write_sample_plate_layout(pid, layout)
            pids.append(pid)

        # creating dna plates
        plate_to_use = 2
        if just_one_plate:
            pids = [pids[plate_to_use]]

        pid_plates = db.extract_sample_plates(
            pids, 'test', exp_robot['name'], exp_kit['name'],
            exp_tool['name'])

        # formating dna_plates for the next step
        dna_plates = []
        for i, v in enumerate(pid_plates):
            self._clean_up_funcs.insert(
                0, partial(db.delete_dna_plate, v))
            dna_plates.append((v, i))

        if just_one_plate:
            # it's always the only one [0]
            dna_plates = [(pid_plates[0], plate_to_use)]

        email = 'test'
        name = "full plate"
        robot = 'ROBE'
        plate_type = 2L
        volume = 0.22
        cid = db.condense_dna_plates(dna_plates, name, email,
                                     robot, plate_type, volume)
        self._clean_up_funcs.insert(0, partial(db.delete_shotgun_plate, cid))

        return cid, dna_plates

    def test_condense_dna_plates(self):
        cid, dna_plates = self._generate_condense_dna_plates()
        obs = db.read_shotgun_plate(cid)
        # not testing time to avoid problems
        del obs['created_on']
        # just testing dna_plates
        self.assertItemsEqual(obs['condensed_plates'], dna_plates)
        del obs['condensed_plates']
        exp = {
            'plate_type_id': 2L, 'dna_q_volume': None, 'name': "full plate",
            'robot': 'ROBE', 'dna_q_mail': None, 'volume': 0.22,
            'plate_reader_id': None, 'email': 'test', 'dna_q_date': None,
            'id': cid, 'shotgun_plate_layout': [[{
                'sample_id': None, 'dna_concentration': None}
                for c in range(24)] for r in range(16)]}
        self.assertEqual(obs, exp)

    def test_condense_dna_plates_errors(self):
        # study creation
        db.create_study(9999, title='LabAdmin test project',
                        alias='LTP', jira_id='KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))

        # plates creation
        dna_plates = []
        exp_robot = db.get_property_options("extraction_robot")[0]
        exp_kit = db.get_property_options("extraction_kit_lot")[0]
        exp_tool = db.get_property_options("extraction_tool")[0]
        for i in range(4):
            pid = db.create_sample_plate('Test %s' % i, 2, 'test', [9999])
            self._clean_up_funcs.insert(
                0, partial(db.delete_sample_plate, pid))

            dp_pid = db.extract_sample_plates(
                [pid], 'test', exp_robot['name'], exp_kit['name'],
                exp_tool['name'])[0]
            self._clean_up_funcs.insert(
                0, partial(db.delete_dna_plate, dp_pid))
            dna_plates.append((dp_pid, i))

        email = 'test'
        name = "full plate"
        robot = 'HOWE_KF1'
        plate_type = 100
        volume = 0.22

        # error with plate_type
        with self.assertRaises(ValueError) as ctx:
            db.condense_dna_plates(dna_plates, name, email, robot, plate_type,
                                   volume)
        self.assertEqual(
            ctx.exception.message, "Plate type ID 100 does not exist.")

        # error with number of plates
        plate_type = 2
        dna_plates = []
        with self.assertRaises(ValueError) as ctx:
            db.condense_dna_plates(dna_plates, name, email, robot, plate_type,
                                   volume)
        self.assertEqual(
            ctx.exception.message,
            "You should have between 1 and 4 plates but you have 0")
        dna_plates = [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4)]
        with self.assertRaises(ValueError) as ctx:
            db.condense_dna_plates(dna_plates, name, email, robot, plate_type,
                                   volume)
        self.assertEqual(
            ctx.exception.message,
            "You should have between 1 and 4 plates but you have 5")

        # error dna plates positions/existance
        dna_plates = [(0, 10)]
        with self.assertRaises(ValueError) as ctx:
            db.condense_dna_plates(dna_plates, name, email, robot, plate_type,
                                   volume)
        self.assertEqual(
            ctx.exception.message,
            "Wrong dna plates position: [(0, 10)]")

    def test_read_shotgun_plate(self):
        # functional testing is part of test_condense_dna_plates, just testing
        # errors
        with self.assertRaises(ValueError) as ctx:
            db.read_shotgun_plate(100000)
        self.assertEqual(
            ctx.exception.message, "Shotgun Plate 100000 does not exist")

    def test_delete_shotgun_plate(self):
        # functional testing is part of test_condense_dna_plates, just testing
        # errors
        with self.assertRaises(ValueError) as ctx:
            db.delete_shotgun_plate(100000)
        self.assertEqual(
            ctx.exception.message, "Shotgun Plate 100000 does not exist")

    def test_quantify_shotgun_plate(self):
        sgp_id, dna_plates = self._generate_condense_dna_plates()
        email = 'test'
        volume = .002
        plate_reader = 'PR1234'
        plate_concentration = np.random.rand(16, 24)
        db.quantify_shotgun_plate(sgp_id, email, volume, plate_reader,
                                  plate_concentration)
        obs = db.read_shotgun_plate(sgp_id)
        # not testing time to avoid problems
        del obs['created_on']
        # just testing dna_plates
        self.assertItemsEqual(obs['condensed_plates'], dna_plates)
        del obs['condensed_plates']
        # testing layout, we only gonna check 10 specific values
        test_vals = [
            (5, 3, '9999.g.2.1'), (12, 10, '9999.b.6.5'),
            (11, 11, '9999.g.5.5'), (14, 5, '9999.r.7.2'),
            (10, 9, '9999.r.5.4'), (8, 8, '9999.b.4.4'),
            (5, 15, '9999.g.2.7'), (7, 0, '9999.y.3.0'),
            (12, 9, '9999.r.6.4'), (15, 4, '9999.y.7.2')]
        for r, c, sn in test_vals:
            to_test = obs['shotgun_plate_layout'][r][c]
            self.assertEqual(to_test['sample_id'], sn)
            npt.assert_almost_equal(
                to_test['dna_concentration'], plate_concentration[r, c],
                decimal=5)
        del obs['shotgun_plate_layout']
        exp = {
            'plate_type_id': 2L,
            'dna_q_volume': None,
            'name': 'full plate',
            'dna_q_mail': None,
            'robot': 'ROBE',
            'volume': 0.002,
            'plate_reader_id': 1L,
            'email': 'test',
            'dna_q_date': None,
            'id': sgp_id
        }
        self.assertEqual(obs, exp)

    def test_quantify_shotgun_plate_cond_concentration(self):
        # Test error
        sgp_id, dna_plates = self._generate_condense_dna_plates()
        email = 'test'
        volume = .002
        plate_reader = 'PR1234'
        with self.assertRaises(ValueError) as ctx:
            db.quantify_shotgun_plate(sgp_id, email, volume, plate_reader)
        self.assertEqual(
            ctx.exception.message,
            "Provide 'plate_concentration' or 'cond_plates_concentration'")

        # Test success
        cond_plates_concentration = [np.random.rand(8, 12) for i in range(4)]
        db.quantify_shotgun_plate(
            sgp_id, email, volume, plate_reader,
            cond_plates_concentration=cond_plates_concentration)
        obs = db.read_shotgun_plate(sgp_id)
        # not testing time to avoid problems
        del obs['created_on']
        # just testing dna_plates
        self.assertItemsEqual(obs['condensed_plates'], dna_plates)
        del obs['condensed_plates']
        # testing layout, we only gonna check 10 specific values
        for i, color in enumerate(['b', 'r', 'y', 'g']):
            pass
        test_vals = [
            (5, 3, '9999.g.2.1', cond_plates_concentration[3][2][1]),
            (12, 10, '9999.b.6.5', cond_plates_concentration[0][6][5]),
            (11, 11, '9999.g.5.5', cond_plates_concentration[3][5][5]),
            (14, 5, '9999.r.7.2', cond_plates_concentration[1][7][2]),
            (10, 9, '9999.r.5.4', cond_plates_concentration[1][5][4]),
            (8, 8, '9999.b.4.4', cond_plates_concentration[0][4][4]),
            (5, 15, '9999.g.2.7', cond_plates_concentration[3][2][7]),
            (7, 0, '9999.y.3.0', cond_plates_concentration[2][3][0]),
            (12, 9, '9999.r.6.4', cond_plates_concentration[1][6][4]),
            (15, 4, '9999.y.7.2', cond_plates_concentration[2][7][2])]
        for r, c, sn, conc in test_vals:
            to_test = obs['shotgun_plate_layout'][r][c]
            self.assertEqual(to_test['sample_id'], sn)
            npt.assert_almost_equal(
                to_test['dna_concentration'], conc,
                decimal=5)
        del obs['shotgun_plate_layout']
        exp = {
            'plate_type_id': 2L,
            'dna_q_volume': None,
            'name': 'full plate',
            'dna_q_mail': None,
            'robot': 'ROBE',
            'volume': 0.002,
            'plate_reader_id': 1L,
            'email': 'test',
            'dna_q_date': None,
            'id': sgp_id
        }
        self.assertEqual(obs, exp)

    def test_quantify_shotgun_plate_one_plate(self):
        sgp_id, dna_plates = self._generate_condense_dna_plates(True)
        email = 'test'
        volume = .002
        plate_reader = 'PR1234'
        plate_concentration = np.random.rand(16, 24)
        db.quantify_shotgun_plate(sgp_id, email, volume, plate_reader,
                                  plate_concentration)
        obs = db.read_shotgun_plate(sgp_id)
        # not testing time to avoid problems
        del obs['created_on']
        # just testing dna_plates
        self.assertItemsEqual(obs['condensed_plates'], dna_plates)
        del obs['condensed_plates']
        # testing layout, we only gonna check 10 specific values
        test_vals = [
            (5, 3, None), (12, 10, None),
            (11, 11, None), (14, 5, None),
            (10, 9, None), (8, 8, None),
            (5, 15, None), (7, 0, '9999.y.3.0'),
            (12, 9, None), (15, 4, '9999.y.7.2')]
        for r, c, sn in test_vals:
            to_test = obs['shotgun_plate_layout'][r][c]
            self.assertEqual(to_test['sample_id'], sn)
            if sn is not None:
                npt.assert_almost_equal(
                    to_test['dna_concentration'], plate_concentration[r, c],
                    decimal=5)
        del obs['shotgun_plate_layout']
        exp = {
            'plate_type_id': 2L,
            'dna_q_volume': None,
            'name': 'full plate',
            'dna_q_mail': None,
            'robot': 'ROBE',
            'volume': 0.002,
            'plate_reader_id': 1L,
            'email': 'test',
            'dna_q_date': None,
            'id': sgp_id
        }
        self.assertEqual(obs, exp)

    def test_get_pool_list(self):
        self.assertEqual(db.get_pool_list(), [])

        pool_ids = self._create_test_data_pool()
        exp = [{'id': pool_ids[0], 'name': 'LabAdmin test pool',
                'targeted_pools': ['Test plate']},
               {'id': pool_ids[1], 'name': 'LabAdmin test pool 2',
                'targeted_pools': ['Test plate 2']}]

        self.assertEqual(db.get_pool_list(), exp)

    def test_create_sequencing_run(self):
        pool_ids = self._create_test_data_pool()

        # Create the run
        before = datetime.datetime.now()
        run_id = db.create_sequencing_run(
            pool_ids[0], 'test', 'Knight Lab In house MiSeq',
            'MiSeq v3 150 cycle', 'MS1234',
            'Illumina', 'MiSeq', 'Kapa Hyper Plus', 151, 151)

        after = datetime.datetime.now()
        self._clean_up_funcs.insert(
            0, partial(db.delete_sequencing_run, run_id))

        obs = db.read_sequencing_run(run_id)
        self.assertTrue(before <= obs.pop('created_on') <= after)
        exp = {'id': run_id, 'name': 'LabAdmin test pool', 'notes': None,
               'sequencer': 'Knight Lab In house MiSeq',
               'pool_id': pool_ids[0],
               'platform': 'Illumina', 'instrument_model': 'MiSeq',
               'reagent_type': 'MiSeq v3 150 cycle',
               'reagent_lot': 'MS1234',
               'assay': 'Kapa Hyper Plus',
               'fwd_cycles': 151, 'rev_cycles': 151,
               'email': 'test'}
        self.assertEqual(obs, exp)

    def test_read_sequencing_run(self):
        # Success is already tested in "test_pool_plates"
        with self.assertRaises(ValueError) as ctx:
            db.read_sequencing_run(0)
        self.assertEqual(ctx.exception.message, 'Run 0 does not exist')

    def test_delete_sequencing_run(self):
        # Success is already tested in "test_pool_plates"
        with self.assertRaises(ValueError) as ctx:
            db.delete_sequencing_run(0)
        self.assertEqual(ctx.exception.message, 'Run 0 does not exist')

    def test_generate_prep_information(self):
        # Create a couple of studies
        db.create_study(9999, title='TEST TP1', alias='LTP1', jira_id='TM1')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))
        db.create_study(9998, title='TEST TP2', alias='LTP2', jira_id='TM2')
        self._clean_up_funcs.append(partial(db.delete_study, 9998))

        # Create some plates
        p_id = db.create_sample_plate('Plate 1', 1, 'test', [9999, 9998])
        self._clean_up_funcs.insert(0, partial(db.delete_sample_plate, p_id))
        p_id_2 = db.create_sample_plate('Plate 2', 1, 'test', [9999, 9998])
        self._clean_up_funcs.insert(0, partial(db.delete_sample_plate, p_id_2))

        # Add some samples to the studies
        samples1 = ['9999.Sample.%s' % i for i in range(12)]
        db.set_study_samples(9999, samples1)
        samples2 = ['9998.Sample.%s' % i for i in range(12)]
        db.set_study_samples(9998, samples2)

        # Create layouts
        well = {'sample_id': 'BLANK', 'name': None, 'notes': None}
        row = [deepcopy(well) for i in range(12)]
        layout = [deepcopy(row) for i in range(8)]
        layout2 = deepcopy(layout)
        for i in range(12):
            layout[0][i]['sample_id'] = samples1[i]
            layout[1][i]['sample_id'] = samples2[i]
        for i in range(8):
            layout2[i][0]['sample_id'] = samples1[i]
            layout2[i][1]['sample_id'] = samples2[i]
        db.write_sample_plate_layout(p_id, layout)
        db.write_sample_plate_layout(p_id_2, layout2)

        # Create DNA plates
        dna_plate_ids = db.extract_sample_plates(
            [p_id, p_id_2], 'test', 'HOWE_KF1', 'PM16B11', '108379ZZ')
        for i in dna_plate_ids:
            self._clean_up_funcs.insert(0, partial(db.delete_dna_plate, i))

        # Create the target gene plates
        plate_links = [
            {'dna_plate_id': dna_plate_ids[0], 'primer_plate_id': 1},
            {'dna_plate_id': dna_plate_ids[1], 'primer_plate_id': 2}]
        targeted_ids = db.prepare_targeted_libraries(
            plate_links, 'test', 'ROBE', '208484Z', '108364Z', '14459',
            'RNBD9959')
        for i in targeted_ids:
            self._clean_up_funcs.insert(
                0, partial(db.delete_targeted_plate, i))

        # Quantify the plate
        db.quantify_targeted_plate(
            targeted_ids[0], 'raw_concentration',
            np.random.uniform(125, 175, size=(8, 12)))
        db.quantify_targeted_plate(
            targeted_ids[1], 'raw_concentration',
            np.random.uniform(125, 175, size=(8, 12)))
        db.quantify_targeted_plate(
            targeted_ids[0], 'mod_concentration',
            np.random.uniform(4, 6, size=(8, 12)))
        db.quantify_targeted_plate(
            targeted_ids[1], 'mod_concentration',
            np.random.uniform(4, 6, size=(8, 12)))

        # Prepare the pools
        pools = [
            {'targeted_plate_id': targeted_ids[0], 'volume': 240,
             'percentage': 50},
            {'targeted_plate_id': targeted_ids[1], 'volume': 240,
             'percentage': 50}]
        pool_id = db.pool_plates(pools, 'TestPool', 5)
        self._clean_up_funcs.insert(0, partial(db.delete_pool, pool_id))

        # Create the sequencing run
        run_id = db.create_sequencing_run(
            pool_id, 'test', None, 'MiSeq v3 150 cycle', 'MS1234',
            'Illumina', 'MiSeq', 'TrueSeq HT', 151, 151)
        self._clean_up_funcs.insert(
            0, partial(db.delete_sequencing_run, run_id))

        # Generate the prep information
        preps = db.generate_prep_information(run_id)

        # There were 2 studies in this run, so we should get 2 preps
        self.assertEqual(len(preps), 2)

        # Check that we have the expected columns in both preps
        cols = ['sample_name', 'study_id', 'targeted_plate_name',
                'dna_plate_name', 'email', 'dna_plate_id', 'master_mix_lot',
                'robot', 'tm300_8_tool', 'tm50_8_tool', 'water_lot', 'row',
                'col', 'sample_plate_layout_notes', 'sample_details',
                'is_blank', 'primer', 'target_subfragment', 'target_gene',
                'barcode', 'extraction_robot_name', 'extraction_kit_lot_name',
                'extraction_tool_name', 'targeted_pool_volume',
                'sequencing_run_notes', 'sequencer', 'platform',
                'instrument_model', 'reagent_type', 'reagent_lot', 'assay',
                'fwd_cycles', 'rev_cycles', 'created_on', 'run_name']
        for prep in preps:
            self.assertItemsEqual(prep.columns, cols)

        # Check that in each prep we have a single study
        p0 = preps[0]
        p0_study_vals = set(p0.study_id.values)
        self.assertEqual(len(p0_study_vals), 1)
        p1 = preps[1]
        p1_study_vals = set(p1.study_id.values)
        self.assertEqual(len(p1_study_vals), 1)

        # Figure out which prep belongs to which study so we can check per
        # study values
        if '9999' in p0:
            study1_prep = p0
            study2_prep = p1
        else:
            study1_prep = p1
            study2_prep = p0

        s1_p1_bcds = ['AGCCTTCGTCGC', 'TCCATACCGGAA', 'AGCCCTGCTACA',
                      'CCTAACGGTCCA', 'CGCGCCTTAAAC', 'TATGGTACCCAG',
                      'TACAATATCTGT', 'AATTTAGGTAGG', 'GACTCAACCAGT',
                      'GCCTCTACGTCG', 'ACTACTGAGGAT', 'AATTCACCTCCT']
        s1_p2_bcds = ['CTACAGGGTCTC', 'GTTCATTAAACT', 'TTCGATGCCGCA',
                      'TCGTTATTCAGT', 'ACTCTGTAATTA', 'ATATGTTCTCAA',
                      'TCAGACCAACTG', 'TCATTAGCGTGG']
        # Magic number 8 -> the first 8 samples of this study where in 2
        # plates
        for idx, sample in enumerate(samples1[:8]):
            md_sample = study1_prep[study1_prep.sample_name == sample]
            self.assertEqual(len(md_sample), 2)

            md_sample_p1 = md_sample[md_sample.dna_plate_name == 'Plate 1']
            self.assertEqual(len(md_sample_p1), 1)
            self.assertEqual(md_sample_p1.barcode.iloc[0], s1_p1_bcds[idx])
            self.assertEqual(md_sample_p1.row.iloc[0], 1)
            self.assertEqual(md_sample_p1.col.iloc[0], idx + 1)

            md_sample_p2 = md_sample[md_sample.dna_plate_name == 'Plate 2']
            self.assertEqual(len(md_sample_p2), 1)
            self.assertEqual(md_sample_p2.barcode.iloc[0], s1_p2_bcds[idx])
            self.assertEqual(md_sample_p2.row.iloc[0], idx + 1)
            self.assertEqual(md_sample_p2.col.iloc[0], 1)

        s2_p1_bcds = ['CGTATAAATGCG', 'ATGCTGCAACAC', 'ACTCGCTCGCTG',
                      'TTCCTTAGTAGT', 'CGTCCGTATGAA', 'ACGTGAGGAACG',
                      'GGTTGCCCTGTA', 'CATATAGCCCGA', 'GCCTATGAGATC',
                      'CAAGTGAAGGGA', 'CACGTTTATTCC', 'TAATCGGTGCCA']
        s2_p2_bcds = ['CTTGGAGGCTTA', 'GTGCCGGCCGAC', 'AGAGGGTGATCG',
                      'GGATACTCGCAT', 'TCATGGCCTCCG', 'ATGTGCTGCTCG',
                      'CCACGAGCAGGC', 'CGCCGTACTTGC']
        for idx, sample in enumerate(samples2[:8]):
            md_sample = study2_prep[study2_prep.sample_name == sample]
            self.assertEqual(len(md_sample), 2)

            md_sample_p1 = md_sample[md_sample.dna_plate_name == 'Plate 1']
            self.assertEqual(len(md_sample_p1), 1)
            self.assertEqual(md_sample_p1.barcode.iloc[0], s2_p1_bcds[idx])
            self.assertEqual(md_sample_p1.row.iloc[0], 2)
            self.assertEqual(md_sample_p1.col.iloc[0], idx + 1)

            md_sample_p2 = md_sample[md_sample.dna_plate_name == 'Plate 2']
            self.assertEqual(len(md_sample_p2), 1)
            self.assertEqual(md_sample_p2.barcode.iloc[0], s2_p2_bcds[idx])
            self.assertEqual(md_sample_p2.row.iloc[0], idx + 1)
            self.assertEqual(md_sample_p2.col.iloc[0], 2)


if __name__ == "__main__":
    main()

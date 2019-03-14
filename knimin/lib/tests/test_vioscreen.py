from unittest import TestCase, main, skipIf
import json

from knimin.lib.vioscreen import VioscreenHandler
from knimin import config


skip = config.vioscreen_regcode == 'test'


class TestVioscreenHandler(TestCase):
    @skipIf(skip, "No credentials")
    def setUp(self):
        self.vio = VioscreenHandler()
        self.vio.sync_vioscreen({'853df6a15d131b2c'})

    @skipIf(skip, "No credentials")
    def tearDown(self):
        self.vio.flush_vioscreen_db()

    @skipIf(skip, "No credentials")
    def test_get_token(self):
        token = self.vio.get_token()
        self.assertIsNotNone(token)

    @skipIf(skip, "No credentials")
    def test_get_users(self):
        users = self.vio.get_users()
        self.assertIsNotNone(users)
        self.assertIsNotNone(users['users'])

        user = users['users'][0]
        res = user.keys()
        exp = [u'username',
               u'weight',
               u'firstname',
               u'displayUnits',
               u'middlename',
               u'lastname',
               u'activityLevel',
               u'created',
               u'subjectId',
               u'email',
               u'height',
               u'dateOfBirth',
               u'gender',
               u'timeZone',
               u'guid',
               u'id']
        for i in res:
            self.assertIn(i, exp)

    @skipIf(skip, "No credentials")
    def test_get_init_surveys(self):
        res = self.vio.get_init_surveys()
        exp = '853df6a15d131b2c'
        self.assertIn(exp, res.keys())
        self.assertEqual('Finished', res[exp])

    @skipIf(skip, "No credentials")
    def test_update_status(self):
        survey_id = '853df6a15d131b2c'

        self.vio.update_status(survey_id, 'Started')
        sql = '''SELECT * FROM ag.vioscreen_surveys WHERE survey_id = %s'''

        res = list(self.vio.sql_handler.execute_fetchone(sql, [survey_id]))
        self.assertEqual(['Started', survey_id, None], res)

        self.vio.update_status(survey_id, 'Finished')
        res = self.vio.sql_handler.execute_fetchone(sql, [survey_id])

        self.assertEqual('Finished', res['status'])
        self.assertEqual(survey_id, res['survey_id'])
        self.assertIsNotNone(res['pulldown_date'])

    @skipIf(skip, "No credentials")
    def test_insert_survey(self):
        survey_id = u'4fa6fd0e4f93adea'

        self.vio.insert_survey(survey_id, 'Finished')
        sql = '''SELECT * FROM ag.vioscreen_surveys WHERE survey_id = %s'''
        res = self.vio.sql_handler.execute_fetchone(sql, [survey_id])

        self.assertEqual('Finished', res['status'])
        self.assertEqual(survey_id, res['survey_id'])
        self.assertIsNotNone(res['pulldown_date'])

    @skipIf(skip, "No credentials")
    def test_insert_survey_duplicate(self):
        with self.assertRaises(ValueError):
            self.vio.insert_survey('853df6a15d131b2c', 'Finished')

    @skipIf(skip, "No credentials")
    def test_get_vio_survey_ids_not_in_ag(self):
        survey_ids = {'853df6a15d131b2c', '63df0f4276b84b14'}
        res = self.vio.get_vio_survey_ids_not_in_ag(survey_ids)

        self.assertNotIn('853df6a15d131b2c', res)
        self.assertIn('63df0f4276b84b14', res)

    @skipIf(skip, "No credentials")
    def test_tidyfy(self):
        username = 'testuser'
        data = [{'amount': 10,
                 'code': u'substance_a',
                 'description': u'Substance A',
                 'units': u'mg',
                 'valueType': u'Amount'},
                {'amount': 20,
                 'code': u'substance_b',
                 'description': u'Substance B',
                 'units': u'g',
                 'valueType': u'Amount'},
                {'amount': 30,
                 'code': u'substance_c',
                 'description': u'Substance C'}]
        tidy_data = self.vio.tidyfy(username, data)
        for row in tidy_data:
            self.assertIn('survey_id', row.keys())
            self.assertIn(username, row.values())
            del row['survey_id']
        self.assertEqual(data, tidy_data)

    @skipIf(skip, "No credentials")
    def test_get_session_data_foodcomponents(self):
        session_id = u'000ada854d4f45f5abda90ccade7f0a8'
        endpoint = 'foodcomponents'
        foodcomponents = self.vio.get_session_data(session_id, endpoint)
        self.assertEqual(len(foodcomponents), 2)
        self.assertIn('sessionId', foodcomponents.keys())
        self.assertIn('data', foodcomponents.keys())
        self.assertEqual(foodcomponents['sessionId'], session_id)
        self.assertIsNotNone(foodcomponents['data'])

    @skipIf(skip, "No credentials")
    def test_get_session_data(self):
        session_id = u'000ada854d4f45f5abda90ccade7f0a8'
        endpoints = ['foodcomponents',
                     'percentenergy',
                     'mpeds',
                     'eatingpatterns',
                     'foodconsumption',
                     'dietaryscore']
        for endpoint in endpoints:
            res = self.vio.get_session_data(session_id, endpoint)
            self.assertIsNotNone(res)

    @skipIf(skip, "No credentials")
    def test_sync_vioscreen_inval_param(self):
        survey_ids = ['853df6a15d131b2c']
        survey_ids_1 = '853df6a15d131b2c'
        with self.assertRaises(TypeError):
            self.vio.sync_vioscreen(survey_ids)
            self.vio.sync_vioscreen(survey_ids_1)

    @skipIf(skip, "No credentials")
    def test_insert_foodcomponents(self):
        survey_id = u'dd8445986318aed4'
        data = [{u'amount': 0.0,
                 u'code': u'acesupot',
                 u'description': u'Acesulfame Potassium',
                 'survey_id': u'dd8445986318aed4',
                 u'units': u'mg',
                 u'valueType': u'Amount'},
                {u'amount': 29.5868480021635,
                 u'code': u'addsugar',
                 u'description': u'Added Sugars (by Available Carbohydrate)',
                 'survey_id': u'dd8445986318aed4',
                 u'units': u'g',
                 u'valueType': u'Amount'},
                {u'amount': 27.345585189008,
                 u'code': u'adsugtot',
                 u'description': u'Added Sugars (by Total Sugars)',
                 'survey_id': u'dd8445986318aed4',
                 u'units': u'g',
                 u'valueType': u'Amount'}]
        res = self.vio.insert_foodcomponents(data)
        self.assertEqual(res, len(data))

        sql = '''SELECT * FROM ag.vioscreen_foodcomponents
                 WHERE survey_id = %s'''
        res = self.vio.sql_handler.execute_fetchall(sql, [survey_id])
        res = [dict(r) for r in res]
        # Compares each row of original data to those of pulled data
        # The rows should all be the same, with the exception of keys,
        # which are always lowercase when pulled from the db
        for row in range(len(data)):
            for key in data[row].keys():
                self.assertEqual(res[row][key.lower()], data[row][key])

    @skipIf(skip, "No credentials")
    def test_insert_percentenergy(self):
        survey_id = u'dd8445986318aed4'
        data = [{u'amount': 29.3328087363491,
                 u'code': u'%fat',
                 u'description': u'Percent of calories from Fat',
                 u'foodComponentType': 1,
                 u'foodDataDefinition': None,
                 u'precision': 0,
                 u'shortDescription': u'Fat',
                 'survey_id': u'dd8445986318aed4',
                 u'units': u'%'},
                {u'amount': 15.7438637903384,
                 u'code': u'%protein',
                 u'description': u'Percent of calories from Protein',
                 u'foodComponentType': 1,
                 u'foodDataDefinition': None,
                 u'precision': 0,
                 u'shortDescription': u'Protein',
                 'survey_id': u'dd8445986318aed4',
                 u'units': u'%'}]
        res = self.vio.insert_percentenergy(data)
        self.assertEqual(res, len(data))

        sql = '''SELECT * FROM ag.vioscreen_percentenergy
                 WHERE survey_id = %s'''
        res = self.vio.sql_handler.execute_fetchall(sql, [survey_id])
        res = [dict(r) for r in res]
        for row in range(len(data)):
            for key in data[row].keys():
                self.assertEqual(res[row][key.lower()], data[row][key])

    @skipIf(skip, "No credentials")
    def test_insert_mpeds(self):
        survey_id = u'dd8445986318aed4'
        data = [{u'amount': 0.000623145173877886,
                 u'code': u'A_BEV',
                 u'description': u'MPED: Total drinks of alcohol',
                 'survey_id': u'dd8445986318aed4',
                 u'units': u'alc_drinks',
                 u'valueType': u'Amount'},
                {u'amount': 0.0,
                 u'code': u'A_CAL',
                 u'description': u'MPED: Calories from alcoholic beverages',
                 'survey_id': u'dd8445986318aed4',
                 u'units': u'kcal',
                 u'valueType': u'Amount'}]
        res = self.vio.insert_mpeds(data)
        self.assertEqual(res, len(data))

        sql = '''SELECT * FROM ag.vioscreen_mpeds
                 WHERE survey_id = %s'''
        res = self.vio.sql_handler.execute_fetchall(sql, [survey_id])
        res = [dict(r) for r in res]
        for row in range(len(data)):
            for key in data[row].keys():
                self.assertEqual(res[row][key.lower()], data[row][key])

    @skipIf(skip, "No credentials")
    def test_insert_eatingpatterns(self):
        survey_id = u'dd8445986318aed4'
        data = [{u'amount': 4.85534558425067,
                 u'code': u'ADDEDFATS',
                 u'description': u'Eating Pattern',
                 'survey_id': u'dd8445986318aed4',
                 u'units': None,
                 u'valueType': u'Amount'},
                {u'amount': 0.000623145173877886,
                 u'code': u'ALCOHOLSERV',
                 u'description': u'Eating Pattern',
                 'survey_id': u'dd8445986318aed4',
                 u'units': None,
                 u'valueType': u'Amount'}]
        res = self.vio.insert_eatingpatterns(data)
        self.assertEqual(res, len(data))

        sql = '''SELECT * FROM ag.vioscreen_eatingpatterns
                 WHERE survey_id = %s'''
        res = self.vio.sql_handler.execute_fetchall(sql, [survey_id])
        res = [dict(r) for r in res]
        for row in range(len(data)):
            for key in data[row].keys():
                self.assertEqual(res[row][key.lower()], data[row][key])

    @skipIf(skip, "No credentials")
    def test_insert_foodconsumption(self):
        survey_id = u'dd8445986318aed4'
        data = [{u'amount': 1.0,
                 u'consumptionAdjustment': 1.0,
                 u'created': u'2017-07-29T06:55:57.537',
                 u'data': [{"units": "mg", "amount": 0.0, "code": "acesupot",
                            "description": "Acesulfame Potassium",
                            "valueType": "Amount"}],
                 u'description': (u'All other cheese, such as American, '
                                  'cheddar or cream cheese, including '
                                  'cheese used in cooking'),
                 u'foodCode': u'70005',
                 u'foodGroup': u'Cheese and Dairy Products',
                 u'frequency': 52,
                 u'servingFrequencyText': u'1 per week',
                 u'servingSizeText': (u'1 slice (1 oz), 1/4 cup shredded, '
                                      '2 tablespoons cream cheese'),
                 'survey_id': u'dd8445986318aed4'}]
        res = self.vio.insert_foodconsumption(data)
        self.assertEqual(res, len(data))

        sql = '''SELECT * FROM ag.vioscreen_foodconsumption
                 WHERE survey_id = %s'''
        res = self.vio.sql_handler.execute_fetchall(sql, [survey_id])
        res = [dict(r) for r in res]
        for row in range(len(data)):
            data[row]['data'] = json.loads(data[row]['data'])
            for key in data[row].keys():
                self.assertEqual(res[row][key.lower()], data[row][key])

    @skipIf(skip, "No credentials")
    def test_insert_dietaryscore(self):
        survey_id = u'dd8445986318aed4'
        data = [{u'lowerLimit': 0.0,
                 u'name': u'Total Vegetables',
                 u'score': 5.0,
                 'survey_id': u'dd8445986318aed4',
                 u'type': u'TotalVegetables',
                 u'upperLimit': 5.0},
                {u'lowerLimit': 0.0,
                 u'name': u'Greens and Beans',
                 u'score': 5.0,
                 'survey_id': u'dd8445986318aed4',
                 u'type': u'GreensAndBeans',
                 u'upperLimit': 5.0}]
        res = self.vio.insert_dietaryscore(data)
        self.assertEqual(res, len(data))

        sql = '''SELECT * FROM ag.vioscreen_dietaryscore
                 WHERE survey_id = %s'''
        res = self.vio.sql_handler.execute_fetchall(sql, [survey_id])
        res = [dict(r) for r in res]
        for row in range(len(data)):
            for key in data[row].keys():
                self.assertEqual(res[row][key.lower()], data[row][key])


if __name__ == "__main__":
    main()

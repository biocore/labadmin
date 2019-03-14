import requests
import os
import json

from datetime import datetime
from functools import partial
from knimin import config
from knimin.lib.data_access import SQLHandler


class VioscreenHandler(object):
    """VioScreen handler object.

    Used to pull data from VioScreen RESTful API and store data in AG database.
    """
    def __init__(self):
        self._key = config.vioscreen_regcode
        self._user = config.vioscreen_user
        self._pw = config.vioscreen_password

        self._session = requests.Session()
        # define partial functions for get and post
        self.get = partial(self.request, self._session.get)
        self.post = partial(self.request, self._session.post)
        # setup our HTTP header data
        self._headers = {'Accept': 'application/json',
                         'Authorization': 'Bearer %s' % self.get_token()}
        self._users = self.get_users()
        self.sql_handler = SQLHandler(config)

    def get_token(self):
        """Gets an API token for vioscreen

        Return
        ------
        str
            The API token

        Raises
        ------
        ValueError
            If the post returned None
        """
        url = 'https://api.viocare.com/%s/auth/login' % self._key
        response = self.post(url,
                             data={"username": self._user,
                                   "password": self._pw})
        if 'token' not in response:
            raise ValueError('Token request not successful')
        return response['token']

    def get_users(self):
        """Gets list of users that vioscreen has data for

        Return
        ------
        list of dict
            List of users that have vioscreen data
        """
        return self.get('https://api.viocare.com/%s/users' % self._key,
                        headers=self._headers)

    def request(self, func, url, retries=5, **kwargs):
        """Extension of get  and post methods from requests.
        Will make a request for data and return it, or return an
        error message if data was unable to be retrieved

        Parameters
        ----------
        func: function
            requests function being called, either GET or POST
        url: str
            The url from which data is requested
        retries: int
            Number of tries the function takes if we refresh the token
            each time a retrieval fails
        **kwargs
            Optional arguments that requests takes

        Return
        ------
        dict
            Data returned from HTTP request
        """
        for i in range(retries):
            req = func(url, **kwargs)
            if req.status_code != 200:  # HTTP status code, 200 is all good
                data = req.json()

                # if we did not get a HTTP status code 200, than guess that the
                # API token is no longer valid so get a new one and retry
                if 'Code' in data and data['Code'] == 1016:
                    self._headers['token'] = self.get_token()
                else:
                    raise ValueError("Unable to make this query work: %s\n%s"
                                     % (str(data),
                                        str(sorted(os.environ.keys()))))
            else:
                return req.json()
        raise ValueError("Unable to make this query work")

    def tidyfy(self, username, payload):
        """Restructures data so that 'survey_id' is associated with each row

        Parameters
        ----------
        username: str
            Survey ID that is being inserted each of the rows
        payload: list of dict
            The data that is getting associated with the survey_id

        Return
        ------
        list of dict
            The newly formatted data containing the username in each row
        """
        dat = []
        for entry in payload:
            entry['survey_id'] = username
            dat.append(entry)
        return dat

    def get_session_data(self, session_id, endpoint):
        """Pulls data from the vioscreen API based on
        a specific session ID and session type(ex. 'foodcomponents')

        Parameters
        ----------
        session_id: str
            Session ID that data is being requested for
        endpoint: str
            Name of the session type that data is being requested for

        Return
        ------
        dict:
            Food frequency questionnaire data
        """
        url = 'https://api.viocare.com/%s/sessions/%s/%s' % (self._key,
                                                             session_id,
                                                             endpoint)
        return self.get(url, headers=self._headers)

    def sync_vioscreen(self, user_ids=None):
        """Pulls data from the vioscreen API and stores
        the data into the AG database

        Parameters
        ----------
        user_ids: set of str
            Set of user_ids (identical to survey_ids) that
            are needed to have their data pulled. Default None (syncs all)
        """
        all_vio_user_ids = {x['username'] for x in self._users['users']}
        failures = []
        if user_ids is not None:
            without_ffq = user_ids - all_vio_user_ids
            failures = list(without_ffq)
            user_ids = all_vio_user_ids & user_ids
        else:
            user_ids = all_vio_user_ids

        # takes all survey IDs from vio_screen survey info and filters
        # only ones that do not have their data in the ag database
        ids_to_sync = self.get_vio_survey_ids_not_in_ag(user_ids)

        # gets list of surveys in AG database along with their statuses
        survey_ids = self.get_init_surveys()

        for username in ids_to_sync:
            url = 'https://api.viocare.com/%s/users/%s/sessions' % (self._key,
                                                                    username)
            session_data = self.get(url, headers=self._headers)
            session_detail = session_data['sessions'][0]
            sessionid = session_detail['sessionId']

            url = 'https://api.viocare.com/%s/sessions/%s/detail' % (self._key,
                                                                     sessionid)
            detail = self.get(url, headers=self._headers)

            # Adds new survey information to database
            if username not in survey_ids:
                survey_ids[username] = detail['status']
                self.insert_survey(username, detail['status'])
            # Updates status of vioscreen survey if it has changed
            elif survey_ids[username] != detail['status']:
                survey_ids[username] = detail['status']
                self.update_status(username, detail['status'])

            # only finished surveys will have their data pulled
            if detail['status'] != 'Finished':
                continue

            try:
                foodcomponents = self.get_session_data(sessionid,
                                                       'foodcomponents')
                percentenergy = self.get_session_data(sessionid,
                                                      'percentenergy')
                mpeds = self.get_session_data(sessionid,
                                              'mpeds')
                eatingpatterns = self.get_session_data(sessionid,
                                                       'eatingpatterns')
                foodconsumption = self.get_session_data(sessionid,
                                                        'foodconsumption')
                dietaryscore = self.get_session_data(sessionid,
                                                     'dietaryscore')
            except ValueError:
                # sometimes there is a status Finished w/o data...
                continue

            dietaryscore = dietaryscore['dietaryScore']['scores']
            foodconsumption = foodconsumption['foodConsumption']
            mpeds = mpeds['data']
            eatingpatterns = eatingpatterns['data']
            percentenergy = percentenergy['calculations']
            foodcomponents = foodcomponents['data']

            foodcomponents = self.tidyfy(username, foodcomponents)
            percentenergy = self.tidyfy(username, percentenergy)
            mpeds = self.tidyfy(username, mpeds)
            eatingpatterns = self.tidyfy(username, eatingpatterns)
            foodconsumption = self.tidyfy(username, foodconsumption)
            dietaryscore = self.tidyfy(username, dietaryscore)

            self.insert_foodcomponents(foodcomponents)
            self.insert_percentenergy(percentenergy)
            self.insert_mpeds(mpeds)
            self.insert_eatingpatterns(eatingpatterns)
            self.insert_foodconsumption(foodconsumption)
            self.insert_dietaryscore(dietaryscore)

        return failures

    # DB access functions
    def get_init_surveys(self):
        """Retrieve initial set of vioscreen surveys before sync

        Returns
        -------
        dict
           Initial set of survey IDs and their corresponding statuses
        """
        sql = """SELECT survey_id, status from ag.vioscreen_surveys"""
        data = self.sql_handler.execute_fetchall(sql)
        survey_ids = {}
        for row in data:
            survey_ids[row[0]] = row[1]
        return survey_ids

    def update_status(self, survey_id, status):
        """Updates vioscreen status of AG database to correspond to status
           pulled from vioscreen

        Parameters
        ----------
        survey_id: str
            Survey ID being updated in database
        status: str
            Status that the survey ID status is being updated to
        """
        if status == 'Finished':
            pulldown_date = datetime.now()
        else:
            pulldown_date = None
        sql = """UPDATE ag.vioscreen_surveys SET status=%s,
                 pulldown_date=%s WHERE survey_id=%s"""
        self.sql_handler.execute(sql, [status, pulldown_date, survey_id])

    def insert_survey(self, survey_id, status):
        """Inserts a survey id that has a vioscreen session along with its
           status ('Started', 'Finished', etc.) and pulldown date into the
           ag.vioscreen_surveys table

        Parameters
        ----------
        survey_id: str
            Survey ID being inserted into vioscreen survey database
        status: str
            Status that the survey ID is being inserted with
        """
        pulldown_date = datetime.now()
        sql = """INSERT INTO ag.vioscreen_surveys (status, survey_id,
                 pulldown_date) VALUES (%s, %s, %s)"""
        self.sql_handler.execute(sql, [status, survey_id, pulldown_date])

    def get_vio_survey_ids_not_in_ag(self, vio_ids):
        """Retrieve survey ids that have vioscreen data but
           have not have their data transferred to AG

        Parameters
        ----------
        vio_ids: set of str
            The set of IDs present in vioscreen

        Returns
        -------
        set of str
            The set of survey IDs in vioscreen that aren't in AG
        """
        sql = """SELECT survey_id FROM ag.vioscreen_surveys
                 WHERE status = 'Finished'"""

        ag_survey_ids = self.sql_handler.execute_fetchall(sql)
        ag_survey_ids = {i[0] for i in ag_survey_ids}
        return vio_ids - set(ag_survey_ids)

    def _call_sql_handler(self, sql, session_data):
        """Formats session_data to insert into a particular table

        Parameters
        ----------
        sql: str
            SQL query specific to particular session insertion
            session_data : Data pulled from Vioscreen
        session_data: list of dict
            The data that is being stored into the AG database

        Return
        ------
        int
            The number of rows added to the database
        """
        # inserts represents the data of a session to be stored
        inserts = []
        keys = sorted(session_data[0].keys())
        for row in session_data:
            # row_insert represents the data of a single row
            row_insert = []
            for key in keys:
                row_insert.append(row[key])
            inserts.append(row_insert)
        self.sql_handler.executemany(sql, inserts)
        return len(inserts)

    def insert_foodcomponents(self, foodcomponents):
        """Inserts foodcomponents data into AG database

        Parameters
        ----------
        foodcomponents: list of different types
            foodcomponents session data

        Return
        ------
        int
            The number of rows added to the database
        """
        sql = """INSERT INTO ag.vioscreen_foodcomponents (amount, code,
                 description, survey_id, units, valueType) VALUES (%s,
                 %s, %s, %s, %s, %s)"""
        return self._call_sql_handler(sql, foodcomponents)

    def insert_percentenergy(self, percentenergy):
        """Inserts percentenergy data into AG database

        Parameters
        ----------
        percentenergy: list of different types
            percentenergy session data

        Return
        ------
        int
            The number of rows added to the database
        """
        sql = """INSERT INTO ag.vioscreen_percentenergy
                    (amount, code, description, foodComponentType,
                     foodDataDefinition, precision, shortDescription,
                     survey_id, units)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        return self._call_sql_handler(sql, percentenergy)

    def insert_mpeds(self, mpeds):
        """Inserts mpeds data into AG database

        Parameters
        ----------
        mpeds: list of different types
            mpeds session data

        Return
        ------
        int
            The number of rows added to the database
        """
        sql = """INSERT INTO ag.vioscreen_mpeds
                    (amount, code, description, survey_id,
                     units, valueType)
                 VALUES (%s, %s, %s, %s, %s, %s)"""
        return self._call_sql_handler(sql, mpeds)

    def insert_eatingpatterns(self, eatingpatterns):
        """Inserts eatingpatterns data into AG database

        Parameters
        ----------
        eatingpatterns: list of different types
            eatingpatterns session data

        Return
        ------
        int
            The number of rows added to the database
        """
        sql = """INSERT INTO ag.vioscreen_eatingpatterns
                    (amount, code, description,
                     survey_id, units, valueType)
                 VALUES (%s, %s, %s, %s, %s, %s)"""
        return self._call_sql_handler(sql, eatingpatterns)

    def insert_foodconsumption(self, foodconsumption):
        """Inserts foodconsumption data into AG database

        Parameters
        ----------
        foodconsumption: list of different types
            foodconsumption session data

        Return
        ------
        int
            The number of rows added to the database
        """
        sql = """INSERT INTO ag.vioscreen_foodconsumption
                    (amount, consumptionAdjustment, created, data, description,
                     foodCode, foodGroup, frequency, servingFrequencyText,
                     servingSizeText, survey_id)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        # convert large data dict to json for data storage
        for row in foodconsumption:
            row['data'] = json.dumps(row['data'])
        return self._call_sql_handler(sql, foodconsumption)

    def insert_dietaryscore(self, dietaryscore):
        """Inserts dietaryscore data into AG database

        Parameters
        ----------
        dietaryscore: list of different types
            dietaryscore session data

        Return
        ------
        int
            The number of rows added to the database
        """
        sql = """INSERT INTO ag.vioscreen_dietaryscore
                    (lowerLimit, name, score, survey_id,
                     type, upperLimit)
                 VALUES (%s, %s, %s, %s, %s, %s)"""
        return self._call_sql_handler(sql, dietaryscore)

    # Testing function
    def flush_vioscreen_db(self):
        """Flushes VioScreen data from AG database"""
        tables = ['foodcomponents', 'percentenergy', 'mpeds', 'eatingpatterns',
                  'foodconsumption', 'dietaryscore', 'surveys']
        for i in tables:
            sql = """DELETE FROM ag.vioscreen_{0}""".format(i)
            self.sql_handler.execute(sql)

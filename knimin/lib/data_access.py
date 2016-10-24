from __future__ import unicode_literals
from contextlib import contextmanager
from collections import defaultdict, namedtuple
from os import walk
from os.path import join, splitext, isdir, abspath
from copy import copy
from re import sub
from hashlib import sha512
from datetime import datetime, time, timedelta
import json
import re

from bcrypt import hashpw, gensalt
from future.utils import viewitems

from psycopg2 import connect, Error as PostgresError
from psycopg2.extras import DictCursor

from mail import send_email
from util import (make_valid_kit_ids, make_verification_code, make_passwd,
                  categorize_age, categorize_etoh, categorize_bmi, correct_age,
                  fetch_url, correct_bmi)
from constants import (md_lookup, month_int_lookup, month_str_lookup,
                       regions_by_state, blanks_values, season_lookup,
                       ebi_remove, env_lookup)
from geocoder import geocode, Location, GoogleAPILimitExceeded
from string_converter import converter
from sql_connection import TRN


class IncorrectEmailError(Exception):
    pass


class IncorrectPasswordError(Exception):
    pass


class SQLHandler(object):
    """Encapsulates the DB connection with the Postgres DB

    Sourced from QIITA's SQLConnectionHandler
    """
    def __init__(self, config):
        self._connection = connect(user=config.db_user,
                                   password=config.db_password,
                                   database=config.db_database,
                                   host=config.db_host,
                                   port=config.db_port)

    def __del__(self):
        self._connection.close()

    @contextmanager
    def cursor(self):
        """ Returns a Postgres cursor

        Returns
        -------
        pgcursor : psycopg2.cursor
        """
        with self._connection.cursor(cursor_factory=DictCursor) as cur:
            yield cur

    def _check_sql_args(self, sql_args):
        """ Checks that sql_args have the correct type

        Inputs:
            sql_args: SQL arguments

        Raises a TypeError if sql_args does not have the correct type,
            otherwise it just returns the execution to the caller
        """
        # Check that sql arguments have the correct type
        if sql_args and type(sql_args) not in [tuple, list, dict]:
            raise TypeError("sql_args should be tuple, list or dict. Found %s "
                            % type(sql_args))

    @contextmanager
    def _sql_executor(self, sql, sql_args=None, many=False):
        """Executes an SQL query

        Parameters
        ----------
        sql: str
            The SQL query
        sql_args: tuple or list, optional
            The arguments for the SQL query
        many: bool, optional
            If true, performs an execute many call

        Returns
        -------
        pgcursor : psycopg2.cursor
            The cursor in which the SQL query was executed

        Raises
        ------
        ValueError
            If there is some error executing the SQL query
        """
        # Check that sql arguments have the correct type
        if many:
            for args in sql_args:
                self._check_sql_args(args)
        else:
            self._check_sql_args(sql_args)

        # Execute the query
        with self.cursor() as cur:
            try:
                if many:
                    cur.executemany(sql, sql_args)
                else:
                    cur.execute(sql, sql_args)
                yield cur
                self._connection.commit()
            except PostgresError as e:
                self._connection.rollback()
                try:
                    err_sql = cur.mogrify(sql, sql_args)
                except:
                    err_sql = cur.mogrify(sql, sql_args[0])
                raise ValueError(("\nError running SQL query: %s"
                                  "\nError: %s" % (err_sql, e)))

    def execute_fetchall(self, sql, sql_args=None):
        """ Executes a fetchall SQL query

        Parameters
        ----------
        sql: str
            The SQL query
        sql_args: tuple or list, optional
            The arguments for the SQL query

        Returns
        ------
        list of tuples
            The results of the fetchall query

        Note: from psycopg2 documentation, only variable values should be bound
            via sql_args, it shouldn't be used to set table or field names. For
            those elements, ordinary string formatting should be used before
            running execute.
        """
        with self._sql_executor(sql, sql_args) as pgcursor:
            result = pgcursor.fetchall()
        return result

    def execute_fetchone(self, sql, sql_args=None):
        """ Executes a fetchone SQL query

        Parameters
        ----------
        sql: str
            The SQL query
        sql_args: tuple or list, optional
            The arguments for the SQL query

        Returns
        -------
        Tuple
            The results of the fetchone query

        Notes
        -----
        from psycopg2 documentation, only variable values should be bound
            via sql_args, it shouldn't be used to set table or field names. For
            those elements, ordinary string formatting should be used before
            running execute.
        """
        with self._sql_executor(sql, sql_args) as pgcursor:
            result = pgcursor.fetchone()
        return result

    def execute_fetchdict(self, sql, sql_args=None):
        """ Executes a fetchall SQL query and returns each row as a dict

        Parameters
        ----------
        sql: str
            The SQL query
        sql_args: tuple or list, optional
            The arguments for the SQL query

        Returns
        -------
        list of dict
            The results of the query as
            [{colname: val, colname: val, ...}, ...]

        Notes
        -----
        from psycopg2 documentation, only variable values should be bound
        via sql_args, it shouldn't be used to set table or field names.
        For those elements, ordinary string formatting should be used
        before running execute.
        """
        with self._sql_executor(sql, sql_args) as pgcursor:
            result = [dict(row) for row in pgcursor.fetchall()]
        return result

    def execute(self, sql, sql_args=None):
        """ Executes an SQL query with no results

        Parameters
        ----------
        sql: str
            The SQL query
        sql_args: tuple or list, optional
            The arguments for the SQL query

        Notes
        -----
        from psycopg2 documentation, only variable values should be bound
            via sql_args, it shouldn't be used to set table or field names. For
            those elements, ordinary string formatting should be used before
            running execute.
        """
        with self._sql_executor(sql, sql_args):
            pass

    def executemany(self, sql, sql_args_list):
        """ Executes an executemany SQL query with no results

        Parameters
        ----------
        sql: str
            The SQL query
        sql_args: list of tuples
            The arguments for the SQL query

        Note: from psycopg2 documentation, only variable values should be bound
            via sql_args, it shouldn't be used to set table or field names. For
            those elements, ordinary string formatting should be used before
            running execute.
        """
        with self._sql_executor(sql, sql_args_list, True):
            pass

    def execute_proc_return_cursor(self, procname, proc_args):
        """Executes a stored procedure and returns a cursor

        Parameters
        ----------
        procname: str
            the name of the stored procedure
        proc_args: list
            arguments sent to the stored procedure
        """
        proc_args.append('cur2')
        cur = self._connection.cursor()
        cur.callproc(procname, proc_args)
        cur.close()
        return self._connection.cursor('cur2')


class KniminAccess(object):
    # arbitrary, unique ID and value
    human_sites = ['Stool',
                   'Mouth',
                   'Right hand',
                   'Left hand',
                   'Forehead',
                   'Torso',
                   'Left leg',
                   'Right leg',
                   'Nares',
                   'Hair',
                   'Tears',
                   'Nasal mucus',
                   'Ear wax',
                   'Vaginal mucus']

    animal_sites = ['Stool',
                    'Mouth',
                    'Nares',
                    'Ears',
                    'Skin',
                    'Fur']

    general_sites = ['Animal Habitat',
                     'Biofilm',
                     'Dust',
                     'Food',
                     'Fermented Food',
                     'Indoor Surface',
                     'Outdoor Surface',
                     'Plant habitat',
                     'Soil',
                     'Sole of shoe',
                     'Water']

    def __init__(self, config):
        self._con = SQLHandler(config)
        self._con.execute('set search_path to ag, barcodes, public')
        self.config = config

    def _get_col_names_from_cursor(self, cur):
        if cur.description:
            return [x[0] for x in cur.description]
        else:
            return []

    def has_access(self, email, access_levels):
        """Whether user has access level given or not.

        Parameters
        ----------
        email : str
            Email of user to check
        access_levels : list of str
            Access level to check

        Returns
        -------
        bool
            Whether user has access (true) or not (false)

        Notes
        -----
        For uses with Admin acces, this will always return true.

        Raises
        ------
        ValueError
            Unknown access level passed
        """
        # Make sure all access levels passed exist
        sql = "Select 1 from ag.labadmin_access WHERE access_name = %s"
        for level in access_levels:
            if self._con.execute_fetchone(sql, [level]) is None:
                raise ValueError('Unknown access level %s' % level)

        sql = """SELECT EXISTS(
                    SELECT 1
                    FROM ag.labadmin_users_access
                    JOIN ag.labadmin_access USING (access_id)
                    WHERE email = %s AND access_name IN %s)"""
        access = tuple(access_levels + ['Admin'])
        return self._con.execute_fetchone(sql, [email, access])[0]

    def get_users(self):
        """Get a list of users in the system

        Returns
        -------
        list of str
            Users in the system
        """
        sql = "SELECT email FROM ag.labadmin_users"
        hold = self._con.execute_fetchall(sql)
        if hold is not None:
            return [x[0] for x in hold]
        else:
            return []

    def get_barcode_details(self, barcode):
        """
        Returns the general barcode details for a barcode
        """
        sql = """SELECT  create_date_time, status, scan_date,
                  sample_postmark_date,
                  biomass_remaining, sequencing_status, obsolete
                  FROM    barcode
                  WHERE barcode = %s"""
        res = self._con.execute_fetchdict(sql, [barcode])
        return res[0] if res else {}

    def get_access_levels(self):
        """Returns tuple of all access levels and ids in the system

        Returns
        -------
        list of tuple of (int, str)
            All access levels in the form (id, name)
        """
        sql = "SELECT access_id, access_name FROM ag.labadmin_access"
        return self._con.execute_fetchall(sql)

    def get_access_levels_user(self, email):
        """Returns tuple of all access levels and ids for a user

        Parameters
        ----------
        email : str
            Email of user to check

        Returns
        -------
        list of tuple of (int, str)
            All access levels in the form (id, name)
        """
        sql = """SELECT access_id, access_name
                 FROM ag.labadmin_access
                 JOIN ag.labadmin_users_access USING (access_id)
                 WHERE email = %s"""
        hold = self._con.execute_fetchall(sql, [email])
        return hold if hold is not None else []

    def alter_access_levels(self, email, levels):
        """Alters existing user's access levels

        Parameters
        ----------
        email : str
            Email of user to alter
        levels : list of int
            List of access level IDs user should now have
        """
        all_levels = set(l[0] for l in self.get_access_levels())
        new_levels = set(levels)
        user_levels = set(l[0] for l in self.get_access_levels_user(email))

        # Delete removed levels
        remove = all_levels - new_levels
        if remove:
            sql = """DELETE FROM ag.labadmin_users_access
                     WHERE email = %s and access_id IN %s"""
            self._con.execute(sql, [email, tuple(remove)])

        # Add new levels
        add = new_levels - user_levels
        if add:
            sql = """INSERT INTO ag.labadmin_users_access (email, access_id)
                     VALUES (%s, %s)"""
            self._con.executemany(sql, [(email, l) for l in add])

    def get_ag_barcode_details(self, barcodes):
        """Retrieve sample, kit, and login details by barcode

        Parameters
        ----------
        barcodes : iterable of str
            The list of barcodes for which to get login details

        Returns
        -------
        dict of dict
            {barcode: {column: value}, ...}
        """
        sql = """SELECT DISTINCT barcode, *
                 FROM ag_kit_barcodes
                 JOIN ag_kit USING (ag_kit_id)
                 FULL OUTER JOIN ag_login_surveys USING
                    (survey_id, ag_login_id)
                 JOIN ag_login USING (ag_login_id)
                 WHERE barcode in %s"""
        res = self._con.execute_fetchall(sql, [tuple(b[:9] for b in barcodes)])
        return {row[0]: dict(row) for row in res}

    def get_surveys(self, barcodes):  # noqa
        """Retrieve surveys for specific barcodes

        Parameters
        ----------
        barcodes : iterable of str
            The list of barcodes for which metadata will be retrieved

        Returns
        -------
        dict
            {survey: {barcode: {shortname: response, ...}, ...}, ...}

        Notes
        -----
        For multiples, the shortname that is used in the returned dict is
        combined with a modified version of the response. Specifically, spaces
        and non-alphanumeric characters are replaced with underscroes, and the
        response is capitalized. E.g., If the person is allergic to "Tree
        nuts", the key in the dict would be "ALLERGIC_TO_TREE_NUTS" (the
        ALLERGIC_TO portion taken from the shortname column of the question
        table).
        """
        # SINGLE answers SQL
        single_sql = \
            """SELECT S.survey_id, barcode, question_shortname, response
               FROM ag.ag_kit_barcodes
               JOIN ag.survey_answers SA USING (survey_id)
               JOIN ag.survey_question USING (survey_question_id)
               JOIN ag.survey_question_response_type USING (survey_question_id)
               JOIN ag.group_questions GQ USING (survey_question_id)
               JOIN ag.surveys S USING (survey_group)
               WHERE survey_response_type='SINGLE'
                   AND (withdrawn IS NULL OR withdrawn != 'Y')
                   AND barcode in %s"""

        # MULTIPLE answers SQL
        multiple_sql = \
            """SELECT S.survey_id, barcode, question_shortname,
                      array_agg(response) as responses
               FROM ag.ag_kit_barcodes
               JOIN ag.survey_answers USING (survey_id)
               JOIN ag.survey_question USING (survey_question_id)
               JOIN ag.survey_question_response_type USING (survey_question_id)
               JOIN ag.group_questions USING (survey_question_id)
               JOIN ag.surveys S USING (survey_group)
               WHERE survey_response_type='MULTIPLE'
                   AND (withdrawn IS NULL OR withdrawn != 'Y')
                   AND barcode in %s
               GROUP BY S.survey_id, barcode, question_shortname"""

        # Also need to get the possible responses for multiples
        multiple_responses_sql = \
            """SELECT question_shortname, response
               FROM survey_question
               JOIN survey_question_response_type USING (survey_question_id)
               JOIN survey_question_response USING (survey_question_id)
               WHERE survey_response_type = 'MULTIPLE'"""

        # STRING and TEXT answers SQL
        others_sql = \
            """SELECT S.survey_id, barcode, question_shortname, response
               FROM ag.ag_kit_barcodes
               JOIN ag.survey_answers_other SA USING (survey_id)
               JOIN ag.survey_question USING (survey_question_id)
               JOIN ag.survey_question_response_type USING (survey_question_id)
               JOIN ag.group_questions GQ USING (survey_question_id)
               JOIN ag.surveys S USING (survey_group)
               WHERE survey_response_type IN ('STRING', 'TEXT')
                   AND (withdrawn IS NULL OR withdrawn != 'Y')
                   AND barcode IN %s"""

        # Get third party surveys, if there is one and one is requested

        # Formats a question and response for a MULTIPLE question into a header
        def _translate_multiple_response_to_header(question, response):
            response = response.replace(" ", "_")
            response = sub('\W', '', response)
            header = '_'.join([question, response])
            return header.upper()

        # For each MULTIPLE question, build a dict of the possible responses
        # and what the header should be for the column representing the
        # response
        multiples_headers = defaultdict(dict)
        for question, response in self._con.execute_fetchall(
                multiple_responses_sql):
            multiples_headers[question][response] = \
                _translate_multiple_response_to_header(question, response)

        # find special case barcodes with appended info and store them
        special_bc = sorted(b for b in barcodes if len(b) > 9)
        # Strip off any appending from barcodes before getting data
        bc = tuple(set(b[:9] for b in barcodes))
        # this function reduces code duplication by generalizing as much
        # as possible how questions and responses are fetched from the db

        def _format_responses_as_dict(sql, json=False, multiple=False):
            ret_dict = defaultdict(lambda: defaultdict(dict))
            for survey, barcode, q, a in self._con.execute_fetchall(sql, [bc]):
                # Get special barcodes that match, if applicable
                match = [x for x in special_bc if barcode in x]
                if not match:
                    match = [barcode]

                if json:
                    # Clean since all json are single-element lists
                    # and we want no seperators at the beginning or end of data
                    a = unicode(a, 'utf-8')
                    a = a.strip('"\'[]_,\t\r\n\\/ ')
                if multiple:
                    for response, header in multiples_headers[q].items():
                        for bcs in match:
                            ret_dict[survey][bcs][header] = \
                                'Yes' if response in a else 'No'
                else:
                    for bcs in match:
                        ret_dict[survey][bcs][q] = a
            return ret_dict

        single_results = _format_responses_as_dict(single_sql)
        others_results = _format_responses_as_dict(others_sql, json=True)
        multiple_results = _format_responses_as_dict(multiple_sql,
                                                     multiple=True)

        # combine the results for each barcode
        for survey, barcodes in single_results.items():
            for barcode in barcodes:
                single_results[survey][barcode].update(
                    others_results[survey][barcode])
                single_results[survey][barcode].update(
                    multiple_results[survey][barcode])

        # At this point, the variable name is a misnomer, as it contains
        # the results from all question types
        return single_results

    def _months_between_dates(self, d1, d2):
        """Calculate the number of months between two dates

        Parameters
        ----------
        d1 : datetime
            First date
        d2 : datetime
            Second date

        Raises
        ------
        ValueError
            if the first date is greater than the second date

        Notes
        -----
        - Assumes the first date d1 is not greater than the second date d2
        - Ignores the day (uses only year and month)
        """
        if d1 > d2:
            raise ValueError("First date must not be greater than the second")

        # Calculate the number of 12-month periods between the years
        return (d2.year - d1.year) * 12 + (d2.month - d1.month)

    def _geocode(self, barcode, zipcode, country, zip_lookup, country_lookup):
        """Adds geocoding information to the barcoe for pulldown"""
        try:
            barcode['LATITUDE'] = zip_lookup[zipcode][country][0]
            barcode['LONGITUDE'] = zip_lookup[zipcode][country][1]
            barcode['ELEVATION'] = zip_lookup[zipcode][country][2]
            barcode['STATE'] = zip_lookup[zipcode][country][3]
            barcode['COUNTRY'] = country_lookup[country]
            barcode['GEO_LOC_NAME'] = ':'.join(
                [barcode['COUNTRY'], barcode['STATE']])
        except KeyError:
            # geocode unknown zip/country combo and add to
            # zipcode table & lookup dict
            info = self.get_geocode_zipcode(zipcode, country)
            if info.lat is not None:
                barcode['LATITUDE'] = "%.1f" % info.lat
                barcode['LONGITUDE'] = "%.1f" % info.long
                barcode['ELEVATION'] = "%.1f" % info.elev
                barcode['STATE'] = info.state
                barcode['COUNTRY'] = country_lookup[info.country]
                barcode['GEO_LOC_NAME'] = ':'.join(
                    [barcode['COUNTRY'], barcode['STATE']])
                # Store in dict so we don't geocode again
                zip_lookup[zipcode][country] = (
                    round(info.lat, 1), round(info.long, 1),
                    round(info.elev, 1), info.state)
            else:
                barcode['LATITUDE'] = 'Unspecified'
                barcode['LONGITUDE'] = 'Unspecified'
                barcode['ELEVATION'] = 'Unspecified'
                barcode['STATE'] = 'Unspecified'
                barcode['COUNTRY'] = 'Unspecified'
                barcode['GEO_LOC_NAME'] = 'Unspecified'
                # Store in dict so we don't geocode again
                zip_lookup[zipcode][country] = (
                    'Unspecified', 'Unspecified', 'Unspecified',
                    'Unspecified')
        return barcode

    def format_survey_data(self, md, external_surveys=None, full=False):  # noqa
        """Modifies barcode metadata to include all columns and correct units

        Specifically, this function:
        - corrects height and weight to be in the same units (cm and kg,
          respectively)
        - Adds AGE_MONTHS and AGE_YEARS columns
        - Adds standard columns for EBI and MiMARKS

        Parameters
        ----------
        md : dict of dict of dict
            E.g., the output from get_barcode_metadata.
            {survey: {barcode: {shortname: response, ...}, ...}, ...}
        external_surveys : list of str
            External surveys to add, default None
        full : bool
            Whether to pull full or filtered answers. Default filtered (False)

        Returns
        -------
        dict of dict of dict
            the formatted metadata
        list of tuple of str
            The barcode and error message if something failed
        """
        if external_surveys is None:
            external_surveys = []
        errors = {}
        # get barcode information
        all_barcodes = set().union(*[set(md[s]) for s in md])
        barcode_info = self.get_ag_barcode_details(all_barcodes)

        # tuples are latitude, longitude, elevation, state
        if full:
            zipcode_sql = """SELECT UPPER(zipcode), country,
                                 latitude::numeric,
                                 longitude::numeric,
                                 elevation::numeric, state
                             FROM zipcodes"""
        else:
            zipcode_sql = """SELECT UPPER(zipcode), country,
                                 round(latitude::numeric, 1),
                                 round(longitude::numeric,1),
                                 round(elevation::numeric, 1), state
                             FROM zipcodes"""
        zip_lookup = defaultdict(dict)
        for row in self._con.execute_fetchall(zipcode_sql):
            zip_lookup[row[0]][row[1]] = map(
                lambda x: x if x is not None else 'Unspecified', row[2:])

        country_sql = "SELECT country, EBI from ag.iso_country_lookup"
        country_lookup = dict(self._con.execute_fetchall(country_sql))
        # Add for scrubbed testing database
        country_lookup['REMOVED'] = 'REMOVED'

        survey_sql = "SELECT barcode, survey_id FROM ag.ag_kit_barcodes"
        survey_lookup = dict(self._con.execute_fetchall(survey_sql))

        dupes_sql = """SELECT duplicate_survey_id, participant_name
                       FROM ag.duplicate_consents dc
                       JOIN ag.ag_login_surveys als USING (ag_login_id)
                       WHERE  dc.main_survey_id = als.survey_id"""
        dupes_lookup = dict(self._con.execute_fetchall(dupes_sql))

        # Get external survey answers and normalize column names
        external_sql = """SELECT survey_id, external_survey, answers
                          FROM ag.external_survey_answers
                          JOIN ag.ag_kit_barcodes USING (survey_id)
                          JOIN ag.external_survey_sources
                            USING (external_survey_id)
                          WHERE external_survey = %s AND barcode IN %s"""
        external = defaultdict(dict)
        unknown_external = {}
        for e in external_surveys:
            for survey_id, survey, answers in self._con.execute_fetchall(
                    external_sql, [e, tuple(all_barcodes)]):
                external[survey_id].update({
                    self._convert_header(survey, key): val
                    for key, val in viewitems(answers)})
        if external:
            unknown_external = {k: 'Unspecified'
                                for k in external[external.keys()[0]].keys()}

        # Pet survey (id 2)
        for barcode, responses in md[2].items():
            # Invariant information
            md[2][barcode]['ANONYMIZED_NAME'] = barcode
            md[2][barcode]['HOST_SUBJECT_ID'] = barcode
            # md[2][barcode]['HOST_TAXID'] = ????
            md[2][barcode]['TITLE'] = 'American Gut Project'
            md[2][barcode]['ALTITUDE'] = 0
            md[2][barcode]['ASSIGNED_FROM_GEO'] = 'Yes'
            md[2][barcode]['ENV_BIOME'] = 'dense settlement biome'
            md[2][barcode]['ENV_FEATURE'] = 'animal-associated habitat'
            md[2][barcode]['DEPTH'] = 0
            md[2][barcode]['DESCRIPTION'] = 'American Gut Project' + \
                ' Animal sample'
            md[2][barcode]['DNA_EXTRACTED'] = 'Yes'
            md[2][barcode]['PHYSICAL_SPECIMEN_REMAINING'] = 'Yes'
            md[2][barcode]['PHYSICAL_SPECIMEN_LOCATION'] = 'UCSDMI'

            specific_info = barcode_info[barcode[:9]]
            zipcode = specific_info['zip'].upper()
            country = specific_info['country']
            md[1][barcode] = self._geocode(md[1][barcode], zipcode, country,
                                           zip_lookup, country_lookup)

        # Human survey (id 1)
        for barcode, responses in md[1].items():
            bc_info = barcode_info[barcode[:9]]
            try:
                # convert numeric fields
                for field in ('HEIGHT_CM', 'WEIGHT_KG'):
                    md[1][barcode][field] = sub('[^0-9.]',
                                                '', md[1][barcode][field])
                    if md[1][barcode][field]:
                        md[1][barcode][field] = float(md[1][barcode][field])
                    else:
                        md[1][barcode][field] = 'Unspecified'

                # Correct height units
                if responses['HEIGHT_UNITS'] == 'inches' and \
                        isinstance(md[1][barcode]['HEIGHT_CM'], float):
                    md[1][barcode]['HEIGHT_CM'] = \
                        2.54*md[1][barcode]['HEIGHT_CM']
                md[1][barcode]['HEIGHT_UNITS'] = 'centimeters'

                # Correct weight units
                if responses['WEIGHT_UNITS'] == 'pounds' and \
                        isinstance(md[1][barcode]['WEIGHT_KG'], float):
                    md[1][barcode]['WEIGHT_KG'] = \
                        md[1][barcode]['WEIGHT_KG']/2.20462
                md[1][barcode]['WEIGHT_UNITS'] = 'kilograms'

                if all([isinstance(md[1][barcode]['WEIGHT_KG'], float),
                        md[1][barcode]['WEIGHT_KG'] != 0.0,
                        isinstance(md[1][barcode]['HEIGHT_CM'], float),
                        md[1][barcode]['HEIGHT_CM'] != 0.0]):
                    md[1][barcode]['BMI'] = md[1][barcode]['WEIGHT_KG'] / \
                        (md[1][barcode]['HEIGHT_CM']/100)**2
                else:
                    md[1][barcode]['BMI'] = 'Unspecified'

                # Get age in years (int) and remove birth month
                if responses['BIRTH_MONTH'] != 'Unspecified' and \
                        responses['BIRTH_YEAR'] != 'Unspecified':
                    birthdate = datetime(
                        int(responses['BIRTH_YEAR']),
                        int(month_int_lookup[responses['BIRTH_MONTH']]), 1)
                    now = datetime.now()
                    md[1][barcode]['AGE_YEARS'] = int(
                        self._months_between_dates(birthdate, now) / 12.0)
                else:
                    md[1][barcode]['AGE_YEARS'] = 'Unspecified'

                # GENDER to SEX
                sex = md[1][barcode]['GENDER']
                if sex is not None:
                    sex = sex.lower()
                else:
                    sex = 'Unspecified'
                md[1][barcode]['SEX'] = sex

                # convenience variable
                site = bc_info['site_sampled']

                # Invariant information
                md[1][barcode]['ANONYMIZED_NAME'] = barcode
                md[1][barcode]['HOST_TAXID'] = 9606
                md[1][barcode]['SCIENTIFIC_NAME'] = 'Homo sapiens'
                md[1][barcode]['TITLE'] = 'American Gut Project'
                md[1][barcode]['ASSIGNED_FROM_GEO'] = 'Yes'
                md[1][barcode]['ENV_BIOME'] = 'dense settlement biome'
                md[1][barcode]['ENV_FEATURE'] = 'human-associated habitat'
                md[1][barcode]['DNA_EXTRACTED'] = 'Yes'
                md[1][barcode]['PHYSICAL_SPECIMEN_REMAINING'] = 'Yes'
                md[1][barcode]['PHYSICAL_SPECIMEN_LOCATION'] = 'UCSDMI'
                md[1][barcode]['HOST_COMMON_NAME'] = 'human'

                # Sample-dependent information
                zipcode = md[1][barcode]['ZIP_CODE'].upper()
                country = bc_info['country']
                md[1][barcode] = self._geocode(
                    md[1][barcode], zipcode, country, zip_lookup,
                    country_lookup)

                md[1][barcode]['SURVEY_ID'] = survey_lookup[barcode[:9]]
                md[1][barcode].update(md_lookup[site])
                md[1][barcode]['COLLECTION_DATE'] = \
                    bc_info['sample_date'].strftime('%m/%d/%Y')

                if bc_info['sample_time']:
                    md[1][barcode]['COLLECTION_TIME'] = \
                        bc_info['sample_time'].strftime('%H:%M')
                else:
                    # If no time data, show unspecified and default to midnight
                    md[1][barcode]['COLLECTION_TIME'] = 'Unspecified'
                    bc_info['sample_time'] = time(0, 0)

                md[1][barcode]['COLLECTION_TIMESTAMP'] = datetime.combine(
                    bc_info['sample_date'],
                    bc_info['sample_time']).strftime('%m/%d/%Y %H:%M')

                participant_name = dupes_lookup.get(
                    md[1][barcode]['SURVEY_ID'],
                    bc_info['participant_name']).lower()

                md[1][barcode]['HOST_SUBJECT_ID'] = sha512(
                    bc_info['ag_login_id'] + participant_name).hexdigest()
                md[1][barcode]['PUBLIC'] = 'Yes'

                # Convert finer grained IBD to coarser grained
                ibd = md[1][barcode].get('IBD_DIAGNOSIS_REFINED',
                                         'Unspecified')
                if ibd != 'Unspecified':
                    if ibd in {"Ileal Crohn's Disease",
                               "Colonic Crohn's Disease",
                               "Ileal and Colonic Crohn's Disease"}:
                        md[1][barcode]['IBD_DIAGNOSIS'] = "Crohn's disease"
                    elif ibd == 'Ulcerative colitis':
                        md[1][barcode]['IBD_DIAGNOSIS'] = 'Ulcerative colitis'

                # Add categorization columns
                md[1][barcode]['ALCOHOL_CONSUMPTION'] = categorize_etoh(
                    md[1][barcode]['ALCOHOL_FREQUENCY'])
                md[1][barcode]['BMI_CAT'] = categorize_bmi(
                    md[1][barcode]['BMI'])
                md[1][barcode]['BMI_CORRECTED'] = correct_bmi(
                    md[1][barcode]['BMI'])
                md[1][barcode]['COLLECTION_SEASON'] = season_lookup[
                    bc_info['sample_date'].month]
                state = md[1][barcode]['STATE']
                try:
                    md[1][barcode]['CENSUS_REGION'] = \
                        regions_by_state[state]['Census_1']
                    md[1][barcode]['ECONOMIC_REGION'] = \
                        regions_by_state[state]['Economic']
                except KeyError:
                    md[1][barcode]['CENSUS_REGION'] = 'Unspecified'
                    md[1][barcode]['ECONOMIC_REGION'] = 'Unspecified'
                md[1][barcode]['SUBSET_AGE'] = \
                    19 < md[1][barcode]['AGE_YEARS'] < 70 and \
                    not md[1][barcode]['AGE_YEARS'] == 'Unspecified'
                md[1][barcode]['SUBSET_DIABETES'] = \
                    (md[1][barcode]['DIABETES'] ==
                        'I do not have this condition')
                md[1][barcode]['SUBSET_IBD'] = \
                    md[1][barcode]['IBD'] == 'I do not have this condition'
                md[1][barcode]['SUBSET_ANTIBIOTIC_HISTORY'] = \
                    (md[1][barcode]['ANTIBIOTIC_HISTORY'] ==
                     'I have not taken antibiotics in the past year.')
                md[1][barcode]['SUBSET_BMI'] = \
                    18.5 <= md[1][barcode]['BMI'] < 30 and \
                    not md[1][barcode]['BMI'] == 'Unspecified'
                md[1][barcode]['SUBSET_HEALTHY'] = all([
                    md[1][barcode]['SUBSET_AGE'],
                    md[1][barcode]['SUBSET_DIABETES'],
                    md[1][barcode]['SUBSET_IBD'],
                    md[1][barcode]['SUBSET_ANTIBIOTIC_HISTORY'],
                    md[1][barcode]['SUBSET_BMI']])
                md[1][barcode]['COLLECTION_MONTH'] = month_str_lookup.get(
                    bc_info['sample_date'].month, 'Unspecified')
                md[1][barcode]['AGE_CORRECTED'] = correct_age(
                    md[1][barcode]['AGE_YEARS'], md[1][barcode]['HEIGHT_CM'],
                    md[1][barcode]['WEIGHT_KG'],
                    md[1][barcode]['ALCOHOL_CONSUMPTION'])
                md[1][barcode]['AGE_CAT'] = categorize_age(
                    md[1][barcode]['AGE_CORRECTED'])

                # make sure conversions are done
                if md[1][barcode]['WEIGHT_KG'] != 'Unspecified':
                    md[1][barcode]['WEIGHT_KG'] = int(
                        md[1][barcode]['WEIGHT_KG'])
                if md[1][barcode]['HEIGHT_CM'] != 'Unspecified':
                    md[1][barcode]['HEIGHT_CM'] = int(
                        md[1][barcode]['HEIGHT_CM'])
                if md[1][barcode]['BMI'] != 'Unspecified':
                    md[1][barcode]['BMI'] = '%.2f' % md[1][barcode]['BMI']

                # Get rid of columns not wanted for pulldown
                if not full:
                    for col in ebi_remove:
                        try:
                            del md[1][barcode][col]
                        except KeyError:
                            # Column doesn't exist already for survey
                            # (retired), so no removal needed
                            pass

                # Add the external surveys
                if unknown_external:
                    md[1][barcode].update(external.get(md[1][barcode][
                        'SURVEY_ID'], unknown_external))
            except Exception as e:
                # Add barcode to error and remove from metadata info
                errors[barcode] = str(e)
                del md[1][barcode]
        return md, errors

    def format_environmental(self, barcodes):
        """Format the environemntal data pulldown metadata

        Parameters
        ----------
        barcodes : list of (barcode, env sampled)
            List of tuples of barcode and the environment sampled

        Returns
        -------
        str
            Formatted tsv metadata for the environmental samples
        """
        md = {}
        errors = {}
        barcode_info = self.get_ag_barcode_details(
            [b[0][:9] for b in barcodes])
        # tuples are latitude, longitude, elevation, state
        zipcode_sql = """SELECT UPPER(zipcode), country,
                             round(latitude::numeric, 1),
                             round(longitude::numeric,1),
                             round(elevation::numeric, 1), state
                         FROM zipcodes"""
        zip_lookup = defaultdict(dict)
        for row in self._con.execute_fetchall(zipcode_sql):
            zip_lookup[row[0]][row[1]] = map(
                lambda x: x if x is not None else 'Unspecified', row[2:])

        country_sql = "SELECT country, EBI from ag.iso_country_lookup"
        country_lookup = dict(self._con.execute_fetchall(country_sql))
        # Add for scrubbed testing database
        country_lookup['REMOVED'] = 'REMOVED'

        for barcode, env in barcodes:
            # Not using defaultdict so we don't ever allow accidental insertion
            # of unknown barcodes
            md[barcode] = {}
            # Add info from constants dict
            try:
                md[barcode].update(env_lookup[env])
                # Invariant information
                md[barcode]['TITLE'] = 'American Gut Project'
                md[barcode]['ASSIGNED_FROM_GEO'] = 'Yes'
                md[barcode]['PHYSICAL_SPECIMEN_REMAINING'] = 'Yes'
                md[barcode]['PHYSICAL_SPECIMEN_LOCATION'] = 'UCSDMI'

                # Barcode specific information
                specific_info = barcode_info[barcode[:9]]

                md[barcode]['ANONYMIZED_NAME'] = barcode
                md[barcode]['HOST_SUBJECT_ID'] = barcode

                # Geolocate based on kit information, since no other
                # geographic info available
                zipcode = specific_info['zip'].upper()
                country = specific_info['country']
                md[barcode] = self._geocode(md[barcode], zipcode, country,
                                            zip_lookup, country_lookup)

                md[barcode]['COLLECTION_DATE'] = \
                    specific_info['sample_date'].strftime('%m/%d/%Y')

                if specific_info['sample_time']:
                    md[barcode]['COLLECTION_TIME'] = \
                        specific_info['sample_time'].strftime('%H:%M')
                else:
                    # If no time data, show unspecified and default to midnight
                    md[barcode]['COLLECTION_TIME'] = 'Unspecified'
                    specific_info['sample_time'] = time(0, 0)

                md[barcode]['COLLECTION_TIMESTAMP'] = datetime.combine(
                    specific_info['sample_date'],
                    specific_info['sample_time']).strftime('%m/%d/%Y %H:%M')
            except Exception as e:
                del md[barcode]
                errors[barcode] = str(e)
                continue
        return md, errors

    def participant_names(self):
        """Retrieve the participant names for the given barcodes

        Returns
        -------
        list of tuple
            (barcode, participant name)
        """
        sql = """SELECT barcode, participant_name
                 FROM ag.ag_kit_barcodes
                 JOIN ag.ag_login_surveys USING (survey_id)
                 WHERE participant_name IS NOT NULL"""
        return self._con.execute_fetchall(sql)

    def _convert_header(self, survey, header):
        return converter.camel_to_snake('_'.join(
            [survey.replace(' ', '_'), header])).upper()

    def pulldown(self, barcodes, blanks=None, external=None,  # noqa
                 full=False):
        """Pulls down AG metadata for given barcodes

        Parameters
        ----------
        barcodes : list of str
            Barcodes to pull metadata down for
        blanks : list of str, optional
            Names for the blanks to add. Default None
            Blanks added to survey 1
        external : list of str, optional
            External surveys to add to the pulldown, default None
        full : bool, optional
            If True do a full pulldown, otherwise do an EBI-cleaned pulldown.
            Default False.

        Returns
        -------
        metadata : dict of str
            Tab delimited qiita sample template, keyed to survey ID it came
            from
        failures : dict
            Barcodes unable to pull metadata down, in the form
            {barcode: reason, ...}
        """
        all_results = {}
        errors = {}
        all_survey_info = self.get_surveys(barcodes)
        if len(all_survey_info) > 0:
            all_results, errors = self.format_survey_data(all_survey_info,
                                                          external, full)

        # Do the pulldown for the environmental samples
        sql = """SELECT barcode, environment_sampled
                 FROM ag.ag_kit_barcodes
                 WHERE environment_sampled IS NOT NULL
                     AND environment_sampled != ''
                     AND barcode IN %s"""
        env_barcodes = self._con.execute_fetchall(sql, [tuple(barcodes)])
        barcodes.extend([b[0] for b in env_barcodes])

        # Set up sql for getting all survey question shortnames
        header_sql = """SELECT DISTINCT question_shortname
                        FROM ag.survey_question
                        JOIN ag.group_questions USING (survey_question_id)
                        JOIN ag.surveys USING (survey_group)
                        WHERE survey_id = %s"""

        ext_survey_sql = """SELECT DISTINCT json_object_keys(answers)
                            FROM ag.external_survey_answers
                            JOIN ag.external_survey_sources
                                USING (external_survey_id)
                            WHERE external_survey = %s"""

        # keep track of which barcodes were seen so we know which weren't
        barcodes_seen = set()
        metadata = {}
        for survey, bc_responses in all_results.items():
            if not bc_responses:
                continue
            # Get the headers for the survey, then union with ones added during
            # pulldown formatting
            headers = set(x[0] for x in
                          self._con.execute_fetchall(header_sql, [survey]))
            headers = headers.union(bc_responses.values()[0])
            # Add external survey headers to the human survey answers
            if survey == 1 and external is not None:
                for ext in external:
                    # get all external survey headers and format them
                    ext_headers = self._con.execute_fetchall(
                        ext_survey_sql, [ext])
                    headers.union(self._convert_header(ext, h[0])
                                  for h in ext_headers)
            # Remove the ebi prohibited columns
            headers = headers.difference(ebi_remove)
            headers = sorted(headers)
            survey_md = [''.join(['sample_name\t', '\t'.join(headers)])]

            for barcode, shortnames_answers in sorted(bc_responses.items()):
                barcodes_seen.add(barcode)
                oa_hold = [barcode]
                for h in headers:
                    # Take care of retired questions not having an answer
                    answer = shortnames_answers.get(h, 'Unspecified')
                    # Convert everything to utf-8 unicode for standardization
                    converted = self._unicode_convert(answer)
                    oa_hold.append(converted)
                survey_md.append('\t'.join(oa_hold))
            if survey == 1 and blanks:
                # only add blanks to human survey sample data
                for blank in blanks:
                    blanks_copy = copy(blanks_values)
                    blanks_copy['ANONYMIZED_NAME'] = blank
                    blanks_copy['HOST_SUBJECT_ID'] = blank
                    survey_md.append(
                        '\t'.join([blank] + [blanks_copy[h]
                                             for h in headers]))
            metadata[survey] = '\n'.join(survey_md).encode('utf-8')

        if len(env_barcodes) > 0:
            all_results['env'], err = self.format_environmental(env_barcodes)
            for b in all_results['env']:
                barcodes_seen.add(b)
            errors.update(err)

        failures = set(barcodes) - barcodes_seen
        failures = self._explain_pulldown_failures(failures)
        failures.update(errors)
        return metadata, failures

    def _unicode_convert(self, value):
        """Convert given value to unicode string"""
        if isinstance(value, unicode):
            converted = value
        elif isinstance(value, str):
            converted = unicode(value, 'utf-8')
        else:
            converted = unicode(str(value), 'utf-8')
        converted = re.sub(r"\t|\r|\n|\s+", " ", converted)
        return converted

    def check_consent(self, barcodes):
        """Gets barcodes with consent, and failure reasons for ones without

        Parameters
        ----------
        barcodes : list of str
            Barcodes to check for consent

        Returns
        -------
        consented : list of str
            Barcodes with consent
        failures : dict
            Barcodes unable to pull metadata down, in the form
            {barcode: reason, ...}
        """
        sql = """SELECT barcode
                 FROM ag.ag_kit_barcodes
                 WHERE barcode in %s AND survey_id IS NOT NULL"""
        consented = [x[0] for x in
                     self._con.execute_fetchall(sql, [tuple(barcodes)])]

        failures = set(barcodes).difference(consented)

        return consented, self._explain_pulldown_failures(failures)

    def _explain_pulldown_failures(self, barcodes):
        """Builds failure reason list for barcodes passed

        Parameters
        ----------
        barcodes : list of str
            Barcodes to explain failure for

        Returns
        -------
        dict
            failure reasons in the form {barcode: reason, ...}
        """
        # if empty list passed, don't touch database
        if len(barcodes) == 0:
            return {}

        def update_reason_and_remaining(sql, reason, failures, remaining):
            failures.update(
                {bc[0]: reason for bc in
                 self._con.execute_fetchall(sql, [tuple(remaining)])})
            return remaining.difference(failures)

        fail_reason = {}
        remaining = set(barcodes)
        # TEST ORDER HERE MATTERS! Assumptions made based on filtering of
        # curent_barcodes by previous checks
        # not an AG barcode
        sql = """SELECT barcode
                 FROM ag.ag_kit_barcodes
                 WHERE barcode IN %s
                 UNION
                 SELECT barcode
                 FROM ag.ag_handout_barcodes
                 WHERE barcode IN %s"""
        hold = {x[0] for x in
                self._con.execute_fetchall(
                    sql, [tuple(remaining)] * 2)}
        fail_reason.update({bc: 'Not an AG barcode' for bc in
                            remaining.difference(hold)})
        remaining = hold
        # No more unexplained, so done
        if len(remaining) == 0:
            return fail_reason

        # handout barcode
        sql = """SELECT barcode
                 FROM ag.ag_handout_barcodes
                 WHERE barcode IN %s"""
        remaining = update_reason_and_remaining(
            sql, 'Unassigned handout kit barcode', fail_reason, remaining)
        # No more unexplained, so done
        if len(remaining) == 0:
            return fail_reason

        # withdrawn
        sql = """SELECT barcode
                 FROM ag.ag_kit_barcodes
                 WHERE withdrawn = 'Y' AND barcode in %s"""
        remaining = update_reason_and_remaining(
            sql, 'Withdrawn sample', fail_reason, remaining)
        # No more unexplained, so done
        if len(remaining) == 0:
            return fail_reason

        # sample not logged
        sql = """SELECT barcode
                 FROM ag.ag_kit_barcodes
                 WHERE sample_date IS NULL AND barcode in %s"""
        remaining = update_reason_and_remaining(
            sql, 'Sample not logged', fail_reason, remaining)
        # No more unexplained, so done
        if len(remaining) == 0:
            return fail_reason

        # Sample not consented
        sql = """SELECT barcode
                 FROM ag.ag_kit_barcodes
                 WHERE survey_id IS NULL AND barcode in %s"""
        remaining = update_reason_and_remaining(
            sql, 'Sample logged without consent', fail_reason, remaining)
        # No more unexplained, so done
        if len(remaining) == 0:
            return fail_reason

        # other
        fail_reason.update({bc: 'Unknown reason' for bc in remaining})
        return fail_reason

    def _hash_password(self, password, hashedpw=None):
        """Hashes password

        Parameters
        ----------
        password: str
            Plaintext password
        hashedpw: str, optional
            Previously hashed password for bcrypt to pull salt from. If not
            given, salt generated before hash

        Returns
        -------
        str
            Hashed password

        Notes
        -----
        Relies on bcrypt library to hash passwords, which stores the salt as
        part of the hashed password. Don't need to actually store the salt
        because of this.
        """
        # all the encode/decode as a python 3 workaround for bcrypt
        if hashedpw is None:
            hashedpw = gensalt()
        else:
            hashedpw = hashedpw.encode('utf-8')
        password = password.encode('utf-8')
        output = hashpw(password, hashedpw)
        if isinstance(output, bytes):
            output = output.decode("utf-8")
        return output

    def authenticate_user(self, email, password):
        # see if user exists
        sql = """SELECT EXISTS (SELECT email FROM ag.labadmin_users
                 WHERE email = %s)"""
        exists = self._con.execute_fetchone(sql, [email])[0]

        if not exists:
            raise IncorrectEmailError("Email not valid: %s" % email)

        # pull password out of database
        sql = "SELECT password FROM ag.labadmin_users WHERE email = %s"

        # verify password
        dbpass = self._con.execute_fetchone(sql, [email])
        dbpass = dbpass[0] if dbpass else ''
        hashed = self._hash_password(password, dbpass)

        if hashed == dbpass:
            return True
        else:
            raise IncorrectPasswordError("Password not valid!")

        return False

    def get_unconsented(self):
        """Returns unconsented barcode and person's email

        Returns
        -------
        list of (str, datetime.date, str)
            Unconsented barcodes, as [(barcode, scan_date, email), ...]
        """
        sql = """SELECT DISTINCT barcode, scan_date, email
                 FROM ag.ag_kit_barcodes
                 JOIN barcodes.barcode USING (barcode)
                 JOIN ag.ag_kit USING (ag_kit_id)
                 JOIN ag.ag_login USING (ag_login_id)
                 WHERE survey_id IS NULL AND scan_date IS NOT NULL
                 ORDER BY barcode"""
        return self._con.execute_fetchall(sql)

    def getAGKitDetails(self, supplied_kit_id):
        sql = """SELECT
                 cast(ag_kit_id AS varchar(100)) AS ag_kit_id, supplied_kit_id,
                 kit_password, swabs_per_kit, kit_verification_code,
                 kit_verified, verification_email_sent
                 FROM ag_kit
                 WHERE supplied_kit_id = %s"""
        res = self._con.execute_fetchone(sql, [supplied_kit_id])
        if res is not None:
            return dict(res)
        else:
            return {}

    def add_barcodes_to_kit(self, ag_kit_id, num_barcodes=1):
        """Attaches barcodes to an existing american gut kit

        Parameters
        ----------
        ag_kit_id : str
            Kit ID to attach barcodes to
        num_barcodes : int, optional
            Number of barcodes to attach. Default 1

        Returns
        -------
        barcodes : list of str
            Barcodes attached to the kit
        """
        barcodes = self.get_unassigned_barcodes(num_barcodes)
        # assign barcodes to projects for the kit
        sql = """SELECT DISTINCT project_id FROM barcodes.project_barcode
                 JOIN ag.ag_kit_barcodes USING (barcode)
                 WHERE ag_kit_id = %s"""
        proj_ids = [x[0] for x in self._con.execute_fetchall(sql, [ag_kit_id])]
        barcode_project_insert = """INSERT INTO project_barcode
                                    (barcode, project_id)
                                    VALUES (%s, %s)"""
        project_inserts = []
        for barcode in barcodes:
            for project in proj_ids:
                project_inserts.append((barcode, project))
        self._con.executemany(barcode_project_insert, project_inserts)

        # Add barcodes to the kit
        sql = """INSERT  INTO ag_kit_barcodes
                (ag_kit_id, barcode, sample_barcode_file)
                VALUES (%s, %s, %s || '.jpg')"""
        barcode_info = [[ag_kit_id, b, b] for b in barcodes]
        self._con.executemany(sql, barcode_info)
        return barcodes

    def create_ag_kits(self, swabs_kits, tag=None, projects=None):
        """ Creates american gut handout kits on the database

        Parameters
        ----------
        swabs_kits : list of tuples
            kits and swab counts, with tuples in the form
            (# of swabs, # of kits with this swab count)
        tag : str, optional
            Tag to add to kit IDs. Default None
        projects : list of str, optional
            Subprojects to attach to, if given. Default None.

        Returns
        -------
        list of namedtuples
            The new kit information, in the form
            [(kit_id, password, verification_code, (barcode, barcode,...)),...]
        """
        # make sure we have enough barcodes
        total_swabs = sum(s * k for s, k in swabs_kits)
        barcodes = self.get_unassigned_barcodes(total_swabs)

        # Assign barcodes to AG and any other subprojects
        if projects is None:
            projects = ["American Gut Project"]
        else:
            if "American Gut Project" not in projects:
                projects.append("American Gut Project")
        self.assign_barcodes(total_swabs, projects)

        kits = []
        kit_barcode_inserts = []
        kit_inserts = []
        start = 0
        KitTuple = namedtuple('AGKit', ['kit_id', 'password',
                              'verification_code', 'barcodes'])
        # build the kits information and the sql insert information
        for num_swabs, num_kits in swabs_kits:
            kit_ids = make_valid_kit_ids(num_kits, self.get_used_kit_ids(),
                                         tag=tag)
            for i in range(num_kits):
                ver_code = make_verification_code()
                password = make_passwd()
                kit_bcs = tuple(barcodes[start:start + num_swabs])
                start += num_swabs
                kits.append(KitTuple(kit_ids[i], password, ver_code, kit_bcs))
                kit_inserts.append((kit_ids[i],
                                    self._hash_password(password),
                                    ver_code, num_swabs))
                for barcode in kit_bcs:
                    kit_barcode_inserts.append((kit_ids[i], barcode, barcode))

        # Insert kits, followed by barcodes attached to the kits
        kit_sql = """INSERT INTO ag_handout_kits
                     (kit_id, password, verification_code, swabs_per_kit)
                     VALUES (%s, %s, %s, %s)"""
        kit_barcode_sql = """INSERT INTO ag_handout_barcodes
                             (kit_id, barcode, sample_barcode_file)
                             VALUES(%s, %s, %s || '.jpg')"""

        self._con.executemany(kit_sql, kit_inserts)
        self._con.executemany(kit_barcode_sql, kit_barcode_inserts)

        return kits

    def get_used_kit_ids(self):
        """Grab in use kit IDs, return set of them
        """
        sql = """SELECT supplied_kit_id FROM ag_kit
                 UNION
                 SELECT kit_id from ag_handout_kits"""

        return set(i[0] for i in self._con.execute_fetchall(sql))

    def create_project(self, name):
        if name.strip() == '':
            raise ValueError("Project name can not be blank!")
        sql = "SELECT EXISTS(SELECT * FROM project WHERE project = %s)"
        exists = self._con.execute_fetchone(sql, [name])[0]
        if exists:
                raise ValueError("Project %s already exists!" % name)

        sql = """INSERT INTO project (project_id, project)
                 SELECT max(project_id)+1, %s FROM project"""
        self._con.execute(sql, [name])

    def get_unassigned_barcodes(self, n=None):
        """Returns unassigned barcodes

        Parameters
        ----------
        n : int, optional
            Number of barcodes to limit to, default returns all unused

        Returns
        -------
        list
            unassigned barcodes

        Raises
        ------
        ValueError
            Not enough unnasigned barcodes for n

        Notes
        -----
        Barcodes are returned in ascending order
        """
        sql_args = None
        sql = """SELECT DISTINCT barcode FROM barcodes.barcode
                 LEFT JOIN barcodes.project_barcode pb USING (barcode)
                 WHERE pb.barcode IS NULL
                 ORDER BY barcode ASC"""
        if n is not None:
            sql += " LIMIT %s"
            sql_args = [n]
        barcodes = [x[0] for x in self._con.execute_fetchall(sql, sql_args)]
        if len(barcodes) < n:
            raise ValueError("Not enough barcodes! %d asked for, %d remaining"
                             % (n, len(barcodes)))
        return barcodes

    def assign_barcodes(self, num_barcodes, projects):
        """Assign a given number of barcodes to projects

        Parameters
        ----------
        num_barcodes : int
            Number of barcodes to assign
        projects : list of str
            Projects to assgn barcodes to

        Returns
        -------
        list of str
            Barcodes assigned to the projects

        Raises
        ------
        ValueError
            One or more projects given don't exist in the database
        """
        # Verify projects given exist
        sql = "SELECT project FROM project"
        existing = {x[0] for x in self._con.execute_fetchall(sql)}
        not_exist = {p for p in projects if p not in existing}
        if not_exist:
            raise ValueError("Project(s) given don't exist in database: %s"
                             % ', '.join(not_exist))

        # Get unassigned barcode list and make sure we have enough barcodes
        barcodes = self.get_unassigned_barcodes(num_barcodes)

        # Assign barcodes to the project(s)
        sql = "SELECT project_id from project WHERE project in %s"
        proj_ids = [x[0] for x in
                    self._con.execute_fetchall(sql, [tuple(projects)])]

        barcode_project_insert = """INSERT INTO project_barcode
                                    (barcode, project_id)
                                    VALUES (%s, %s)"""
        project_inserts = []
        for barcode in barcodes:
            for project in proj_ids:
                project_inserts.append((barcode, project))
        self._con.executemany(barcode_project_insert, project_inserts)
        # Set assign date for the barcodes
        sql = """UPDATE barcodes.barcode
                 SET assigned_on = NOW() WHERE barcode IN %s"""
        self._con.execute(sql, [tuple(barcodes)])
        return barcodes

    def create_barcodes(self, num_barcodes):
        """Creates new barcodes

        Parameters
        ----------
        num_barcodes : int
            Number of barcodes to create

        Returns
        -------
        list
            New barcodes created
        """

        # Get newest barcode as an integer
        sql = "SELECT max(barcode::integer) from barcode"
        newest = self._con.execute_fetchone(sql)[0]

        # create new barcodes by padding integers with zeros
        barcodes = ['%09d' % b for b in range(newest+1, newest+1+num_barcodes)]

        barcode_insert = """INSERT INTO barcode (barcode, obsolete)
                            VALUES (%s, 'N')"""
        self._con.executemany(barcode_insert, [[b] for b in barcodes])
        return barcodes

    def get_barcodes_for_projects(self, projects, limit=None):
        """Gets barcode information for barcodes belonging to projects

        Parameters
        ----------
        projects : list of str
            Projects to get barcodes for (if multiple given, intersection of
            barcodes in each project is returned)
        limit : int, optional
            Number of barcodes to return, starting with most recent
            (default all)

        Returns
        -------
        list of dict
            each barcode with information
        """
        select_sql = """SELECT barcode, create_date_time, sample_postmark_date,
                        scan_date,status,sequencing_status,biomass_remaining,
                        obsolete,array_agg(project) AS projects
                        FROM barcode
                        JOIN project_barcode USING (barcode)
                        JOIN project USING (project_id)
                        WHERE project IN %s GROUP BY barcode
                        ORDER BY barcode DESC"""
        sql_args = [tuple(projects)]
        if limit is not None:
            select_sql += " LIMIT %s"
            sql_args.append(limit)
        return self._con.execute_fetchall(select_sql, sql_args)

    def add_external_survey(self, survey, description, url):
        """Adds a new external survey to the database

        Parameters
        ----------
        survey : str
            Name of the external survey
        description : str
            Short description of what the survey is about
        url : str
            URL for the external survey

        Raises
        ------
        ValueError
            survey already exists in DB
        """
        sql = """SELECT EXISTS(
                    SELECT external_survey
                    FROM ag.external_survey_sources
                    WHERE external_survey = %s)"""
        if self._con.execute_fetchone(sql, [survey])[0]:
            raise ValueError("Survey '%s' already exists" % survey)

        sql = """INSERT INTO ag.external_survey_sources
                 (external_survey, external_survey_description,
                  external_survey_url)
                 VALUES (%s, %s, %s)
                 RETURNING external_survey_id"""
        return self._con.execute_fetchone(sql, [survey, description, url])[0]

    def list_external_surveys(self):
        """Returns list of external survey names

        Returns
        -------
        list of str
            Third party survey names
        """
        sql = """SELECT external_survey
                 FROM ag.external_survey_sources"""
        return [x[0] for x in self._con.execute_fetchall(sql)]

    def store_external_survey(self, in_file, ext_survey, pulldown_date=None,
                              separator="\t", survey_id_col="survey_id",
                              trim=None):
        """Stores third party survey answers in the database

        Parameters
        ----------
        in_file : open file or StringIO
            File with survey spreadsheet
        external_survey_urlsurvey : str
            What third party survey this belongs to
        pulldown_date : datetime object, optional
            When the data was pulled from the external source, default now()
        separator : str, optional
            What separator is used, default tab
        survey_id_col : str
            What column header holds the associated user AG survey id
            Default 'survey_id'
        trim : str
            Regex to trim the survey id column, using re.sub(trim, '', sid)
            Default None

        Returns
        -------
        count : int
            Number of rows inserted

        Raises
        ------
        ValueError
            Survey passed is not found
        """
        # Get the external survey ID
        sql = """SELECT external_survey_id
                 FROM external_survey_sources
                 WHERE external_survey = %s"""
        external_id = self._con.execute_fetchone(sql, [ext_survey])
        if not external_id:
            raise ValueError("Unknown external survey: %s" % ext_survey)
        external_id = external_id[0]
        if pulldown_date is None:
            pulldown_date = datetime.now()

        # Load file data into insertable json format
        header = in_file.readline().strip().split(separator)
        inserts = []
        for line in in_file:
            hold = {h: v.strip('"\'[]_,\t\r\n\\/ ') for h, v in
                    zip(header, line.split(separator))}

            sid = hold[survey_id_col]
            if trim is not None:
                sid = re.sub(trim, '', sid)
            del hold[survey_id_col]
            inserts.append([sid, external_id, pulldown_date,
                            json.dumps(hold)])

        # insert into the database
        sql = """INSERT INTO ag.external_survey_answers
                 (survey_id, external_survey_id, pulldown_date, answers)
                 VALUES (%s, %s, %s, %s)"""
        self._con.executemany(sql, inserts)
        return len(inserts)

    def get_external_survey(self, survey, survey_ids, pulldown_date=None):
        """Get the answers to a survey for given survey IDs

        Parameters
        ----------
        survey : str
            Survey to retrieve answers for
        survey_ids : list of str
            AG survey ids to retrieve answers for
        pulldown_date : datetime object, optional
            Specific pulldown date to limit answers to, default None

        Returns
        -------
        dict of dicts
            Answers to the survey keyed to the given survey IDs, in the form
            {survey_id: {header1: answer, header2: answer, ...}, ...}

        Notes
        -----
        If there are multiple pulldowns for a given survey_id, the newest one
        will be returned.
        """
        # Do pulldown of ids and answers, ordered so newest comes out last
        # This allows you to not specify pulldown date and still get newest
        # answers for the survey
        sql = """SELECT survey_id, answers FROM
                 (SELECT * FROM ag.external_survey_answers
                 JOIN ag.external_survey_sources USING (external_survey_id)
                 WHERE external_survey = %s AND survey_id IN %s{0}
                 ORDER BY pulldown_date ASC) AS A"""
        sql_args = [survey, tuple(survey_ids)]
        format_str = ""
        if pulldown_date is not None:
            format_str = " AND pulldown_date = %s "
            sql_args.append(pulldown_date)

        info = self._con.execute_fetchall(sql.format(format_str), sql_args)
        if info:
            return {s: a for s, a in info}
        else:
            return {}

    def addAGLogin(self, email, name, address, city, state, zip_, country):
        clean_email = email.strip().lower()
        sql = "select ag_login_id from ag_login WHERE LOWER(email) = %s"
        ag_login_id = self._con.execute_fetchone(sql, [clean_email])
        if not ag_login_id:
            # create the login
            sql = ("INSERT INTO ag_login (email, name, address, city, state, "
                   "zip, country) VALUES (%s, %s, %s, %s, %s, %s, %s) "
                   "RETURNING ag_login_id")
            ag_login_id = self._con.execute_fetchone(
                sql, [clean_email, name, address, city, state, zip_, country])
        return ag_login_id[0]

    def updateAGLogin(self, ag_login_id, email, name, address, city, state,
                      zipcode, country):
        sql = """UPDATE  ag_login
                SET email = %s, name = %s, address = %s, city = %s, state = %s,
                    zip = %s, country = %s
                WHERE ag_login_id = %s"""
        self._con.execute(sql, [email.strip().lower(), name,
                                address, city, state, zipcode, country,
                                ag_login_id])

    def updateAGBarcode(self, barcode, ag_kit_id, site_sampled,
                        environment_sampled, sample_date, sample_time,
                        participant_name, notes, refunded, withdrawn):
        # Get survey ID for participant if needed
        if participant_name:
            ag_login_id = self.search_kits(ag_kit_id)[0]
            sql = """SELECT survey_id
                     FROM ag_login_surveys
                     WHERE participant_name = %s AND ag_login_id = %s"""
            survey_id = self._con.execute_fetchone(
                sql, [participant_name, ag_login_id])[0]
        else:
            survey_id = None
            participant_name = None

        # convert empty strings to None for DB consistency
        site_sampled = site_sampled or None
        environment_sampled = environment_sampled or None
        sample_date = sample_date or None
        sample_time = sample_time or None
        notes = notes or None

        sql = """UPDATE  ag_kit_barcodes
                 SET ag_kit_id = %s,
                     site_sampled = %s,
                     environment_sampled = %s,
                     sample_date = %s,
                     sample_time = %s,
                     notes = %s,
                     refunded = %s,
                     withdrawn = %s,
                     survey_id = %s
                 WHERE barcode = %s"""
        self._con.execute(sql, [ag_kit_id, site_sampled, environment_sampled,
                                sample_date, sample_time,
                                notes, refunded, withdrawn, survey_id,
                                barcode])

    def AGGetBarcodeMetadata(self, barcode):
        results = self._con.execute_proc_return_cursor(
            'ag_get_barcode_metadata', [barcode])
        rows = results.fetchall()
        results.close()

        return [dict(row) for row in rows]

    def AGGetBarcodeMetadataAnimal(self, barcode):
        results = self._con.execute_proc_return_cursor(
            'ag_get_barcode_md_animal', [barcode])
        rows = results.fetchall()
        results.close()

        return [dict(row) for row in rows]

    def get_geocode_zipcode(self, zipcode, country):
        """Adds geocode information to zipcode table if needed and return info

        Parameters
        ----------
        zipcode : str
            Zipcode to geocode
        country : str, optional
            Country zipcode belongs in. Default infer from zipcode. Useful
            for countries with zipcode formated like USA

        Returns
        -------
        info : NamedTuple
            Location namedtuple in form
            Location('zip', 'lat', 'long', 'elev', 'city', 'state', 'country')

        Notes
        -----
        If the tuple contains nothing but the zipcode and None for all other
        fields, no geocode was found. Zipcode/country combination added as
        'cannot_geocode'
        """
        # Catch sending None or empty string for these
        if not zipcode or not country:
            return Location(zipcode, None, None, None,
                            None, None, None, country)

        info = geocode('%s %s' % (zipcode, country))
        cannot_geocode = False
        # Clean the zipcode so it is same case and setup, since international
        # people can enter lowercased zipcodes or missing spaces, and google
        # does not give back 9 digit zipcodes for USA, only 6.
        clean_postcode = str(info.postcode).lower().replace(' ', '')
        clean_zipcode = str(zipcode).lower().replace(' ', '').split('-')[0]
        if not info.lat:
            cannot_geocode = True
        # Use startswith because UK zipcodes can be 2, 3, or 6 characters
        elif (info.country != country or
              not clean_postcode.startswith(clean_zipcode)):
            # countries and zipcodes dont match, so blank out info
            info = Location(zipcode, None, None, None,
                            None, None, None, country)
            cannot_geocode = True
        sql = """INSERT INTO ag.zipcodes
                    (zipcode, latitude, longitude, elevation, city,
                     state, country, cannot_geocode)
                 VALUES (%s,%s,%s,%s,%s,%s,%s, %s)"""
        self._con.execute(sql, [zipcode, info.lat, info.long, info.elev,
                                info.city, info.state, country,
                                cannot_geocode])
        return info

    def addGeocodingInfo(self, limit=None, retry=False):
        """Adds latitude, longitude, and elevation to ag_login_table

        Uses the city, state, zip, and country from the database to retrieve
        lat, long, and elevation from the google maps API.

        If any of that information cannot be retrieved, then cannot_geocode
        is set to 'y' in the ag_login table, and it will not be tried again
        on subsequent calls to this function.  Pass retry=True to retry all
        (or maximum of limit) previously failed geocodings.
        """

        # clear previous geocoding attempts if retry is True
        if retry:
            sql = """UPDATE  ag_login
                     SET latitude = %s,
                         longitude = %s,
                         elevation = %s,
                         cannot_geocode = %s
                     WHERE ag_login_id IN (
                        SELECT ag_login_id FROM ag_login
                        WHERE cannot_geocode = 'y')"""
            self._con.execute(sql)

        # get logins that have not been geocoded yet
        sql = """SELECT city, state, zip, country,
                        cast(ag_login_id as varchar(100))
                 FROM ag_login
                 WHERE elevation is NULL AND cannot_geocode is NULL"""
        logins = self._con.execute_fetchall(sql)

        row_counter = 0
        sql_args = []
        for city, state, zipcode, country, ag_login_id in logins:
            row_counter += 1
            if limit is not None and row_counter > limit:
                break

            # Attempt to geocode
            address = '{0} {1} {2} {3}'.format(city, state, zipcode, country)
            try:
                info = geocode(address)
                # empty string to indicate geocode was successful
                sql_args.append([info.lat, info.long, info.elev,
                                 '', ag_login_id])
            except GoogleAPILimitExceeded:
                # limit exceeded so no use trying to keep geocoding
                break
            except:
                # Catch ANY other error and set to could not geocode
                sql_args.append([None, None, None, 'y', ag_login_id])

        sql = """UPDATE  ag_login
                 SET latitude = %s,
                     longitude = %s,
                     elevation = %s,
                 cannot_geocode = %s
                 WHERE ag_login_id = %s"""
        self._con.executemany(sql, sql_args)

    def getGeocodeStats(self):
        stat_queries = [
            ("Total Rows",
             "select count(*) from ag_login"),
            ("Cannot Geocode",
             "select count(*) from ag_login where cannot_geocode = 'y'"),
            ("Null Latitude Field",
             "select count(*) from ag_login where latitude is null"),
            ("Null Elevation Field",
             "select count(*) from ag_login where elevation is null")
        ]
        results = []
        for name, sql in stat_queries:
            total = self._con.execute_fetchone(sql)[0]
            results.append((name, total))
        return results

    def getAGStats(self):
        # returned tuple consists of:
        # site_sampled, sample_date, sample_time, participant_name,
        # environment_sampled, notes
        stats_list = [
            ('Total handout kits',
             'SELECT count(*) FROM ag.ag_handout_kits'),
            ('Total handout barcodes',
             'SELECT count(*) FROM ag.ag_handout_barcodes'),
            ('Total consented participants',
             'SELECT count(*) FROM ag.ag_consent'),
            ('Total registered kits',
             'SELECT count(*) FROM ag.ag_kit'),
            ('Total registered barcodes',
             'SELECT count(*) FROM ag.ag_kit_barcodes'),
            ('Total barcodes with results',
             """SELECT count(*) FROM ag.ag_kit_barcodes
             WHERE results_ready='Y'"""),
            ('Average age of participants',
             """SELECT AVG(AGE((yr.response || '-' ||
                CASE mo.response
                    WHEN 'January' THEN '1'
                    WHEN 'February' THEN '2'
                    WHEN 'March' THEN '3'
                    WHEN 'April' THEN '4'
                    WHEN 'May' THEN '5'
                    WHEN 'June' THEN '6'
                    WHEN 'July' THEN '7'
                    WHEN 'August' THEN '8'
                    WHEN 'September' THEN '9'
                    WHEN 'October' THEN '10'
                    WHEN 'November' THEN '11'
                    WHEN 'December' THEN '12'
                  END || '-1')::date
                )) FROM
              (SELECT response, survey_id
               FROM ag.survey_answers
               WHERE survey_question_id = 112) AS yr
              JOIN
              (SELECT response, survey_id
               FROM ag.survey_answers
               WHERE survey_question_id = 111) AS mo USING (survey_id)
               WHERE yr.response != 'Unspecified'
               AND mo.response != 'Unspecified'"""),
            ('Total male participants',
             """SELECT count(*) FROM ag.survey_answers
                WHERE survey_question_id=107 AND response='Male'"""),
            ('Total female participants',
             """SELECT count(*) FROM ag.survey_answers
                WHERE survey_question_id=107 AND response='Female'""")
            ]
        stats = []
        for label, sql in stats_list:
            res = self._con.execute_fetchone(sql)[0]
            if type(res) == timedelta:
                res = str(res.days/365) + " years"
            stats.append((label, res))
        return stats

    def updateAKB(self, barcode, moldy, overloaded, other, other_text,
                  date_of_last_email):
        """ Update ag_kit_barcodes table.
        """
        sql_args = [moldy, overloaded, other, other_text]
        update_date = ''
        if date_of_last_email:
            update_date = ', date_of_last_email = %s'
            sql_args.append(date_of_last_email)
        sql_args.append(barcode)

        sql = """UPDATE  ag_kit_barcodes
                 SET moldy = %s, overloaded = %s, other = %s,
                     other_text = %s{}
                 WHERE barcode = %s""".format(update_date)
        self._con.execute(sql, sql_args)

    def updateBarcodeStatus(self, status, postmark, scan_date, barcode,
                            biomass_remaining, sequencing_status, obsolete):
        """ Updates a barcode's status
        """
        sql = """UPDATE  barcode
                 SET status = %s,
                     sample_postmark_date = %s,
                     scan_date = %s,
                     biomass_remaining = %s,
                     sequencing_status = %s,
                     obsolete = %s
                 WHERE barcode = %s"""
        self._con.execute(sql, [status, postmark, scan_date, biomass_remaining,
                                sequencing_status, obsolete, barcode])

    def get_barcode_survey(self, barcode):
        """Return survey ID attached to barcode"""
        sql = """SELECT DISTINCT ags.survey_id FROM ag.ag_kit_barcodes
                 JOIN ag.survey_answers USING (survey_id)
                 JOIN ag.group_questions gq USING (survey_question_id)
                 JOIN ag.surveys ags USING (survey_group)
                 WHERE barcode = %s"""
        res = self._con.execute_fetchone(sql, [barcode])
        return res[0] if res else None

    def search_participant_info(self, term):
        sql = """SELECT cast(ag_login_id as varchar(100)) as ag_login_id
                 FROM ag_login al
                 WHERE lower(email) like %s or lower(name) like
                 %s or lower(address) like %s"""
        liketerm = '%%' + term.lower() + '%%'
        results = self._con.execute_fetchall(sql,
                                             [liketerm, liketerm, liketerm])
        return [x[0] for x in results]

    def search_kits(self, term):
        sql = """SELECT cast(ag_login_id as varchar(100)) as ag_login_id
                 FROM ag_kit
                 WHERE lower(supplied_kit_id) like %s or
                 lower(kit_password) like %s or
                 lower(kit_verification_code) = %s or
                 cast(ag_kit_id as varchar(100)) like %s"""
        liketerm = '%%' + term.lower() + '%%'
        results = self._con.execute_fetchall(sql,
                                             [liketerm, liketerm, liketerm,
                                              liketerm])
        return [x[0] for x in results]

    def search_barcodes(self, term):
        sql = """SELECT DISTINCT
                    cast(ag_login_id as varchar(100)) as ag_login_id
                 FROM ag_kit ak
                 INNER JOIN ag_kit_barcodes akb USING (ag_kit_id)
                 FULL OUTER JOIN ag_login_surveys USING
                    (survey_id, ag_login_id)
                 WHERE barcode like %s or lower(participant_name) like
                 %s or lower(notes) like %s"""
        liketerm = '%%' + term.lower() + '%%'
        results = self._con.execute_fetchall(sql,
                                             [liketerm, liketerm, liketerm])
        return [x[0] for x in results]

    def get_kit_info_by_login(self, ag_login_id):
        sql = """SELECT cast(ag_kit_id as varchar(100)) as ag_kit_id,
                        cast(ag_login_id as varchar(100)) as ag_login_id,
                        supplied_kit_id, kit_password, swabs_per_kit,
                        kit_verification_code, kit_verified
                 FROM ag_kit
                 WHERE ag_login_id = %s"""
        info = self._con.execute_fetchdict(sql, [ag_login_id])
        return info if info else []

    def search_handout_kits(self, term):
        sql = """SELECT kit_id, password, barcode, verification_code
                 FROM ag.ag_handout_kits
                 JOIN (SELECT kit_id, barcode, sample_barcode_file
                    FROM ag.ag_handout_barcodes
                    GROUP BY kit_id, barcode) AS hb USING (kit_id)
                 WHERE kit_id LIKE %s or barcode LIKE %s"""
        liketerm = '%%' + term + '%%'
        return self._con.execute_fetchdict(sql, [liketerm, liketerm])

    def get_login_by_email(self, email):
        sql = """SELECT name, address, city, state, zip, country, ag_login_id
                 FROM ag_login WHERE email = %s"""
        row = self._con.execute_fetchone(sql, [email])

        login = {}
        if row:
            login = dict(row)
            login['email'] = email

        return login

    def get_login_info(self, ag_login_id):
        sql = """SELECT  ag_login_id, email, name, address, city, state, zip,
                         country
                 FROM    ag_login
                 WHERE   ag_login_id = %s"""
        return self._con.execute_fetchdict(sql, [ag_login_id])

    def getAGBarcodeDetails(self, barcode):
        sql = """SELECT DISTINCT email,
                    cast(ag_kit_barcode_id as varchar(100)),
                    cast(ag_kit_id as varchar(100)), barcode,  site_sampled,
                    environment_sampled, sample_date, sample_time,
                    participant_name, notes, refunded, withdrawn, moldy, other,
                    other_text, date_of_last_email ,overloaded, name, status,
                    deposited
                 FROM ag_kit_barcodes akb
                 JOIN ag_kit USING(ag_kit_id)
                 JOIN ag_login USING (ag_login_id)
                 FULL OUTER JOIN ag_login_surveys USING
                    (survey_id, ag_login_id)
                 JOIN barcode USING (barcode)
                 WHERE barcode = %s"""

        results = self._con.execute_fetchone(sql, [barcode])
        if not results:
            return {}
        else:
            return dict(results)

    def get_barcode_info_by_kit_id(self, ag_kit_id):
        sql = """SELECT DISTINCT cast(ag_kit_barcode_id as varchar(100)) as
                         ag_kit_barcode_id, cast(ag_kit_id as varchar(100)) as
                         ag_kit_id, barcode, sample_date, sample_time,
                         site_sampled, environment_sampled, participant_name,
                         notes, results_ready, withdrawn, refunded
                 FROM    ag_kit_barcodes
                 FULL OUTER JOIN ag_login_surveys USING (survey_id)
                 WHERE   ag_kit_id = %s"""

        results = [dict(row) for row in
                   self._con.execute_fetchall(sql, [ag_kit_id])]
        return results

    def get_barcodes_with_results(self):
        """Returns list of all barcodes with results ready (PDFs available)

        Returns
        -------
        list of str
            All barcodes with result PDFs available

        Raises
        ------
        IOError
            PDF directory does not exist
        """
        path = join(self.config.base_data_dir, 'pdfs')
        if not isdir(path):
            raise IOError('Unknown folder %s' % abspath(path))
        # Get the list of barcodes from the PDF names
        files = next(walk(path))[2]
        return [splitext(f)[0] for f in files if f.endswith('.pdf')]

    def mark_results_ready(self, barcodes, debug=False):
        """Marks the list of barcodes as ready in the databse and sends email

        Parameters
        ----------
        barcodes: iterable of str
            Barcodes to mark as having results ready

        Notes
        -----
        This function automatically sends emails out to only newly set results
        ready barcodes. This means you can pass in a list of all barcodes from
        all rounds that have results ready, and the function will filter for
        new results automatically.
        """
        debug = {}
        ready_sql = """UPDATE ag.ag_kit_barcodes
                       SET results_ready = 'Y'
                       WHERE barcode IN %s
                       AND (results_ready != 'Y' OR results_ready IS NULL)
                       RETURNING barcode"""
        new_bcs = tuple(x[0] for x in
                        self._con.execute_fetchall(
                            ready_sql, [tuple(barcodes)]))
        debug['new_bcs'] = new_bcs
        if len(new_bcs) == 0:
            # No new barcodes, so no emails to send
            return

        bc_sql = """UPDATE ag.ag_kit_barcodes
                 SET date_of_last_email = '{0}'
                 WHERE barcode IN %s""".format(datetime.now())
        subject = "Your American/British Gut results are ready"
        message = (
            "Good afternoon American & British Gut participants!\n\n"
            "We are pleased to let you know that your results are now "
            "available. You may access them by signing onto "
            "microbio.me/americangut or microbio.me/britishgut. If you have "
            "forgotten your login credentials, you may retrieve them using "
            "the \"Forgot kit ID/password\" functions.\n\n"
            "We thank you for being a part of the project. While we emphasize "
            "getting results back to you, the participant, we and the broader "
            "American/British Gut scientific collaborative network are "
            "extremely excited about the population-scale microbiome "
            "observations that are for the first time becoming possible thanks"
            " to you and the other participants!\n\n"
            "Regards,\n"
            "The American Gut Team\n")
        barcode_info = self.get_ag_barcode_details(new_bcs)
        # Make sure email only sent once if multiple barcodes with same email
        seen_emails = set(i['email'] for bc, i in viewitems(barcode_info))
        mail = send_email(message, subject, bcc=list(seen_emails), debug=debug)
        debug['mail'] = mail
        self._con.execute(bc_sql, [new_bcs])
        if debug:
            return debug

    def getHumanParticipants(self, ag_login_id):
        # get people from new survey setup
        sql = """SELECT DISTINCT participant_name from ag.ag_login_surveys
                 LEFT JOIN ag.survey_answers USING (survey_id)
                 JOIN ag.group_questions gq USING (survey_question_id)
                 JOIN ag.surveys ags USING (survey_group)
                 WHERE ag_login_id = %s AND ags.survey_id = %s"""
        results = self._con.execute_fetchall(sql, [ag_login_id, 1])
        return [row[0] for row in results]

    def getAGKitsByLogin(self):
        sql = """SELECT  lower(al.email) as email, supplied_kit_id,
                 cast(ag_kit_id as varchar(100)) as ag_kit_id
                 FROM ag_login al
                 INNER JOIN ag_kit USING (ag_login_id)
                 ORDER BY lower(email), supplied_kit_id"""
        rows = self._con.execute_fetchall(sql)
        return [dict(row) for row in rows]

    def getAnimalParticipants(self, ag_login_id):
        sql = """SELECT DISTINCT participant_name from ag.ag_login_surveys
                 JOIN ag.survey_answers USING (survey_id)
                 JOIN ag.group_questions gq USING (survey_question_id)
                 JOIN ag.surveys ags USING (survey_group)
                 WHERE ag_login_id = %s AND ags.survey_id = %s"""
        return [row[0] for row in self._con.execute_fetchall(
            sql, [ag_login_id, 2])]

    def ag_new_survey_exists(self, barcode):
        """
        Returns metadata for an american gut barcode in the new database
        tables
        """
        sql = "SELECT EXISTS(SELECT * from ag_kit_barcodes WHERE barcode = %s)"
        return self._con.execute_fetchone(sql, [barcode])[0]

    def get_plate_for_barcode(self, barcode):
        """
        Gets the sequencing plates a barcode is on
        """
        sql = """SELECT p.plate, p.sequence_date
                 FROM plate p
                 INNER JOIN plate_barcode pb
                 ON pb.plate_id = p.plate_id \
                 WHERE pb.barcode = %s"""

        return [dict(row) for row in
                self._con.execute_fetchall(sql, [barcode])]

    def getBarcodeProjType(self, barcode):
        """ Get the project type of the barcode.
            Return a tuple of projects and parent project.
        """
        sql = """SELECT project from barcodes.project
                 JOIN barcodes.project_barcode USING (project_id)
                 where barcode = %s"""
        results = [x[0] for x in self._con.execute_fetchall(sql, [barcode])]
        if 'American Gut Project' in results:
            parent_project = 'American Gut'
            results.remove('American Gut Project')
            projects = ', '.join(results)
        else:
            projects = ', '.join(results)
            parent_project = projects
        return (projects, parent_project)

    def setBarcodeProjects(self, barcode,
                           add_projects=None,
                           rem_projects=None):
        """Sets the projects barcode is associated with

        Parameters
        ----------
        barcode : str
            Barcode to update
        add_projects : list of str, optional
            List of projects from projects table to add project to
        rem_projects : list of str, optional
            List of projects from projects table to remove barcode from
        """
        if add_projects:
            sql = """INSERT INTO barcodes.project_barcode
                      SELECT project_id, %s FROM (
                        SELECT project_id FROM barcodes.project
                        WHERE project in %s)
                     AS P"""

            self._con.execute(sql, [barcode, tuple(add_projects)])
        if rem_projects:
            sql = """DELETE FROM barcodes.project_barcode
                     WHERE barcode = %s AND project_id IN (
                       SELECT project_id
                       FROM barcodes.project WHERE project IN %s)"""
            self._con.execute(sql, [barcode, tuple(rem_projects)])

    def getProjectNames(self):
        """Returns a list of project names
        """
        sql = """SELECT project FROM project"""
        return [x[0] for x in self._con.execute_fetchall(sql)]

    def set_deposited_ebi(self):
        """Updates barcode deposited status by checking EBI"""
        accession = 'ERP012803'
        samples = fetch_url(
            'http://www.ebi.ac.uk/ena/data/warehouse/filereport?accession='
            '%s&result=read_run&fields=sample_alias' % accession)
        # Clean EBI formatted sample names to just the barcodes
        # stripped of any appended letters for barcodes run multiple times
        barcodes = tuple(s.strip().split('.')[1][:9]
                         for s in samples if len(s.split('.')) == 2)

        sql = """UPDATE ag.ag_kit_barcodes
                 SET deposited = TRUE
                 WHERE barcode IN %s"""
        self._con.execute(sql, [barcodes])

    def _study_exists(self, study_id):
        """Confirms that a study ID exists

        Parameters
        ----------
        study_id : int
            ID of the study

        Raises
        ------
        ValueError
            If the study ID does not exist
        """
        with TRN:
            sql = """SELECT EXISTS (SELECT 1 FROM pm.study
                                    WHERE study_id = %s)"""
            TRN.add(sql, [study_id])
            if not TRN.execute_fetchlast():
                raise ValueError('Study ID %s does not exist.' % study_id)

    def _study_is_unique(self, qiita_study_id=None, title=None, skip_id=None):
        """Confirms that a study is unique

        Confirms that the Qiita study ID and/or the title to be assigned to a
        study is not duplicate.

        Parameters
        ----------
        qiita_study_id : int, optional
            Qiita study ID of the study
        title : str, optional
            Title of the study
            Either qiita_study_id or title must be specified as the identifier
            of a study
        skip_id : int, optional
            Skip this study ID in searching
            In function create_study, this is not used
            In function edit_study, this is the current study to be edited

        Raises
        ------
        ValueError
            If neither value is given, or either value already exists
        """
        cols = ['qiita_study_id', 'title']
        vals = [qiita_study_id, title]
        tags = [x.capitalize().replace('_', ' ').replace(' id', ' ID')
                for x in cols]
        if all(val is None for val in vals):
            raise ValueError('Either %s or %s must be specified.'
                             % (tags[0], tags[1]))
        with TRN:
            sql = """SELECT study_id
                     FROM pm.study
                     WHERE {} = %s
                     AND study_id IS DISTINCT FROM %s"""
            errs = []
            err_msg = "%s %s conflicts with exisiting study %s."
            for col, val, tag in zip(cols, vals, tags):
                if val:
                    TRN.add(sql.format(col), [val, skip_id])
                    res = TRN.execute_fetchflatten()
                    if res:
                        errs.append(err_msg % (tag, repr(val), res[0]))
            if errs:
                raise ValueError('\n'.join(errs))

    def create_study(self, qiita_study_id=None, title=None, alias=None,
                     notes=None):
        """Creates a study

        Parameters
        ----------
        qiita_study_id : int, optional
            Assigns a Qiita study ID to the study
        title : str, optional
            Assigns a title to the study
            Either qiita_study_id or title must be specified
        alias : str, optional
            Assigns an alias to the study
        notes : str, optional
            Makes notes of the study

        Returns
        -------
        int
            ID of the study created
        """
        with TRN:
            self._study_is_unique(qiita_study_id, title)
            sql = """INSERT INTO pm.study (qiita_study_id, title, alias, notes)
                     VALUES (%s, %s, %s, %s)
                     RETURNING study_id"""
            sql_args = [qiita_study_id, title, alias, notes]
            TRN.add(sql, sql_args)
            return TRN.execute_fetchlast()

    def edit_study(self, study_id, qiita_study_id=None, title=None, alias=None,
                   notes=None):
        """Edits properties of an existing study

        Parameters
        ----------
        study_id : int
            ID of the study to edit
        qiita_study_id : int, optional
            Assigns a Qiita study ID to the study
        title : str, optional
            Assigns a title to the study
            Either qiita_study_id or title must be specified
        alias : str, optional
            Assigns an alias to the study
        notes : str, optional
            Makes notes of the study
        """
        with TRN:
            self._study_exists(study_id)
            self._study_is_unique(qiita_study_id, title, study_id)
            sql = """UPDATE pm.study
                     SET qiita_study_id = %s, title = %s, alias = %s,
                         notes = %s
                     WHERE study_id = %s
                     RETURNING study_id"""
            sql_args = [qiita_study_id, title, alias, notes, study_id]
            TRN.add(sql, sql_args)
            TRN.execute()

    def read_study(self, study_id):
        """Reads properties of an existing study

        Parameters
        ----------
        study_id : int
            ID of the study to read

        Returns
        -------
        dict
            {qiita_study_id : int, title : str, alias : str, notes : str}
            Properties of the study: Qiita study ID, title, alias and notes

        Raises
        ------
        ValueError
            If the study ID does not exist
        """
        with TRN:
            sql = """SELECT qiita_study_id, title, alias, notes
                     FROM pm.study
                     WHERE study_id = %s"""
            TRN.add(sql, [study_id])
            res = TRN.execute_fetchindex()
            if not res:
                raise ValueError('Study ID %s does not exist.' % study_id)
            return dict(res[0])

    def delete_study(self, study_id):
        """Deletes an existing study

        Samples exclusively associated with the study will be deleted. Samples
        associated with it but also with other studies will be disassociated.

        Parameters
        ----------
        study_id : int
            ID of the study to delete

        Raises
        ------
        ValueError
            If the study ID does not exist
            If one or more associated samples are also associated with one
            or more sample plates, in which case, the sample plates have to be
            deleted prior to the deletion of the study
        """
        with TRN:
            self._study_exists(study_id)
            samples = self.get_samples_by_study(study_id)
            if samples:
                samples_to_delete = [x for x in samples if not samples[x]]
                if samples_to_delete:
                    self.delete_samples(samples_to_delete)
                if len(samples) > len(samples_to_delete):
                    sql = """DELETE FROM pm.study_sample
                             WHERE study_id = %s"""
                    TRN.add(sql, [study_id])
            sql = """DELETE FROM pm.study
                     WHERE study_id = %s"""
            TRN.add(sql, [study_id])
            TRN.execute()

    def _sample_exists(self, sample_id):
        """Checks whether a sample ID exists

        Parameters
        ----------
        sample_id : str
            ID of the sample to check

        Returns
        ------
        bool
            Whether the sample exists
        """
        with TRN:
            sql = """SELECT EXISTS (SELECT 1 FROM pm.sample
                                    WHERE sample_id = %s)"""
            TRN.add(sql, [sample_id])
            return TRN.execute_fetchlast()

    def _samples_exist(self, sample_ids, exist=True):
        """Confirms that given sample ID(s) (do not) exist

        Parameters
        ----------
        sample_ids : list of str
            IDs of the sample to check
        exist : bool, optional, default: True
            True: checks if exist
            False: checks if not exist

        Raises
        ------
        ValueError
            If one or more sample IDs do not exist (when exist == True)
            If one or more sample IDs already exist (when exist == False)
        """
        with TRN:
            sql = """SELECT sample_id
                     FROM pm.sample
                     WHERE sample_id IN %s"""
            TRN.add(sql, [tuple(sample_ids)])
            res = TRN.execute_fetchflatten()
            if exist:
                res = set(sample_ids) - set(res)
                if res:
                    raise ValueError('Sample ID(s) %s do not exist.' %
                                     ', '.join(sorted(res)))
            else:
                if res:
                    raise ValueError('Sample ID(s) %s already exist.' %
                                     ', '.join(sorted(res)))

    def _validate_samples(self, samples):
        """Validate sample properties

        Confirms that the barcodes and study IDs to be assigned to samples are
        valid.

        Parameters
        ----------
        samples : list of dict
            {barcode : str, optional,
                Barcode to be assigned to the sample
             study_ids : list of int, optional
                One or more study IDs to be associateed with the sample}

        Raises
        ------
        ValueError
            If one or more study IDs do not exist
            If one or more sample barcodes do not exist
        """
        with TRN:
            study_ids = set().union(*[x['study_ids'] for x in samples
                                      if 'study_ids' in x])
            barcodes = set([x['barcode'] for x in samples if 'barcode' in x])
            cols = ['barcode', 'study_id']
            tabs = ['barcodes.barcode', 'pm.study']
            vals = [barcodes, study_ids]
            tags = [x.capitalize().replace('_', ' ').replace(' id', ' ID') +
                    '(s)' for x in cols]
            sql = """SELECT {} FROM {} WHERE {} IN %s"""
            err_msg = '%s %s do not exist.'
            for col, tab, val, tag in zip(cols, tabs, vals, tags):
                if val:
                    TRN.add(sql.format(col, tab, col), [tuple(val)])
                    res = val - set(TRN.execute_fetchflatten())
                    if res:
                        val_str = ', '.join(str(x) for x in sorted(res))
                        raise ValueError(err_msg % (tag, val_str))

    def create_samples(self, samples):
        """Creates samples and associates them with studies

        Parameters
        ----------
        samples : list of dict
            A list of samples specified by properties and study IDs
            {id : str,
                Assigns an ID to the sample
             is_blank : bool, optional, default: False,
                Specifies whether the sample is blank
             barcode : str, optional,
                Assigns a barcode to the sample
             notes : str, optional
                Makes notes of the sample
             study_ids : list of int
                Associates the sample with one or more studies}

        Raises
        ------
        ValueError
            If one or more sample IDs already exist
            If one or more study IDs do not exist
        """
        with TRN:
            sample_ids = [x['id'] for x in samples]
            self._samples_exist(sample_ids, exist=False)
            self._validate_samples(samples)
            sql1 = """INSERT INTO pm.sample (sample_id, is_blank, barcode,
                                             notes)
                      VALUES (%s, %s, %s, %s)"""
            sql2 = """INSERT INTO pm.study_sample (study_id, sample_id)
                      SELECT study_ids, %s
                      FROM unnest(%s) study_ids"""
            for sample in samples:
                TRN.add(sql1, [sample['id'], sample.get('is_blank', False),
                               sample.get('barcode'), sample.get('notes')])
                TRN.add(sql2, [sample['id'], sample['study_ids']])
            TRN.execute()

    def edit_samples(self, samples):
        """Edits properties of samples and/or their associations with studies

        Parameters
        ----------
        samples : list of dict
            A list of samples specified by properties and study IDs
            {id : str,
                ID of the sample to edit
             is_blank : bool, optional, default: False,
                Whether the sample is blank
             barcode : str, optional,
                Assigns a barcode to the sample
             notes : str, optional
                Makes notes of the sample
             study_ids : list of int, optional
                Associates the sample with one or more studies}

        Raises
        ------
        ValueError
            If one or more sample IDs do not exist
            If one or more study IDs do not exist
        """
        with TRN:
            sample_ids = [x['id'] for x in samples]
            self._samples_exist(sample_ids)
            self._validate_samples(samples)
            sql1 = """UPDATE pm.sample
                      SET is_blank = %s, barcode = %s, notes = %s
                      WHERE sample_id = %s"""
            sql2 = """DELETE FROM pm.study_sample
                      WHERE sample_id = %s"""
            sql3 = """INSERT INTO pm.study_sample (study_id, sample_id)
                      SELECT study_ids, %s
                      FROM unnest(%s) study_ids"""
            for sample in samples:
                if any(x in sample for x in ['is_blank', 'barcode', 'notes']):
                    TRN.add(sql1, [sample.get('is_blank', False),
                                   sample.get('barcode'), sample.get('notes'),
                                   sample['id']])
                if 'study_ids' in sample:
                    TRN.add(sql2, [sample['id']])
                    TRN.add(sql3, [sample['id'], sample['study_ids']])
            TRN.execute()

    def read_samples(self, ids):
        """Read properties and associated study IDs of samples, if they exist

        Parameters
        ----------
        ids : list of str
            IDs of the samples to read

        Returns
        -------
        dict of dict
            {sample_id : {is_blank : bool, barcode : str, notes : str,
             study_ids : list of int}}
            Properties of each sample: Whether this sample is blank, barcode,
            and notes, and sorted study IDs associated with it

        Notes
        -----
        If one or more sample IDs do not exist, the function will not raise an
        error. Instead, these samples will be absent in the returning dict.
        Therefore, this function combines existence checking and properties
        retrieval in one command.
        """
        with TRN:
            sql = """SELECT sample_id, is_blank, barcode, notes,
                            array_agg(study_id ORDER BY study_id)
                            AS study_ids
                     FROM pm.sample
                     JOIN pm.study_sample
                     USING (sample_id)
                     WHERE sample_id IN %s
                     GROUP BY sample_id"""
            TRN.add(sql, [tuple(ids)])
            samples = {}
            for row in TRN.execute_fetchindex():
                samples[row[0]] = dict(row)
                samples[row[0]].pop('sample_id')
            return samples

    def delete_samples(self, ids):
        """Deletes existing samples along with their associations with studies

        Parameters
        ----------
        ids : list of str
            IDs of the samples to delete

        Raises
        ------
        ValueError
            If one or more sample IDs do not exist
            If one or more samples are associated with one or more sample
            plates, in which case, the sample plates have to be deleted
            prior to the deletion of the samples
        """
        with TRN:
            self._samples_exist(ids)
            sql = """SELECT sample_plate_id, sample_id
                     FROM pm.sample_plate_layout
                     WHERE sample_id IN %s"""
            TRN.add(sql, [tuple(ids)])
            res = TRN.execute_fetchindex()
            if res:
                raise ValueError('Sample ID(s) %s cannot be deleted because '
                                 'they are associated with sample plate(s) %s.'
                                 % (', '.join(set([x[1] for x in res])),
                                    ', '.join(set([str(x[0]) for x in res]))))
            sql = """DELETE FROM pm.study_sample
                     WHERE sample_id IN %s"""
            TRN.add(sql, [tuple(ids)])
            sql = """DELETE FROM pm.sample
                     WHERE sample_id IN %s"""
            TRN.add(sql, [tuple(ids)])
            TRN.execute()

    def get_samples_by_study(self, study_id):
        """Gets samples associated with a study

        Retrieves IDs of all samples associated with a study, and whether
        they are also associated with other studies.

        Parameters
        ----------
        study_id : int
            ID of the study

        Returns
        -------
        dict
            {Sample ID : bool}
                Whether this sample is also associated with other studies

        Raises
        ------
        ValueError
            If the study ID does not exist
        """
        with TRN:
            self._study_exists(study_id)
            sql = """SELECT sample_id
                     FROM pm.study_sample
                     WHERE study_id = %s"""
            TRN.add(sql, [study_id])
            res1 = [x[0] for x in TRN.execute_fetchindex()]
            if res1:
                sql = """SELECT sample_id
                         FROM pm.study_sample
                         WHERE sample_id IN %s
                         AND study_id <> %s"""
                TRN.add(sql, [tuple(res1), study_id])
                res2 = set([x[0] for x in TRN.execute_fetchindex()])
                return {x: x in res2 for x in res1}
            else:
                return {}

    def _sample_plate_exists(self, id):
        """Confirms that a sample plate ID exists

        Parameters
        ----------
        id : int
            ID of the sample plate to check

        Raises
        ------
        ValueError
            If the sample plate ID does not exist
        """
        with TRN:
            sql = """SELECT EXISTS (SELECT 1 FROM pm.sample_plate
                                    WHERE sample_plate_id = %s)"""
            TRN.add(sql, [id])
            if not TRN.execute_fetchlast():
                raise ValueError('Sample plate ID %s does not exist.' % id)

    def _sample_plate_is_unique(self, name, skip_id=None):
        """Confirms that a sample plate name is not duplicate

        Parameters
        ----------
        name : str
            Name to be assigned to a new or existing sample plate
        skip_id : int, optional
            Skips this sample plate ID in searching
            In function create_sample_plate, this is not used
            In function edit_sample_plate, this is the current sample plate to
            be edited

        Raises
        ------
        ValueError
            If the sample plate name already exists
        """
        with TRN:
            sql = """SELECT sample_plate_id
                     FROM pm.sample_plate
                     WHERE name = %s
                     AND sample_plate_id IS DISTINCT FROM %s"""
            TRN.add(sql, [name, skip_id])
            res = TRN.execute_fetchflatten()
            if res:
                raise ValueError('Name %s conflicts with exisiting sample '
                                 'plate %s.' % (repr(name), res[0]))

    def _email_exists(self, email):
        """Confirms that an email exists

        Parameters
        ----------
        email : str
            Email as an identifier of the user

        Raises
        ------
        ValueError
            If the email does not exist
        """
        with TRN:
            sql = """SELECT EXISTS (SELECT 1 FROM ag.labadmin_users
                                    WHERE email = %s)"""
            TRN.add(sql, [email])
            if not TRN.execute_fetchlast():
                raise ValueError('Email %s does not exist.' % email)

    def _get_first_plate_type(self):
        """Retrieves ID of the first plate type

        Returns
        -------
        int
            ID of the first plate type
        """
        with TRN:
            sql = """SELECT plate_type_id
                     FROM pm.plate_type
                     ORDER BY plate_type_id
                     LIMIT 1"""
            TRN.add(sql)
            return TRN.execute_fetchlast()

    def _plate_type_exists(self, id):
        """Confirms that a plate type exists

        Parameters
        ----------
        id : int
            ID of the plate type

        Raises
        ------
        ValueError
            If the plate type does not exist
        """
        with TRN:
            sql = """SELECT EXISTS (SELECT 1 FROM pm.plate_type
                                    WHERE plate_type_id = %s)"""
            TRN.add(sql, [id])
            if not TRN.execute_fetchlast():
                raise ValueError('Plate type ID %s does not exist.' % id)

    def create_sample_plate(self, name, plate_type_id, email=None,
                            created_on=None, notes=None):
        """Creates a new sample plate

        Parameters
        ----------
        name : str
            Assigns a name to the sample plate
        plate_type_id : int
            Defines the type of the sample plate
        email : str, optional
            Specifies who (by Email) created the sample plate
        created_on: datetime, optional
            Specifies when (by date) was the sample plate created
        notes : str, optional
            Makes notes of the sample plate

        Returns
        -------
        int
            ID of the created sample plate
        """
        with TRN:
            self._sample_plate_is_unique(name)
            self._plate_type_exists(plate_type_id)
            if email:
                self._email_exists(email)
            sql = """INSERT INTO pm.sample_plate (name, plate_type_id, email,
                                                  created_on, notes)
                     VALUES (%s, %s, %s, %s, %s)
                     RETURNING sample_plate_id"""
            sql_args = [name, plate_type_id, email, created_on, notes]
            TRN.add(sql, sql_args)
            return TRN.execute_fetchlast()

    def edit_sample_plate(self, id, name, plate_type_id, email=None,
                          created_on=None, notes=None):
        """Edits properties of a sample plate

        Parameters
        ----------
        id : int
            ID of the sample plate to edit
        name : str
            Assigns a name to the sample plate
        plate_type_id : int
            Defines the type of the sample plate
        email : str, optional
            Specifies who (by Email) created the sample plate
        created_on: datetime, optional
            Specifies when (by date) was the sample plate created
        notes : str, optional
            Makes notes of the sample plate
        """
        with TRN:
            self._sample_plate_exists(id)
            self._sample_plate_is_unique(name, id)
            self._plate_type_exists(plate_type_id)
            if email:
                self._email_exists(email)
            sql = """UPDATE pm.sample_plate
                     SET name = %s, plate_type_id = %s, email = %s,
                         created_on = %s, notes = %s
                     WHERE sample_plate_id = %s"""
            sql_args = [name, plate_type_id, email, created_on, notes, id]
            TRN.add(sql, sql_args)
            TRN.execute()

    def read_sample_plate(self, id):
        """Reads properties of a sample plate

        Parameters
        ----------
        id : int
            ID of the sample plate to read

        Returns
        -------
        dict
            {name : str, plate_type_id : int, email : str,
             created_on: datetime, notes : str}
            Properties of the sample plate: name, plate type ID, who created
            it, when it was created, and notes
        """
        with TRN:
            self._sample_plate_exists(id)
            sql = """SELECT name, plate_type_id, email, created_on, notes
                     FROM pm.sample_plate
                     WHERE sample_plate_id = %s"""
            TRN.add(sql, [id])
            return dict(TRN.execute_fetchindex()[0])

    def _sample_plate_layout_exists(self, id):
        """Checks whether the layout of a sample plate exists

        The layout of a sample plate exists when at least one sample-to-well
        record exists.

        Parameters
        ----------
        id : int
            ID of the sample plate whose layout is to be checked

        Returns
        ------
        bool
            Whether the layout exists
        """
        with TRN:
            sql = """SELECT EXISTS (SELECT 1 FROM pm.sample_plate_layout
                                    WHERE sample_plate_id = %s)"""
            TRN.add(sql, [id])
            return TRN.execute_fetchlast()

    def _clear_sample_plate_layout(self, id):
        """Deletes the entire layout of a sample plate

        Parameters
        ----------
        id : int
            ID of the sample plate whose layout is to be deleted
        """
        with TRN:
            sql = """DELETE FROM pm.sample_plate_layout
                     WHERE sample_plate_id = %s"""
            TRN.add(sql, [id])
            TRN.execute()

    def write_sample_plate_layout(self, id, layout):
        """Writes the layout of a sample plate

        Parameters
        ----------
        id : int
            ID of the sample plate whose layout is to be written
        layout : list of dict
            {sample_id : str, col : int, row : int, name : str, notes : str}
            A list of sample-to-well records, each of which includes:
            Sample ID, column number, row number, name, and notes
        """
        with TRN:
            self._sample_plate_exists(id)
            if self._sample_plate_layout_exists(id):
                self._clear_sample_plate_layout(id)
            sql = """INSERT INTO pm.sample_plate_layout (sample_plate_id,
                        sample_id, col, row, name, notes)
                     VALUES (%s, %s, %s, %s, %s, %s)"""
            for x in layout:
                sample_id = x['sample_id']
                if not self._sample_exists(sample_id):
                    raise ValueError('Sample ID %s does not exist.'
                                     % sample_id)
                TRN.add(sql, [id, sample_id, x['col'], x['row'],
                              x.get('name'), x.get('notes')])
                TRN.execute()

    def read_sample_plate_layout(self, id):
        """Reads the layout of a sample plate

        Parameters
        ----------
        id : int
            ID of the sample plate whose layout is to be read

        Returns
        -------
        list of dict
            {sample_id : str, col : int, row : int, name : str, notes : str}
            A list of sample-to-well records, each of which includes:
            Sample ID, column number, row number, name, and notes
            The list is sorted by column then by row in ascending order
        """
        with TRN:
            self._sample_plate_exists(id)
            if not self._sample_plate_layout_exists(id):
                return []
            sql = """SELECT sample_id, col, row, name, notes
                     FROM pm.sample_plate_layout
                     WHERE sample_plate_id = %s
                     ORDER BY col, row"""
            TRN.add(sql, [id])
            return [dict(x) for x in TRN.execute_fetchindex()]

    def delete_sample_plate(self, id):
        """Deletes a sample plate and its layout

        Parameters
        ----------
        id : int
            ID of the sample plate to delete
        """
        with TRN:
            self._sample_plate_exists(id)
            if self._sample_plate_layout_exists(id):
                self._clear_sample_plate_layout(id)
            sql = """DELETE FROM pm.sample_plate
                     WHERE sample_plate_id = %s"""
            TRN.add(sql, [id])
            TRN.execute()

    def get_property_options(self, property):
        """Retrieves a list of available options for a property

        Parameters
        ----------
        property : str
            Property name, i.e., name of a table under schema "pm"

        Returns
        -------
        list of dict
            {id : int, name : str, notes : str}
            ID, name and notes for each option
        """
        with TRN:
            sql = """SELECT {} AS id, name, notes
                     FROM {}
                     ORDER BY {}"""
            TRN.add(sql.format(property + '_id',
                               'pm.' + property,
                               property + '_id'))
            return [dict(x) for x in TRN.execute_fetchindex()]

    def get_plate_types(self):
        """Gets all available plate types

        Returns
        -------
        list of dict
            {id : int, name : str, cols : int, rows : int, notes : str}
            ID, name, notes, and numbers of columns and rows of each plate type
        """
        with TRN:
            sql = """SELECT plate_type_id AS id, name, notes, cols, rows
                     FROM pm.plate_type
                     ORDER BY plate_type_id"""
            TRN.add(sql)
            return [dict(x) for x in TRN.execute_fetchindex()]

    def get_emails(self):
        """Gets all available emails

        Returns
        -------
        list of str
            Sorted list of emails
        """
        with TRN:
            sql = """SELECT email
                     FROM ag.labadmin_users
                     ORDER BY email"""
            TRN.add(sql)
            return TRN.execute_fetchflatten()

    def get_sample_plate_ids(self):
        """Gets a list of sample plate IDs

        Returns
        -------
        list of int
            Sorted list of sample plate IDs
        """
        with TRN:
            sql = """SELECT sample_plate_id
                     FROM pm.sample_plate
                     ORDER BY sample_plate_id"""
            TRN.add(sql)
            return TRN.execute_fetchflatten()

    def get_sample_plate_list(self):
        """Gets basic information of all sample plates

        Returns
        -------
        list of dict
            {id : int, name : str, type : list of [str, int], count : int,
            person : str, date : datetime,
            study : list of [int, int, int, str])}
            Plate id, plate name, plate type (name and total number of wells),
            (number and proportion) of samples filled, email, date, study
            (number of studies, ID, Qiita ID and title of the most frequent
            study)
        """
        with TRN:
            sql = """SELECT sample_plate_id, sample_plate.name, plate_type.name,
                            cols, rows, email, created_on, x.sample_count,
                            x.study_freq, x.study_id, x.qiita_study_id, x.title
                     FROM pm.sample_plate
                     JOIN pm.plate_type USING (plate_type_id)
                     JOIN (SELECT study_id, qiita_study_id, title,
                                  sample_plate_id,
                                  COUNT(DISTINCT study_id) AS study_freq,
                                  COUNT(sample_id) AS sample_count
                           FROM pm.study
                           JOIN pm.study_sample USING (study_id)
                           JOIN pm.sample_plate_layout USING (sample_id)
                           JOIN pm.sample_plate USING (sample_plate_id)
                           GROUP BY study_id, sample_plate_id
                           ORDER BY COUNT(study_id) DESC) AS x
                     USING (sample_plate_id)
                     ORDER BY sample_plate_id"""
            TRN.add(sql)
            res = TRN.execute_fetchindex()
            plates = []
            for row in res:
                wells = row[3]*row[4]
                ratio = 0.0
                if wells:
                    ratio = round(float(row[7])/wells, 3)
                date = None
                if row[6] is not None:
                    date = row[6].strftime('%m/%d/%Y')
                plates.append({'id': int(row[0]),
                               'name': row[1],
                               'type': [row[2], wells],
                               'person': row[5],
                               'date': date,
                               'fill': [row[7], ratio],
                               'study': [row[8], row[9], row[10], row[11]]})
            return plates

    def _clear_table(self, table, schema):
        """Test helper to wipe out a database table"""
        self._con.execute('DELETE FROM %s.%s' % (schema, table))

    def _revert_ready(self, barcodes):
        """Test helper to revert barcodes set as ready"""
        sql = """UPDATE ag.ag_kit_barcodes
                 SET results_ready = NULL
                 WHERE barcode IN %s"""
        self._con.execute(sql, [tuple(barcodes)])

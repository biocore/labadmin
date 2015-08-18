from contextlib import contextmanager
from collections import defaultdict, namedtuple
from re import sub
from hashlib import md5
from datetime import datetime
import urllib
import json
import httplib

from bcrypt import hashpw, gensalt

from psycopg2 import connect, Error as PostgresError
from psycopg2.extras import DictCursor

from util import make_valid_kit_ids, make_verification_code, make_passwd
from constants import country_lookup, md_lookup, month_lookup


class IncorrectEmailError(Exception):
    pass


class IncorrectPasswordError(Exception):
    pass


class GoogleAPILimitExceeded(Exception):
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
            The results of the query as [{colname: val, colname: val, ...}, ...]

        Notes
        -----
        from psycopg2 documentation, only variable values should be bound
            via sql_args, it shouldn't be used to set table or field names. For
            those elements, ordinary string formatting should be used before
            running execute.
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

    def _get_col_names_from_cursor(self, cur):
        if cur.description:
            return [x[0] for x in cur.description]
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
        return dict(self._con.execute_fetchone(sql, [barcode]))

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
        sql = """SELECT barcode, *
                 FROM ag_kit_barcodes
                 JOIN ag_kit USING (ag_kit_id)
                 JOIN ag_login USING (ag_login_id)
                 WHERE barcode in %s"""
        results = {row[0]: dict(row)
                   for row in self._con.execute_fetchall(sql, [tuple(barcodes)])}
        return results

    def get_surveys(self, barcodes):
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
               WHERE survey_response_type='SINGLE' AND barcode in %s"""

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
               WHERE survey_response_type='MULTIPLE' AND barcode in %s
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
               WHERE survey_response_type in ('STRING', 'TEXT')
               AND barcode in %s"""

        # Formats a question and response for a MULTIPLE question into a header
        def _translate_multiple_response_to_header(question, response):
            response = sub('\W', '_', response)
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

        # this function reduces code duplication by generalizing as much
        # as possible how questions and responses are fetched from the db
        bc = tuple(barcodes)

        def _format_responses_as_dict(sql, json=False, multiple=False):
            ret_dict = defaultdict(lambda: defaultdict(dict))
            for survey, barcode, q, a in self._con.execute_fetchall(sql, [bc]):
                if json:
                    # Taking this slice here since all json are single-element
                    # lists
                    a = a[2:-2]

                    # replace all non-alphanumerics with underscore
                    a = sub('[^0-9a-zA-Z.,;/_() -]', '_', a)
                if multiple:
                    for response, header in multiples_headers[q].items():
                        ret_dict[survey][barcode][header] = \
                            'Yes' if response in a else 'No'
                else:
                    ret_dict[survey][barcode][q] = a
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

    def format_survey_data(self, md):
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

        Returns
        -------
        dict of dict of dict
        """
        # get barcode information
        all_barcodes = set().union(*[set(md[s]) for s in md])
        barcode_info = self.get_ag_barcode_details(all_barcodes)

        # Human survey (id 1)
        # tuples are latitude, longitude, elevation
        zipcode_sql = """SELECT zipcode, latitude, longitude, elevation
                         FROM zipcodes"""
        zip_lookup = {row[0]: tuple(row[1:])
                      for row in self._con.execute_fetchall(zipcode_sql)}

        survey_sql = "SELECT barcode, survey_id FROM ag.ag_kit_barcodes"
        survey_lookup = dict(self._con.execute_fetchall(survey_sql))

        for barcode, responses in md[1].items():
            # Get rid of ABOUT_YOURSELF_TEXT
            del md[1][barcode]['ABOUT_YOURSELF_TEXT']

            # convert numeric fields
            for field in ('HEIGHT_CM', 'WEIGHT_KG'):
                md[1][barcode][field] = sub('[^0-9.]',
                                            '', md[1][barcode][field])
                if md[1][barcode][field]:
                    md[1][barcode][field] = float(md[1][barcode][field])

            # Correct height units
            if responses['HEIGHT_UNITS'] == 'inches' and \
                    responses['HEIGHT_CM']:
                md[1][barcode]['HEIGHT_CM'] = \
                    2.54*md[1][barcode]['HEIGHT_CM']
            md[1][barcode]['HEIGHT_UNITS'] = 'centimeters'

            # Correct weight units
            if responses['WEIGHT_UNITS'] == 'pounds' and \
                    responses['WEIGHT_KG']:
                md[1][barcode]['WEIGHT_KG'] = \
                    md[1][barcode]['WEIGHT_KG']/2.20462
            md[1][barcode]['WEIGHT_UNITS'] = 'kilograms'

            # Get age in months (int) and age in years (float)
            if responses['BIRTH_MONTH'] != 'Unspecified' and \
                    responses['BIRTH_YEAR'] != 'Unspecified':
                birthdate = datetime(
                    int(responses['BIRTH_YEAR']),
                    int(month_lookup[responses['BIRTH_MONTH']]),
                    1)
                now = datetime.now()
                md[1][barcode]['AGE_MONTHS'] = self._months_between_dates(
                    birthdate, now)
                md[1][barcode]['AGE_YEARS'] = responses['AGE_MONTHS'] / 12.0
            else:
                md[1][barcode]['AGE_MONTHS'] = 'Unspecified'
                md[1][barcode]['AGE_YEARS'] = 'Unspecified'

            # GENDER to SEX
            sex = md[1][barcode]['GENDER']
            del md[1][barcode]['GENDER']
            if type(sex) == str:
                sex = sex.lower()
            md[1][barcode]['SEX'] = sex

            # get COUNTRY from barcode_info
            md[1][barcode]['COUNTRY'] = country_lookup[
                barcode_info[barcode]['country'].lower()]

            # Add MiMARKS TOT_MASS and HEIGHT_OR_LENGTH columns
            md[1][barcode]['TOT_MASS'] = md[1][barcode]['WEIGHT_KG']
            md[1][barcode]['HEIGHT_OR_LENGTH'] = md[1][barcode]['HEIGHT_CM']

            # convenience variable
            site = barcode_info[barcode]['site_sampled']

            # Invariant information
            md[1][barcode]['ANONYMIZED_NAME'] = barcode
            md[1][barcode]['HOST_TAXID'] = 9606
            md[1][barcode]['TITLE'] = 'American Gut Project'
            md[1][barcode]['ALTITUDE'] = 0
            md[1][barcode]['ASSIGNED_FROM_GEO'] = 'Yes'
            md[1][barcode]['ENV_BIOME'] = 'ENVO:dense settlement biome'
            md[1][barcode]['ENV_FEATURE'] = 'ENVO:human-associated habitat'
            md[1][barcode]['DEPTH'] = 0

            # Sample-dependent information
            try:
                md[1][barcode]['LATITUDE'] = \
                    zip_lookup[md[1][barcode]['ZIP_CODE']][0]
                md[1][barcode]['LONGITUDE'] = \
                    zip_lookup[md[1][barcode]['ZIP_CODE']][1]
                md[1][barcode]['ELEVATION'] = \
                    zip_lookup[md[1][barcode]['ZIP_CODE']][2]
            except KeyError:
                #zipcode is unknown, so leave as blank
                md[1][barcode]['LATITUDE'] = ''
                md[1][barcode]['LONGITUDE'] = ''
                md[1][barcode]['ELEVATION'] = ''

            md[1][barcode]['SURVEY_ID'] = survey_lookup[barcode]
            try:
                md[1][barcode]['TAXON_ID'] = md_lookup[site]['TAXON_ID']
            except Exception as e:
                print("BARCODE:", barcode, "  SITE:", site)
                raise e

            md[1][barcode]['COMMON_NAME'] = md_lookup[site]['COMMON_NAME']
            md[1][barcode]['COLLECTION_DATE'] = \
                barcode_info[barcode]['sample_date']
            md[1][barcode]['ENV_MATTER'] = md_lookup[site]['ENV_MATTER']
            md[1][barcode]['SCIENTIFIC_NAME'] = md_lookup[site]['SCIENTIFIC_NAME']
            md[1][barcode]['SAMPLE_TYPE'] = md_lookup[site]['SAMPLE_TYPE']
            md[1][barcode]['BODY_HABITAT'] = md_lookup[site]['BODY_HABITAT']
            md[1][barcode]['BODY_SITE'] = md_lookup[site]['BODY_SITE']
            md[1][barcode]['BODY_PRODUCT'] = md_lookup[site]['BODY_PRODUCT']
            md[1][barcode]['HOST_SUBJECT_ID'] = md5(
                barcode_info[barcode]['ag_login_id'] +
                barcode_info[barcode]['participant_name']).hexdigest()
            if md[1][barcode]['WEIGHT_KG'] and md[1][barcode]['HEIGHT_CM']:
                md[1][barcode]['BMI'] = md[1][barcode]['WEIGHT_KG'] / \
                    (md[1][barcode]['HEIGHT_CM']/100)**2
            else:
                md[1][barcode]['BMI'] = ''
            md[1][barcode]['PUBLIC'] = 'Yes'

        return md

    def pulldown(self, barcodes):
        """Pulls down AG metadata for given barcodes

        Parameters
        ----------
        barcodes : list of str
            Barcodes to pull metadata down for

        Returns
        -------
        metadata : dict of str
            Tab delimited qiita sample template, keyed to survey ID it came
            from
        failures : list of str
            Barcodes unable to pull metadata down for
        """
        all_survey_info = self.get_surveys(barcodes)
        if len(all_survey_info) == 0:
            # No barcodes given match any survey
            failures = set(barcodes)
            return {}, failures
        all_results = self.format_survey_data(all_survey_info)

        # keep track of which barcodes were seen so we know which weren't
        barcodes_seen = set()

        metadata = {}
        for survey, bc_responses in all_results.items():
            headers = sorted(bc_responses.values()[0])
            survey_md = [''.join(['SAMPLE_NAME\t', '\t'.join(headers)])]
            for barcode, shortnames_answers in sorted(bc_responses.items()):
                barcodes_seen.add(barcode)
                ordered_answers = [shortnames_answers[h] for h in headers]
                ordered_answers = '\t'.join([str(x) for x in ordered_answers])
                survey_md.append('\t'.join([barcode, ordered_answers]))
            metadata[survey] = '\n'.join(survey_md)

        failures = sorted(set(barcodes) - barcodes_seen)

        return metadata, failures

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
            (defult all)

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
        """
        sql = """INSERT INTO ag.external_survey_sources
                 (external_survey, external_survey_description,
                  external_survey_url)
                 VALUES (%s, %s, %s)
                 RETURNING external_survey_id"""
        return self._con.execute_fetchone(sql, [survey, description, url])[0]

    def store_external_survey(self, in_file, survey, pulldown_date=None,
                              seperator="\t", survey_id_col="survey_id"):
        """Stores third party survey answers in the database

        Parameters
        ----------
        in_file : str
            Filepath to the survey answers spreadsheet
        survey : str
            What third party survey this belongs to
        pulldown_date : datetime object, optional
            When the data was pulled from the external source, default now()
        seperator : str, optional
            What seperator is used, default tab
        survey_id_col : str
            What column header holds the associated user AG survey id
            Default 'survey_id'

        Raises
        ------
        ValueError
            Survey passed is not found
        """
        # Get the external survey ID
        sql = """SELECT external_survey_id
                 FROM external_survey_sources
                 WHERE external_survey = %s"""
        external_id = self._con.execute_fetchall(sql, [survey])
        if not external_id:
            raise ValueError("Unknown external survey: %s" % survey)
        external_id = external_id[0]
        if pulldown_date is None:
            pulldown_date = datetime.now()

        # Load file data into insertable json format
        inserts = []
        with open(in_file) as f:
            header = f.readline().strip().split('\t')
            for line in f.readlines():
                line = line.strip()
                hold = {h: v for h, v in zip(header, line.split('\t'))}
                sid = hold[survey_id_col]
                del hold[survey_id_col]
                inserts.append([sid, external_id, pulldown_date, dumps(hold)])

        # insert into the database
        sql = """INSERT INTO ag.external_survey_answers
                 (survey_id, external_survey_id, pulldown_date, answers)
                 VALUES (%s, %s, %s, %s)"""
        self._con.executemany(sql, inserts)

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
                 WHERE external_survey = %s{0}
                 ORDER BY pulldown_date ASC)"""
        sql_args = [survey]
        format_str = ""
        if pulldown_date is not None:
            format_str = " AND pulldown_date = %s "
            sql_args.append(pulldown_date)

        return {s: loads(a)
                for s, a in self._con.execute_fetchall(
                    sql.format(format_str), sql_args)}

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
                      zip, country):
        self._con.execute_proc_return_cursor(
            'ag_update_login', [ag_login_id, email.strip().lower(), name,
                                address, city, state, zip, country])

    def updateAGKit(self, ag_kit_id, supplied_kit_id, kit_password,
                    swabs_per_kit, kit_verification_code):
        kit_password = hashpw(kit_password)

        self._con.execute_proc_return_cursor('ag_update_kit',
                                   [ag_kit_id, supplied_kit_id,
                                    kit_password, swabs_per_kit,
                                    kit_verification_code])

    def updateAGBarcode(self, barcode, ag_kit_id, site_sampled,
                        environment_sampled, sample_date, sample_time,
                        participant_name, notes, refunded, withdrawn):
        self._con.execute_proc_return_cursor('ag_update_barcode',
                                   [barcode, ag_kit_id, site_sampled,
                                    environment_sampled,
                                    sample_date, sample_time,
                                    participant_name, notes,
                                    refunded, withdrawn])

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
            sql = """SELECT cast(ag_login_id as varchar(100)) FROM ag_login
                WHERE cannot_geocode = 'y'"""
            logins = [x[0] for x in self._con.execute_fetchall(sql)]
            print logins

            for ag_login_id in logins:
                self.updateGeoInfo(ag_login_id, None, None, None, '')

        # get logins that have not been geocoded yet
        sql = """SELECT city, state, zip, country,
                     cast(ag_login_id as varchar(100))
                FROM ag_login
                WHERE elevation is NULL AND cannot_geocode is NULL"""
        logins = self._con.execute_fetchall(sql)

        row_counter = 0
        for row in logins:
            row_counter += 1
            if limit is not None and row_counter > limit:
                break

            ag_login_id = row[4]
            # Attempt to geocode
            address = '{0} {1} {2} {3}'.format(row[0], row[1], row[2], row[3])
            encoded_address = urllib.urlencode({'address': address})
            url = '/maps/api/geocode/json?{0}&sensor=false'.format(
                encoded_address)

            r = self.getGeocodeJSON(url)

            if r in ('unknown_error', 'not_OK', 'no_results'):
                # Could not geocode, mark it so we don't try next time
                self.updateGeoInfo(ag_login_id, None, None, None, 'y')
                continue
            elif r == 'over_limit':
                # If the reason for failure is merely that we are over the
                # Google API limit, then we should try again next time
                # ... but we should stop hitting their servers, so raise an
                # exception
                raise GoogleAPILimitExceeded("Exceeded Google API limit")

            # Unpack it and write to DB
            lat, lon = r

            encoded_lat_lon = urllib.urlencode(
                {'locations': ','.join(map(str, [lat, lon]))})

            url2 = '/maps/api/elevation/json?{0}&sensor=false'.format(
                encoded_lat_lon)

            r2 = self.getElevationJSON(url2)

            if r2 in ('unknown_error', 'not_OK', 'no_results'):
                # Could not geocode, mark it so we don't try next time
                self.updateGeoInfo(ag_login_id, None, None, None, 'y')
                continue
            elif r2 == 'over_limit':
                # If the reason for failure is merely that we are over the
                # Google API limit, then we should try again next time
                # ... but we should stop hitting their servers, so raise an
                # exception
                raise GoogleAPILimitExceeded("Exceeded Google API limit")

            elevation = r2

            self.updateGeoInfo(ag_login_id, lat, lon, elevation, '')

    def getGeocodeJSON(self, url):
        conn = httplib.HTTPConnection('maps.googleapis.com')
        success = False
        num_tries = 0
        while num_tries < 2 and not success:
            conn.request('GET', url)
            result = conn.getresponse()

            # Make sure we get an 'OK' status
            if result.status != 200:
                return 'not_OK'

            data = json.loads(result.read())

            # if we're over the query limit, wait 2 seconds and try again,
            # it may just be that we're submitting requests too fast
            if data.get('status', None) == 'OVER_QUERY_LIMIT':
                num_tries += 1
                sleep(2)
            elif 'results' in data:
                success = True
            else:
                return 'unknown_error'

        conn.close()

        # if we got here without getting an unknown_error or succeeding, then
        # we are over the request limit for the 24 hour period
        if not success:
            return 'over_limit'

        # sanity check the data returned by Google and return the lat/lng
        if len(data['results']) == 0:
            return 'no_results'

        geometry = data['results'][0].get('geometry', {})
        location = geometry.get('location', {})
        lat = location.get('lat', {})
        lon = location.get('lng', {})

        if not lat or not lon:
            return 'unknown_error'

        return (lat, lon)

    def getElevationJSON(self, url):
        """Use Google's Maps API to retrieve an elevation

        url should be formatted as described here:
        https://developers.google.com/maps/documentation/elevation
        /#ElevationRequests

        The number of API requests is limited to 2500 per 24 hour period.
        If this function is called and the limit is surpassed, the return value
        will be "over_limit".  Other errors will cause the return value to be
        "unknown_error".  On success, the return value is the elevation of the
        location requested in the url.
        """
        conn = httplib.HTTPConnection('maps.googleapis.com')
        success = False
        num_tries = 0
        while num_tries < 2 and not success:
            conn.request('GET', url)
            result = conn.getresponse()

            # Make sure we get an 'OK' status
            if result.status != 200:
                return 'not_OK'

            data = json.loads(result.read())

            # if we're over the query limit, wait 2 seconds and try again,
            # it may just be that we're submitting requests too fast
            if data.get('status', None) == 'OVER_QUERY_LIMIT':
                num_tries += 1
                sleep(2)
            elif 'results' in data:
                success = True
            else:
                return 'unknown_error'

        conn.close()

        # if we got here without getting an unknown_error or succeeding, then
        # we are over the request limit for the 24 hour period
        if not success:
            return 'over_limit'

        # sanity check the data returned by Google and return the lat/lng
        if len(data['results']) == 0:
            return 'no_results'

        elevation = data['results'][0].get('elevation', {})

        if not elevation:
            return 'unknown_error'

        return elevation

    def updateGeoInfo(self, ag_login_id, lat, lon, elevation, cannot_geocode):
        sql = """UPDATE  ag_login
                 SET latitude = %s,
                     longitude = %s,
                     elevation = %s,
                     cannot_geocode = %s
                 WHERE ag_login_id = %s"""
        self._con.execute(sql, [lat, lon, elevation, cannot_geocode, ag_login_id])

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
        results = self._con.execute_proc_return_cursor('ag_stats', [])
        ag_stats = results.fetchall()
        results.close()
        return ag_stats

    def updateAKB(self, barcode, moldy, overloaded, other, other_text,
                  date_of_last_email):
        """ Update ag_kit_barcodes table.
        """
        sql = """UPDATE  ag_kit_barcodes
                 SET moldy = %s, overloaded = %s, other = %s,
                     other_text = %s, date_of_last_email = %s
                 WHERE barcode = %s"""
        self._con.execute(sql, [moldy, overloaded, other,
                          other_text, date_of_last_email, barcode])

    def updateBarcodeStatus(self, status, postmark, scan_date, barcode,
                            biomass_remaining, sequencing_status, obsolete):
        """ Updates a barcode's status
        """
        sql = """update  barcode
        set     status = %s,
            sample_postmark_date = %s,
            scan_date = %s,
            biomass_remaining = %s,
            sequencing_status = %s,
            obsolete = %s
        where   barcode = %s"""
        self._con.execute(sql, [status, postmark, scan_date, biomass_remaining,
                                sequencing_status, obsolete, barcode])

    def search_participant_info(self, term):
        sql = """select   cast(ag_login_id as varchar(100)) as ag_login_id
                 from    ag_login al
                 where   lower(email) like %s or lower(name) like
                 %s or lower(address) like %s"""
        liketerm = '%%' + term.lower() + '%%'
        results = self._con.execute_fetchall(sql, [liketerm, liketerm, liketerm])
        return [x[0] for x in results]

    def search_kits(self, term):
        sql = """ select  cast(ag_login_id as varchar(100)) as ag_login_id
                 from    ag_kit
                 where   lower(supplied_kit_id) like %s or
                 lower(kit_password) like %s or
                 lower(kit_verification_code) = %s"""
        liketerm = '%%' + term.lower() + '%%'
        results = self._con.execute_fetchall(sql, [liketerm, liketerm, liketerm])
        return [x[0] for x in results]

    def search_barcodes(self, term):
        sql = """select  cast(ak.ag_login_id as varchar(100)) as ag_login_id
                 from    ag_kit ak
                 inner join ag_kit_barcodes akb
                 on ak.ag_kit_id = akb.ag_kit_id
                 where   barcode like %s or lower(participant_name) like
                 %s or lower(notes) like %s"""
        liketerm = '%%' + term.lower() + '%%'
        results = self._con.execute_fetchall(sql, [liketerm, liketerm, liketerm])
        return [x[0] for x in results]

    def get_kit_info_by_login(self, ag_login_id):
        sql = """select  cast(ag_kit_id as varchar(100)) as ag_kit_id,
                        cast(ag_login_id as varchar(100)) as ag_login_id,
                        supplied_kit_id, kit_password, swabs_per_kit,
                        kit_verification_code, kit_verified
                from    ag_kit
                where   ag_login_id = %s"""
        self._con.execute_fetchdict(sql, [ag_login_id])
        return []

    def search_handout_kits(self, term):
        sql = """SELECT kit_id, password, barcode, verification_code
                 FROM ag_handout_kits
                 JOIN (SELECT kit_id, barcode, sample_barcode_file
                    FROM ag.ag_handout_barcodes
                    GROUP BY kit_id, barcode) AS hb USING (kit_id)
                 WHERE kit_id LIKE %s or barcode LIKE %s"""
        liketerm = '%%' + term + '%%'
        results = self._con.execute_fetchall(sql, [liketerm, liketerm])
        return [x[0] for x in results]

    def get_login_by_email(self, email):
        sql = """select name, address, city, state, zip, country, ag_login_id
                 from ag_login where email = %s"""
        cursor.execute(sql, [email])
        col_names = self._get_col_names_from_cursor(cursor)
        row = cursor.fetchone()

        login = {}
        if row:
            login = dict(zip(col_names, row))
            login['email'] = email

        return login

    def get_login_info(self, ag_login_id):
        sql = """SELECT  ag_login_id, email, name, address, city, state, zip,
                         country
                 FROM    ag_login
                 WHERE   ag_login_id = %s"""
        return [dict(row) for row in self._con.execute_fetchall(sql, [ag_login_id])]

    def getAGBarcodeDetails(self, barcode):
        results = self._con.execute_proc_return_cursor(
            'ag_get_barcode_details', [barcode])
        barcode_details = results.fetchone()
        col_names = self._get_col_names_from_cursor(results)
        results.close()

        row_dict = {}
        if barcode_details:
            row_dict = dict(zip(col_names, barcode_details))

        return row_dict

    def getHumanParticipants(self, ag_login_id):
        # get people from new survey setup
        sql = """SELECT participant_name from ag.ag_login_surveys
                 JOIN ag.survey_answers USING (survey_id)
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
        sql = """SELECT participant_name from ag.ag_login_surveys
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
        sql = """select  p.plate, p.sequence_date
                 from    plate p inner join plate_barcode pb on
                 pb.plate_id = p.plate_id \
                where   pb.barcode = %s"""
        cursor.execute(sql, [barcode])
        col_names = [x[0] for x in cursor.description]
        results = [dict(zip(col_names, row)) for row in cursor.fetchall()]
        cursor.close()
        return results

    def getBarcodeProjType(self, barcode):
        """ Get the project type of the barcode.
            Return a tuple of project and project type.
        """
        sql = """select p.project from project p inner join
                 project_barcode pb on (pb.project_id = p.project_id)
                 where pb.barcode = %s"""
        results = self._con.execute_fetchone(sql, [barcode])
        proj = results[0]
        #this will get changed to get the project type from the db
        if proj in ('American Gut Project', 'ICU Microbiome', 'Handout Kits',
                    'Office Succession Study',
                    'American Gut Project: Functional Feces',
                    'Down Syndrome Microbiome', 'Beyond Bacteria',
                    'All in the Family', 'American Gut Handout kit',
                    'Personal Genome Project', 'Sleep Study',
                    'Anxiety/Depression cohort', 'Alzheimers Study'):
            proj_type = 'American Gut'
        else:
            proj_type = proj
        return (proj, proj_type)

    def setBarcodeProjType(self, project, barcode):
        """sets the project type of the barcodel

            project is the project name from the project table
            barcode is the barcode
        """
        sql = """UPDATE project_barcode
                 SET project_id =
                (select project_id from project where project = %s)
                where barcode = %s"""
        self._con.execute(sql, [project, barcode])

    def getProjectNames(self):
        """Returns a list of project names
        """
        sql = """SELECT project FROM project"""
        return [x[0] for x in self._con.execute_fetchall(sql)]

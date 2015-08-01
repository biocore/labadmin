from contextlib import contextmanager
from collections import defaultdict, namedtuple
from re import sub
from hashlib import md5
from datetime import datetime

from bcrypt import hashpw, gensalt

from psycopg2 import connect, Error as PostgresError
from psycopg2.extras import DictCursor

from util import make_valid_kit_ids, make_verification_code, make_passwd


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
    def __init__(self, config):
        self._con = SQLHandler(config)
        self._con.execute('set search_path to ag, barcodes, public')

    def get_barcode_details(self, barcodes):
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

        # For use with SQL query "IN (...)" clause
        barcodes_formatted = "'%s'" % "', '".join(barcodes)

        sql = """SELECT akb.barcode, *
                 FROM ag_kit_barcodes akb JOIN ag_kit ak USING (ag_kit_id)
                 JOIN ag_login al USING (ag_login_id)
                 WHERE akb.barcode in ({})""".format(barcodes_formatted)

        with self._con.cursor() as cur:
            cur.execute(sql)
            headers = [x[0] for x in cur.description][1:]
            results = {row[0]: dict(zip(headers, row[1:]))
                       for row in cur.fetchall()}

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

        # For use with SQL query "IN (...)" clause
        barcodes_formatted = "'%s'" % "', '".join(barcodes)

        # SINGLE answers SQL
        single_sql = """SELECT S.survey_id, AKB.barcode, SQ.question_shortname,
                               SA.response
                 FROM ag_kit_barcodes AKB
                      JOIN survey_answers SA ON
                        AKB.survey_id=SA.survey_id
                      JOIN survey_question SQ
                        ON SA.survey_question_id=SQ.survey_question_id
                      JOIN survey_question_response_type SQRTYPE
                        ON SQ.survey_question_id=SQRTYPE.survey_question_id
                      JOIN group_questions GQ
                        ON SQ.survey_question_id = GQ.survey_question_id
                      JOIN survey_group SG
                        ON GQ.survey_group = SG.group_order
                      JOIN surveys S
                        ON SG.group_order = S.survey_group
                 WHERE sqrtype.survey_response_type='SINGLE'
                      AND AKB.barcode in ({})""".format(barcodes_formatted)

        # MULTIPLE answers SQL
        multiple_sql = """SELECT S.survey_id, AKB.barcode,
                                 SQ.question_shortname,
                                 array_agg(SA.response) as responses
                 FROM ag_kit_barcodes AKB
                      JOIN survey_answers SA ON
                        AKB.survey_id=SA.survey_id
                      JOIN survey_question SQ
                        ON SA.survey_question_id=SQ.survey_question_id
                      JOIN survey_question_response_type SQRTYPE
                        ON SQ.survey_question_id=SQRTYPE.survey_question_id
                      JOIN group_questions GQ
                        ON SQ.survey_question_id = GQ.survey_question_id
                      JOIN survey_group SG
                        ON GQ.survey_group = SG.group_order
                      JOIN surveys S
                        ON SG.group_order = S.survey_group
                 WHERE sqrtype.survey_response_type='MULTIPLE'
                      AND AKB.barcode in ({})
                 GROUP BY S.survey_id, AKB.barcode, SQ.question_shortname
                 """.format(barcodes_formatted)

        # Also need to get the possible responses for multiples
        multiple_responses_sql = """
            SELECT SQ.question_shortname, SQR.response
            FROM survey_question SQ
            JOIN survey_question_response_type SQRTYPE
                 ON SQ.survey_question_id = SQRTYPE.survey_question_id
            JOIN survey_question_response SQR
                 ON SQ.survey_question_id = SQR.survey_question_id
            WHERE SQRTYPE.survey_response_type = 'MULTIPLE'"""

        # STRING and TEXT answers SQL
        others_sql = """SELECT S.survey_id, AKB.barcode,
                        SQ.question_shortname, SA.response
                 FROM ag_kit_barcodes AKB
                      JOIN survey_answers_other SA ON
                        AKB.survey_id=SA.survey_id
                      JOIN survey_question SQ
                        ON SA.survey_question_id=SQ.survey_question_id
                      JOIN survey_question_response_type SQRTYPE
                        ON SQ.survey_question_id=SQRTYPE.survey_question_id
                      JOIN group_questions GQ
                        ON SQ.survey_question_id = GQ.survey_question_id
                      JOIN survey_group SG
                        ON GQ.survey_group = SG.group_order
                      JOIN surveys S
                        ON SG.group_order = S.survey_group
                 WHERE sqrtype.survey_response_type in ('STRING', 'TEXT')
                      AND AKB.barcode in ({})""".format(barcodes_formatted)

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
        def _format_responses_as_dict(sql, json=False, multiple=False):
            ret_dict = defaultdict(lambda: defaultdict(dict))
            for survey, barcode, q, a in self._con.execute_fetchall(sql):
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
        all_barcodes = set.union(*[set(md[s]) for s in md])
        barcode_info = self.get_barcode_details(all_barcodes)

        # Human survey (id 1)

        # standard fields that are set based on sampling site
        md_lookup = {
            'Hair':
                {'BODY_PRODUCT': 'UBERON:sebum',
                 'COMMON_NAME': 'human skin metagenome',
                 'SAMPLE_TYPE': 'Hair',
                 'TAXON_ID': '539655',
                 'BODY_HABITAT': 'UBERON:hair',
                 'ENV_MATTER': 'ENVO:sebum',
                 'BODY_SITE': 'UBERON:hair'},
            'Nares': {
                'BODY_PRODUCT': 'UBERON:mucus',
                'COMMON_NAME': 'human nasal/pharyngeal metagenome',
                'SAMPLE_TYPE': 'Nares',
                'TAXON_ID': '1131769',
                'BODY_HABITAT': 'UBERON:nose',
                'ENV_MATTER': 'ENVO:mucus',
                'BODY_SITE': 'UBERON:nostril'},
            'Vaginal mucus': {
                'BODY_PRODUCT': 'UBERON:mucus',
                'COMMON_NAME': 'vaginal metagenome',
                'SAMPLE_TYPE': 'Vaginal mucus',
                'TAXON_ID': '1549736',
                'BODY_HABITAT': 'UBERON:vagina',
                'ENV_MATTER': 'ENVO:mucus',
                'BODY_SITE': 'UBERON:vaginal introitus'},
            'Sole of foot': {
                'BODY_PRODUCT': 'UBERON:sebum',
                'COMMON_NAME': 'human skin metagenome',
                'SAMPLE_TYPE': 'Sole of foot',
                'TAXON_ID': '539655',
                'BODY_HABITAT': 'UBERON:skin',
                'ENV_MATTER': 'ENVO:sebum',
                'BODY_SITE': 'UBERON:skin of foot'},
            'Nasal mucus': {
                'BODY_PRODUCT': 'UBERON:mucus',
                'COMMON_NAME': 'human nasal/pharyngeal metagenome',
                'SAMPLE_TYPE': 'Nasal mucus',
                'TAXON_ID': '1131769',
                'BODY_HABITAT': 'UBERON:nose',
                'ENV_MATTER': 'ENVO:mucus',
                'BODY_SITE': 'UBERON:nostril'},
            'Stool': {
                'BODY_PRODUCT': 'UBERON:feces',
                'COMMON_NAME': 'human gut metagenome',
                'SAMPLE_TYPE': 'Stool',
                'TAXON_ID': '408170',
                'BODY_HABITAT': 'UBERON:feces',
                'ENV_MATTER': 'ENVO:feces',
                'BODY_SITE': 'UBERON:feces'},
            'Forehead': {
                'BODY_PRODUCT': 'UBERON:sebum',
                'COMMON_NAME': 'human skin metagenome',
                'SAMPLE_TYPE': 'Forehead',
                'TAXON_ID': '539655',
                'BODY_HABITAT': 'UBERON:skin',
                'ENV_MATTER': 'ENVO:sebum',
                'BODY_SITE': 'UBERON:skin of head'},
            'Tears': {
                'BODY_PRODUCT': 'UBERON:tears',
                'COMMON_NAME': 'human metagenome',
                'SAMPLE_TYPE': 'Tears',
                'TAXON_ID': '646099',
                'BODY_HABITAT': 'UBERON:eye',
                'ENV_MATTER': 'ENVO:tears',
                'BODY_SITE': 'UBERON:eye'},
            'Right hand': {
                'BODY_PRODUCT': 'UBERON:sebum',
                'COMMON_NAME': 'human skin metagenome',
                'SAMPLE_TYPE': 'Right Hand',
                'TAXON_ID': '539655',
                'BODY_HABITAT': 'UBERON:skin',
                'ENV_MATTER': 'ENVO:sebum',
                'BODY_SITE': 'UBERON:skin of hand'},
            'Mouth': {
                'BODY_PRODUCT': 'UBERON:saliva',
                'COMMON_NAME': 'human oral metagenome',
                'SAMPLE_TYPE': 'Mouth',
                'TAXON_ID': '447426',
                'BODY_HABITAT': 'UBERON:oral cavity',
                'ENV_MATTER': 'ENVO:saliva',
                'BODY_SITE': 'UBERON:tongue'},
            'Left hand': {
                'BODY_PRODUCT': 'UBERON:sebum',
                'COMMON_NAME': 'human skin metagenome',
                'SAMPLE_TYPE': 'Left Hand',
                'TAXON_ID': '539655',
                'BODY_HABITAT': 'UBERON:skin',
                'ENV_MATTER': 'ENVO:sebum',
                'BODY_SITE': 'UBERON:skin of hand'},
            'Ear wax': {
                'BODY_PRODUCT': 'UBERON:ear wax',
                'COMMON_NAME': 'human metagenome',
                'SAMPLE_TYPE': 'Ear wax',
                'TAXON_ID': '646099',
                'BODY_HABITAT': 'UBERON:ear',
                'ENV_MATTER': 'ENVO:ear wax',
                'BODY_SITE': 'UBERON:external auditory meatus'}
        }

        month_lookup = {'January': 1, 'February': 2, 'March': 3,
                        'April': 4, 'May': 5, 'June': 6,
                        'July': 7, 'August': 8, 'September': 9,
                        'October': 10, 'November': 11, 'December': 12}

        # tuples are latitude, longitude, elevation
        zipcode_sql = """SELECT zipcode, latitude, longitude, elevation
                         FROM zipcodes"""
        zip_lookup = {row[0]: tuple(row[1:])
                      for row in self._con.execute_fetchall(zipcode_sql)}

        country_lookup = defaultdict(lambda: 'unknown')
        country_lookup.update({
            'united states': 'GAZ:United States of America',
            'united states of america': 'GAZ:United States of America',
            'us': 'GAZ:United States of America',
            'usa': 'GAZ:United States of America',
            'u.s.a': 'GAZ:United States of America',
            'u.s.': 'GAZ:United States of America',
            'canada': 'GAZ:Canada',
            'canadian': 'GAZ:Canada',
            'ca': 'GAZ:Canada',
            'australia': 'GAZ:Australia',
            'au': 'GAZ:Australia',
            'united kingdom': 'GAZ:United Kingdom',
            'belgium': 'GAZ:Belgium',
            'gb': 'GAZ:Great Britain',
            'korea, republic of': 'GAZ:South Korea',
            'nl': 'GAZ:Netherlands',
            'netherlands': 'GAZ:Netherlands',
            'spain': 'GAZ:Spain',
            'es': 'GAZ:Spain',
            'norway': 'GAZ:Norway',
            'germany': 'GAZ:Germany',
            'de': 'GAZ:Germany',
            'china': 'GAZ:China',
            'singapore': 'GAZ:Singapore',
            'new zealand': 'GAZ:New Zealand',
            'france': 'GAZ:France',
            'fr': 'GAZ:France',
            'ch': 'GAZ:Switzerland',
            'switzerland': 'GAZ:Switzerland',
            'denmark': 'GAZ:Denmark',
            'scotland': 'GAZ:Scotland',
            'united arab emirates': 'GAZ:United Arab Emirates',
            'ireland': 'GAZ:Ireland',
            'thailand': 'GAZ:Thailand'})

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
            md[1][barcode]['SEX'] = md[1][barcode]['GENDER']

            # get COUNTRY from barcode_info
            md[1][barcode]['COUNTRY'] = country_lookup[
                barcode_info[barcode]['country'].lower()]

            # Add MiMARKS TOT_MASS and HEIGHT_OR_LENGTH columns
            md[1][barcode]['TOT_MASS'] = md[1][barcode]['WEIGHT_KG']
            md[1][barcode]['HEIGHT_OR_LENGTH'] = md[1][barcode]['HEIGHT_CM']

            # convenience variable
            site = barcode_info[barcode]['site_sampled']

            # Invariant information
            md[1][barcode]['SAMPLE_NAME'] = barcode
            md[1][barcode]['ANONYMIZED_NAME'] = barcode
            md[1][barcode]['HOST_TAXID'] = 9606
            md[1][barcode]['TITLE'] = 'American Gut Project'
            md[1][barcode]['ALTITUDE'] = 0
            md[1][barcode]['ASSIGNED_FROM_GEO'] = 'Yes'
            md[1][barcode]['ENV_BIOME'] = 'ENVO:dense settlement biome'
            md[1][barcode]['ENV_FEATURE'] = 'ENVO:human-associated habitat'
            md[1][barcode]['DEPTH'] = 0

            # Sample-dependent information
            md[1][barcode]['TAXON_ID'] = md_lookup[site]['TAXON_ID']
            md[1][barcode]['COMMON_NAME'] = md_lookup[site]['COMMON_NAME']
            md[1][barcode]['COLLECTION_DATE'] = \
                barcode_info[barcode]['sample_date']
            md[1][barcode]['LATITUDE'] = \
                zip_lookup[barcode_info[barcode]['zip']][0]
            md[1][barcode]['LONGITUDE'] = \
                zip_lookup[barcode_info[barcode]['zip']][1]
            md[1][barcode]['ELEVATION'] = \
                zip_lookup[barcode_info[barcode]['zip']][2]
            md[1][barcode]['ENV_MATTER'] = md_lookup[site]['ENV_MATTER']
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

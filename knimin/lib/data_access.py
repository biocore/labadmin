from contextlib import contextmanager
from json import loads
from collections import defaultdict
from re import sub

from psycopg2 import connect, Error as PostgresError
from psycopg2.extras import DictCursor


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
                except ValueError:
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
        self._con.execute('set search_path to ag, public')

    def authenticate_user(self, user, password):
        return True

    def get_barcode_metadata(self, barcodes):
        """Retrieve metadata for specified barcodes

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
                    # Taking 0th index here since all json are single-element
                    # lists
                    a = str(loads(a)[0])
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

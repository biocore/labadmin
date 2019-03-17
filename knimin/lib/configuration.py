#!/usr/bin/env python

import os
from os.path import join, dirname, abspath
from future import standard_library
with standard_library.hooks():
    from configparser import ConfigParser


DEFAULT_CONFIG_FP = join(dirname(abspath(__file__)), '../config.txt')


class KniminConfig(object):
    """Holds the configuration information

    Parameters
    ----------
    config_fp: str, optional
        Filepath to the configuration file

    Attributes
    ----------
    debug : bool
        If in debug state
    base_log_dir : str
        Path to the base directory where the log file will be written
    user : str
        The postgres user
    password : str
        The postgres password for the previous user
    database : str
        The postgres database to connect to
    host : str
        The host where the database lives
    port : int
        The port used to connect to the postgres database in the previous host

    Notes
    -----
    ConfigurationManager base sourced from the QIITA project
    """
    config_fp = os.environ.get('KNIMIN_CONFIG_FP', DEFAULT_CONFIG_FP)

    def __init__(self, config_fp=None):
        if config_fp is None:
            config_fp = self.config_fp

        if not os.path.exists(config_fp):
            raise IOError('Config file %s missing!' % config_fp)

        config = ConfigParser()
        with open(config_fp, 'U') as conf_file:
            config.readfp(conf_file)

        _expected_sections = {'main', 'postgres', 'tornado', 'email'}
        if set(config.sections()) != _expected_sections and \
                len(_expected_sections.difference(config.sections())) != 0:
            missing = _expected_sections - set(config.sections())
            raise ValueError("Missing sections: %s" % missing)

        self._get_main(config)
        self._get_postgres(config)
        self._get_tornado(config)
        self._get_email(config)
        self._get_vioscreen(config)
        self._get_qiita(config)

    def _get_main(self, config):
        """Get the configuration of the main section"""
        self.debug = config.getboolean('main', 'debug')
        self.help_email = config.get('main', 'help_email')
        self.base_data_dir = config.get('main', 'base_data_dir')
        self.base_log_dir = config.get('main', 'BASE_LOG_DIR')

    def _get_postgres(self, config):
        """Get the configuration of the postgres section"""
        self.db_user = config.get('postgres', 'user')
        self.db_password = config.get('postgres', 'password')
        self.db_database = config.get('postgres', 'database')
        self.db_host = config.get('postgres', 'host')
        self.db_port = config.getint('postgres', 'port')

    def _get_tornado(self, config):
        """Get tornado config bits"""
        self.http_port = config.getint('tornado', 'port')

    def _get_email(self, config):
        self.smtp_host = config.get('email', 'HOST')
        self.smtp_ssl = config.getboolean('email', 'SSL')
        self.smtp_port = config.getint('email', 'PORT')
        self.smtp_user = config.get('email', 'USERNAME')
        self.smtp_password = config.get('email', 'PASSWORD')

    def _get_vioscreen(self, config):
        self.vioscreen_user = os.environ.get('VIOSCREEN_USERNAME',
                                             config.get('vioscreen', 'user'))
        self.vioscreen_password = os.environ.get('VIOSCREEN_PASSWORD',
                                                 config.get('vioscreen',
                                                            'password'))
        self.vioscreen_regcode = os.environ.get('VIOSCREEN_REGISTRATION',
                                                config.get('vioscreen',
                                                           'registration'))

    def _get_qiita(self, config):
        self.qiita_host = config.get('qiita', 'QIITA_HOST')
        self.qiita_port = config.get('qiita', 'QIITA_PORT')
        self.qiita_client_id = config.get('qiita', 'QIITA_CLIENT_ID')
        self.qiita_client_secret = config.get('qiita', 'QIITA_CLIENT_SECRET')
        self.qiita_certificate = config.get('qiita', 'QIITA_CERT')
        self.qiita_study_id = config.get('qiita', 'QIITA_STUDY_ID')


config = KniminConfig()

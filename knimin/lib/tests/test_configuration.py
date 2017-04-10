#!/usr/bin/env python

from unittest import TestCase, main
import tempfile

from knimin.lib.configuration import KniminConfig


class ConfigurationTests(TestCase):
    def setUp(self):
        self.config = tempfile.NamedTemporaryFile()
        self.config.write(test_config)
        self.config.seek(0)
        self.config_fp = self.config.name

    def tearDown(self):
        self.config.close()

    def test_init(self):
        KniminConfig(self.config_fp)

        with self.assertRaises(IOError):
            KniminConfig('does not exist')

        # test that expection is raised if not all sections are specified
        config = tempfile.NamedTemporaryFile()
        config.write(test_config[:100])
        config.seek(0)
        config_fp = config.name
        with self.assertRaises(ValueError):
            KniminConfig(config_fp)

    def test_get_main(self):
        config = KniminConfig(self.config_fp)
        self.assertTrue(config.debug)
        self.assertEqual(config.base_data_dir, '/some/dir/path')

    def test_get_postgres(self):
        config = KniminConfig(self.config_fp)
        self.assertEqual(config.db_user, 'test')
        self.assertEqual(config.db_password, '')
        self.assertEqual(config.db_database, 'knimin')
        self.assertEqual(config.db_host, 'localhost')
        self.assertEqual(config.db_port, 5432)

    def test_get_tornado(self):
        config = KniminConfig(self.config_fp)
        self.assertEqual(config.http_port, 8888)

    def test_get_jira(self):
        config = KniminConfig(self.config_fp)
        self.assertEqual(config.jira_host, 'http://127.0.0.1:2990/jira')
        self.assertEqual(config.jira_user, 'admin')
        self.assertEqual(config.jira_password, 'admin')
        self.assertEqual(config.jira_passkey, 'mykey')

    def test_get_qiita(self):
        config = KniminConfig(self.config_fp)
        self.assertEqual(config.qiita_host, 'https://127.0.0.1:21174')
        self.assertEqual(config.qiita_client_id, 'CLIENTID')
        self.assertEqual(config.qiita_client_secret, 'CLIENTSECRET')
        self.assertEqual(config.qiita_server_cert, '/some/path/to/server.crt')


test_config = """[main]
debug = True
help_email = help@email.com
base_data_dir = /some/dir/path
BASE_LOG_DIR = /tmp

[postgres]
user = test
password =
database = knimin
host = localhost
port = 5432

[tornado]
port = 8888

[email]
HOST = localhost
PORT = 465
SSL = False
USERNAME =
PASSWORD =

[jira]
HOST = http://127.0.0.1:2990/jira
USERNAME = admin
PASSWORD = admin
PASSKEY = mykey

[qiita]
HOST = https://127.0.0.1:21174
CLIENT_ID = CLIENTID
CLIENT_SECRET = CLIENTSECRET
SERVER_CERT = /some/path/to/server.crt
"""


if __name__ == '__main__':
    main()

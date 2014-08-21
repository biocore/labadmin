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

    def test_get_main(self):
        config = KniminConfig(self.config_fp)
        self.assertTrue(config.debug)

    def test_get_postgres(self):
        config = KniminConfig(self.config_fp)
        self.assertEqual(config.user, 'test')
        self.assertEqual(config.password, '')
        self.assertEqual(config.database, 'knimin')
        self.assertEqual(config.host, 'localhost')
        self.assertEqual(config.port, 5432)


test_config = """[main]
debug = True

[postgres]
user = test
password =
database = knimin
host = localhost
port = 5432
"""


if __name__ == '__main__':
    main()

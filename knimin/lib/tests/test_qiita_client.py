# This code is based on the QiitaClient project
# https://github.com/qiita-spots/qiita_client
# and the test code in Qiita
# https://github.com/biocore/qiita
# We can't directly use the QiitaClient library because it doesn't play nice
# with the new restAPI due to the returning status codes.
# Hence, including here the copyright notice from the QiitaClient project

# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The Qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from unittest import TestCase, main

from knimin.lib.qiita_client import QiitaClient
from knimin.lib.configuration import config


class QiitaClientTests(TestCase):
    def setUp(self):
        self.tester = QiitaClient(config.qiita_host, config.qiita_client_id,
                                  config.qiita_client_secret,
                                  server_cert=config.qiita_server_cert)

    def test_init(self):
        obs = QiitaClient(config.qiita_host, config.qiita_client_id,
                          config.qiita_client_secret,
                          server_cert=config.qiita_server_cert)
        self.assertEqual(obs._server_url, config.qiita_host)
        self.assertEqual(obs._client_id, config.qiita_client_id)
        self.assertEqual(obs._client_secret, config.qiita_client_secret)
        self.assertEqual(obs._verify, config.qiita_server_cert)

    def test_get(self):
        status_code, data = self.tester.get('/api/v1/study/1/status')
        self.assertEqual(status_code, 200)
        exp = {'is_public': False,
               'has_sample_information': True,
               'sample_information_has_warnings': False,
               'preparations': [{'id': 1, 'has_artifact': True},
                                {'id': 2, 'has_artifact': True}]
               }
        self.assertEqual(data, exp)

    def test_post(self):
        payload = {'title': 'foo',
                   'study_abstract': 'stuff',
                   'study_description': 'asdasd',
                   'owner': 'doesnotexist@foo.bar',
                   'study_alias': 'blah',
                   'contacts': {'principal_investigator': [u'PIDude',
                                                           u'Wash U'],
                                'lab_person': [u'LabDude',
                                               u'knight lab']}}
        status_code, data = self.tester.post('/api/v1/study', data=payload,
                                             as_json=True)
        self.assertEqual(status_code, 403)
        self.assertEqual(data, {'message': 'Unknown user'})

    def test_patch(self):
        body = {'sampleid1': {'category_a': 'value_a'},
                'sampleid2': {'category_b': 'value_b'}}
        exp = {'message': 'Study not found'}
        status_code, data = self.tester.patch('/api/v1/study/0/samples',
                                              data=body)
        self.assertEqual(status_code, 404)
        self.assertEqual(data, exp)


if __name__ == '__main__':
    main()

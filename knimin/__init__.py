# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from knimin.lib.configuration import config
from knimin.lib.data_access import KniminAccess
from knimin.lib.ag_jira import create_jira_handler
from knimin.lib.qiita_client import QiitaClient

db = KniminAccess(config)
jira_handler = create_jira_handler(config)
qiita_client = QiitaClient(config.qiita_host, config.qiita_client_id,
                           config.qiita_client_secret,
                           server_cert=config.qiita_server_cert)

__all__ = ['db', 'jira_handler', 'qiita_client']

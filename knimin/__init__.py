#!/usr/bin/env python
from knimin.lib.configuration import config
from knimin.lib.data_access import KniminAccess
from knimin.lib.ag_jira import create_jira_handler

db = KniminAccess(config)
jira_handler = create_jira_handler(config)

__all__ = ['db', 'jira_handler']

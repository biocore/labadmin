#!/usr/bin/env python

from knimin.lib.data_access import KniminAccess
from knimin.lib.configuration import KniminConfig

config = KniminConfig()
db = KniminAccess(config)

__all__ = ['config', 'db']

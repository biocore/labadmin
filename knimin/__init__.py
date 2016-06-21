#!/usr/bin/env python
from knimin.lib.configuration import config
from knimin.lib.data_access import KniminAccess

db = KniminAccess(config)

__all__ = ['db']

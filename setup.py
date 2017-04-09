#!/usr/bin/env python

# -----------------------------------------------------------------------------
# Copyright (c) 2013, The Qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from setuptools import setup
__version__ = "0.1.0-dev"

long_description = """Knight lab admin"""

setup(name='Knight lab UI',
      version=__version__,
      long_description=long_description,
      license="BSD",
      description='',
      author="",
      author_email="mcdonadt@colorado.edu",
      url='',
      test_suite='nose.collector',
      package_data={'knimin': [],
                    'knimin.lib': [],
                    'knimin.handlers': []},
      extras_require={'test': ["nose >= 0.10.1", "pep8", "flake8", "mock",
                               "requests-mock"]},
      install_requires=['psycopg2 < 2.7', 'tornado==4.4.2', 'WTForms==2.0.1',
                        'future', 'bcrypt', 'pillow', 'python-dateutil',
                        'requests', 'mock', 'pandas', 'six', 'jira']
      )

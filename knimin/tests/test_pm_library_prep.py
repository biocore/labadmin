# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------
from unittest import main

from knimin.tests.tornado_test_base import TestHandlerBase


class TestPMLibraryPrepHandler(TestHandlerBase):
    def test_get_not_auther(self):
        response = self.get('/pm_library_prep/')
        self.assertEqual(response.code, 200)
        self.assertTrue(
            response.effective_url.endswith('?next=%2Fpm_library_prep%2F'))

    def test_get(self):
        self.mock_login_admin()
        response = self.get('/pm_library_prep/')
        self.assertEqual(response.code, 200)
        # Check that the page is not empty
        self.assertIn('<h3>Prepare a new library</h3>', response.body)


if __name__ == '__main__':
    main()

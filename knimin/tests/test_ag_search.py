from unittest import main

from tornado.escape import url_escape

from knimin.tests.tornado_test_base import TestHandlerBase
from knimin import db
from knimin.lib.util import xhtml_escape_recursive


class testAGSearchHandler(TestHandlerBase):
    def test_get_not_logged_in(self):
        db.alter_access_levels('test', [3])
        response = self.get('/ag_search/')
        self.assertEqual(response.code, 200)
        port = self.get_http_port()
        self.assertEqual(response.effective_url,
                         'http://localhost:%d/login/?next=%s' %
                         (port, url_escape('/ag_search/')))

    def test_get(self):
        self.mock_login_admin()
        response = self.get('/ag_search/')
        self.assertEqual(response.code, 200)
        self.assertIn('Find stuff.', response.body)

    def test_post_user(self):
        self.mock_login_admin()

        # search participant info
        search_term = 'qdkwzpkuci@yrvxr.com'
        response = self.post('/ag_search/', {'search_term': search_term})
        self.assertEqual(response.code, 200)
        for login in db.search_participant_info(search_term):
            for l in db.get_login_info(login):
                for field in l:
                    if field == 'ag_login_id':
                        self.assertNotIn(l[field], response.body)
                    else:
                        self.assertIn(l[field], response.body)

    def test_post_kit(self):
        self.mock_login_admin()

        search_term = 'tst_zpdIN'
        response = self.post('/ag_search/', {'search_term': search_term})
        self.assertEqual(response.code, 200)
        for kit_id in db.search_kits(search_term):
            for kit in db.get_kit_info_by_login(kit_id):
                for field in kit:
                    if (field != 'ag_kit_id') and (field != 'ag_login_id'):
                        self.assertIn(str(kit[field]), response.body)

    def test_post_barcode(self):
        self.mock_login_admin()

        search_term = '000028538'
        response = self.post('/ag_search/', {'search_term': search_term})
        self.assertEqual(response.code, 200)
        for barcode in db.search_barcodes(search_term):
            kit_id = db.get_kit_info_by_login(barcode)[0]['ag_kit_id']
            for sample in db.get_barcode_info_by_kit_id(kit_id):
                for field in sample:
                    if sample[field] is not None:
                        if (field == 'ag_kit_id') or \
                           (field == 'ag_kit_barcode_id'):
                            self.assertNotIn(sample[field], response.body)
                        else:
                            exp = xhtml_escape_recursive(sample[field])
                            self.assertIn(str(exp),
                                          response.body)

    def test_search_barcodes(self):
        # Elaine Wolfe found the following bug, May 13th 2017:
        # Barcodes in a kit do not show up unless they are logged when
        # searched.
        # (This can be annoying if we are trying to look up barcode numbers
        # based on names/kit IDs.)
        self.mock_login_admin()

        # a barcode that is member of a kit AND is assigned to at least one
        # survey
        # SELECT barcode FROM ag.source_barcodes_surveys LIMIT 1;
        barcode_assigned = '000026028'
        response = self.post('/ag_search/', {'search_term': barcode_assigned})
        self.assertEqual(response.code, 200)
        self.assertIn('/ag_edit_barcode/?barcode=%s' % barcode_assigned,
                      response.body)

        # a barcode that is member of a kit, but not assigned to any survey
        # SELECT barcode FROM ag.ag_kit_barcodes WHERE barcode NOT IN
        #        (SELECT barcode FROM ag.source_barcodes_surveys) LIMIT 1;
        barcode_nosurvey = '000020299'
        response = self.post('/ag_search/', {'search_term': barcode_nosurvey})
        self.assertEqual(response.code, 200)
        self.assertIn('/ag_edit_barcode/?barcode=%s' % barcode_nosurvey,
                      response.body)

        # a barcode that is NOT member of any kit and therefore not assigned
        # to any survey
        # SELECT barcode FROM barcodes.barcode WHERE barcode NOT IN
        #        (SELECT barcode FROM ag.ag_kit_barcodes) LIMIT 1;
        barcode_nokit = '000016453'
        response = self.post('/ag_search/',
                             {'search_term': barcode_nokit})
        self.assertEqual(response.code, 200)
        self.assertNotIn('/ag_edit_barcode/?barcode=%s' % barcode_nokit,
                         response.body)


if __name__ == '__main__':
    main()

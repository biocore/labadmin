from unittest import main

from tornado.escape import url_escape
from json import loads, dumps

from knimin.tests.tornado_test_base import TestHandlerBase
from knimin import db


class TestAGNewKitDLHandler(TestHandlerBase):
    def test_get_not_authed(self):
        response = self.get('/ag_new_kit/download/')
        self.assertEqual(response.code, 405)  # Method Not Allowed

    def test_post(self):
        self.mock_login_admin()

        # fake kitinfo data structure
        kitinfo = [["xxx_pggwy", "96812490", "23577",
                    ["000033914", "000033915"]],
                   ["xxx_drcrv", "33422033", "56486",
                    ["000033916", "000033917"]]]
        response = self.post('/ag_new_kit/download/',
                             {'kitinfo': dumps(kitinfo),
                              'fields': ('kit_id,password,verification_code,'
                                         'barcodes')})
        self.assertEqual(response.code, 200)
        # is it necessary to unpack the zipfile and check its content?
        self.assertEqual(response.headers['Content-Disposition'],
                         'attachment; filename=kitinfo.zip')


class TestAGNewKitHandler(TestHandlerBase):
    def test_get_not_authed(self):
        response = self.get('/ag_new_kit/')
        self.assertEqual(response.code, 200)
        port = self.get_http_port()
        self.assertEqual(response.effective_url,
                         'http://localhost:%d/login/?next=%s' %
                         (port, url_escape('/ag_new_kit/')))

    def test_get(self):
        self.mock_login_admin()
        response = self.get('/ag_new_kit/')
        self.assertEqual(response.code, 200)
        for project in db.getProjectNames():
            self.assertIn("<option value='%s'>%s</option>" %
                          (project, project), response.body)
        self.assertIn("%i</span> unassigned barcodes" %
                      len(db.get_unassigned_barcodes()), response.body)

    def test_post(self):
        self.mock_login_admin()
        kits = [1, 2]
        swabs = [2, 2]
        tag = 'abc'

        # check for correct results
        response = self.post('/ag_new_kit/',
                             {'tag': tag,
                              'projects': ['PROJECT2', 'PROJECT5'],
                              'swabs': swabs,
                              'kits': kits,
                              })
        kitinfo = loads(response.body)
        self.assertEqual(len(kitinfo['kitinfo']), sum(kits))
        for k in kitinfo['kitinfo']:
            self.assertIn(tag, k[0])
        self.assertEqual(len(kitinfo['kitinfo'][0][-1]), swabs[0])
        self.assertEqual(len(kitinfo['kitinfo'][1][-1]), swabs[1])
        self.assertEqual(kitinfo['fields'],
                         "kit_id,password,verification_code,barcodes")

        # missing argument
        response = self.post('/ag_new_kit/',
                             {'projects': ['PROJECT2', 'PROJECT5'],
                              'swabs': swabs,
                              'kits': kits,
                              })
        self.assertEqual(response.code, 400)

        # too long tag
        response = self.post('/ag_new_kit/',
                             {'tag': 'toolongtag',
                              'projects': ['PROJECT2', 'PROJECT5'],
                              'swabs': swabs,
                              'kits': kits,
                              })
        # TODO: we should find more speaking ways to report an error to the
        # user, see issue: #113
        self.assertEqual(response.code, 500)
        self.assertIn("Tag must be 4 or less characters", response.body)

        # test that non existing projects are recognized.
        response = self.post('/ag_new_kit/',
                             {'tag': 'abc',
                              'projects': ['doesNotExist', 'PROJECT5'],
                              'swabs': swabs,
                              'kits': kits,
                              })
        self.assertEqual(response.code, 500)
        self.assertIn("Project(s) given don\'t exist in database:",
                      response.body)

        # check for empty swabs list
        response = self.post('/ag_new_kit/',
                             {'tag': tag,
                              'projects': ['PROJECT2', 'PROJECT5'],
                              'swabs': [],
                              'kits': kits,
                              })
        self.assertEqual(response.code, 500)
        self.assertIn("SET assigned_on = NOW() WHERE barcode IN ()",
                      response.body)

        # no kits given
        response = self.post('/ag_new_kit/',
                             {'tag': tag,
                              'projects': ['PROJECT2', 'PROJECT5'],
                              'swabs': swabs,
                              'kits': [],
                              })
        self.assertEqual(response.code, 500)
        self.assertIn("SET assigned_on = NOW() WHERE barcode IN ()",
                      response.body)

if __name__ == "__main__":
    main()

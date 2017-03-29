from unittest import main
import os
from os.path import dirname, realpath, join
from tempfile import NamedTemporaryFile

from tornado.escape import url_escape

from knimin.tests.tornado_test_base import TestHandlerBase
from knimin import db
from knimin.lib.mem_zip import extract_zip


# class testUpdateEBIStatusHandler(TestHandlerBase):
#     os.environ["ASYNC_TEST_TIMEOUT"] = "60"
#
#     def test_get_not_authed(self):
#         response = self.get('/update_ebi/')
#         self.assertEqual(response.code, 200)
#         port = self.get_http_port()
#         self.assertEqual(response.effective_url,
#                          'http://localhost:%d/login/?next=%s' %
#                          (port, url_escape('/update_ebi/')))
#
#     def test_get(self):
#         self.mock_login_admin()
#         os.environ["ASYNC_TEST_TIMEOUT"] = "60"
#
#         # test successful query
#         response = self.get('/update_ebi/')
#         self.assertIn(response.code, [200, 599])  # either success, or time out
#         if response.code == 200:
#             self.assertIn('Successfully updated barcodes in database',
#                           response.body)
#
#         # TODO: I cannot see how I can raise an Exception, since there are no
#         # input arguments necessary for the get() method
#
#
# class testAGPulldownHandler(TestHandlerBase):
#     file_empty = join(dirname(realpath(__file__)), 'data', 'barcodes.txt')
#
#     def test_get_not_authed(self):
#         response = self.get('/ag_pulldown/')
#         self.assertEqual(response.code, 200)
#         port = self.get_http_port()
#         self.assertEqual(response.effective_url,
#                          'http://localhost:%d/login/?next=%s' %
#                          (port, url_escape('/ag_pulldown/')))
#
#     def test_get(self):
#         self.mock_login_admin()
#         response = self.get('/ag_pulldown/')
#         self.assertEqual(response.code, 200)
#         for survey in db.list_external_surveys():
#             self.assertIn("<option value='%s'>%s</option>" % (survey, survey),
#                           response.body)
#         self.assertNotIn('<input type="submit" disabled>', response.body)
#         for (id, name, selected) in db.list_ag_surveys():
#             if selected:
#                 self.assertIn("<option value='%i' selected>%s</option>" %
#                               (id, name), response.body)
#             else:
#                 self.assertIn("<option value='%i' >%s</option>" %
#                               (id, name), response.body)
#
#     def test_post(self):
#         self.mock_login_admin()
#
#         # check that warnings pop up, if no barcode file is provided
#         data = {}
#         files = {'somethingelse': self.file_empty}
#         response = self.multipart_post('/ag_pulldown/', data, files)
#         self.assertEqual(response.code, 200)
#         self.assertIn("<div style='color:red;'>%s</div>" % ("No barcode file "
#                       "given, thus nothing could be pulled down."),
#                       response.body)
#
#         data = {}
#         files = {'barcodes': self.file_empty}
#         response = self.multipart_post('/ag_pulldown/', data, files)
#         self.assertEqual(response.code, 200)
#         self.assertIn(('<h3 style="color:red">Pulldown Processing, please wait'
#                        ' for file download. It may take a while with many '
#                        'barcodes.</h3>'), response.body)
#
#         data = {'external': 'cd,ef'}
#         response = self.multipart_post('/ag_pulldown/', data, files)
#         self.assertEqual(response.code, 200)
#         self.assertIn("dummy.addParameter('external', 'cd,ef');",
#                       response.body)


class testAGPulldownDLHandler(TestHandlerBase):
    def test_get_not_authed(self):
        response = self.get('/ag_pulldown/download/')
        self.assertEqual(response.code, 405)

    def test_post(self):
        self.mock_login_admin()
        response = self.post('/ag_pulldown/download/',
                             {'barcodes': (',000001448,000001447,100001449,'
                                           '000001445,000015296,000015297,'
                                           '000015298,000015299,000015300,'
                                           '000016180,000016280,000016281,'
                                           '000016282,000016283,000016284'),
                              'blanks': ('BLANK000001449,BLANK000001453,'
                                         'BLANK100001453'),
                              'external': ",".join(
                                  db.list_external_surveys()[:1]),
                              'selected_ag_surveys': "-1,-2,-3,-4,-5",
                              'merged': 'True'})
        self.assertEqual(response.headers['Content-Disposition'],
                         'attachment; filename=metadata.zip')
        self.assertIn('failures.txt', response.body)
        self.assertIn('survey_Personal_Information_md.txt', response.body)

        # store the resulting zip archive to disc ...
        tmpfile = NamedTemporaryFile(mode='w', delete=False,
                                     prefix='metadata_pulldown_single_',
                                     suffix='.zip')
        tmpfile.write(response.body)
        tmpfile.close()
        # ... and read the content as dict of strings
        result = extract_zip(tmpfile.name)
        os.remove(tmpfile.name)

        # read in the true content from data dir for comparison
        truth = extract_zip(join(dirname(realpath(__file__)), 'data',
                                 'results_barcodes.zip'))

        self.maxDiff = None
        self.assertEqual(result, truth)

    # def test_post_multiple_surverys(self):
    #     self.mock_login_admin()
    #     response = self.post('/ag_pulldown/download/',
    #                          {'barcodes': ('000033796,000033797,000033798,'
    #                                        '000033799,000033800,000033801,'
    #                                        '000033802'),
    #                           'blanks': '',
    #                           'external': '',
    #                           'selected_ag_surveys': '-1,-2,-3,-4,-5',
    #                           'merged': 'True'})
    #     self.assertEqual(response.headers['Content-Disposition'],
    #                      'attachment; filename=metadata.zip')
    #
    #     # store the resulting zip archive to disc ...
    #     tmpfile = NamedTemporaryFile(mode='w', delete=False,
    #                                  prefix='metadata_pulldown_multiple_',
    #                                  suffix='.zip')
    #     tmpfile.write(response.body)
    #     tmpfile.close()
    #     # ... and read the content as dict of strings
    #     result = extract_zip(tmpfile.name)
    #     os.remove(tmpfile.name)
    #
    #     # read in the true content from data dir for comparison
    #     truth = extract_zip(join(dirname(realpath(__file__)), 'data',
    #                              'results_multiplesurvey_barcodes.zip'))
    #
    #     self.assertEqual(result, truth)

    # def test_post_select_surveys(self):
    #     self.mock_login_admin()
    #     response = self.post('/ag_pulldown/download/',
    #                          {'barcodes': ('000033796,000033797,000033798,'
    #                                        '000033799,000033800,000033801,'
    #                                        '000033802'),
    #                           'blanks': '',
    #                           'external': '',
    #                           'selected_ag_surveys': '-2,-3,-8',
    #                           'merged': 'False'})
    #     # store the resulting zip archive to disc ...
    #     tmpfile = NamedTemporaryFile(mode='w', delete=False,
    #                                  prefix='metadata_pulldown_multiple_sel_',
    #                                  suffix='.zip')
    #     tmpfile.write(response.body)
    #     tmpfile.close()
    #     # ... and read the content as dict of strings
    #     result = extract_zip(tmpfile.name)
    #     self.assertItemsEqual(result.keys(),
    #                           ['failures.txt',
    #                            'survey_Fermented_Foods_md.txt',
    #                            'survey_Pet_Information_md.txt'])
    #     os.remove(tmpfile.name)
    #
    #     # no blanks
    #     response = self.post('/ag_pulldown/download/',
    #                          {'barcodes': ['000001445',
    #                                        '000001446',
    #                                        '000001447',
    #                                        '000001448',
    #                                        '100001449',
    #                                        '000016180',
    #                                        '000015296',
    #                                        '000015297',
    #                                        '000015298',
    #                                        '000015299',
    #                                        '000015300',
    #                                        '000016280',
    #                                        '000016281',
    #                                        '000016282',
    #                                        '000016283',
    #                                        '000016284'],
    #                           'blanks': '',
    #                           'external': db.list_external_surveys()[:1]})
    #     self.assertEqual(response.code, 200)
    #     self.assertEqual(response.headers['Content-Disposition'],
    #                      'attachment; filename=metadata.zip')
    #
    #     # no externals
    #     response = self.post('/ag_pulldown/download/',
    #                          {'barcodes': ['000001445',
    #                                        '000001446',
    #                                        '000001447',
    #                                        '000001448',
    #                                        '100001449',
    #                                        '000016180',
    #                                        '000015296',
    #                                        '000015297',
    #                                        '000015298',
    #                                        '000015299',
    #                                        '000015300',
    #                                        '000016280',
    #                                        '000016281',
    #                                        '000016282',
    #                                        '000016283',
    #                                        '000016284'],
    #                           'blanks': ['BLANK000001449',
    #                                      'BLANK000001453',
    #                                      'BLANK100001453'],
    #                           'external': ''})
    #     self.assertEqual(response.code, 200)
    #     self.assertEqual(response.headers['Content-Disposition'],
    #                      'attachment; filename=metadata.zip')


if __name__ == "__main__":
    main()

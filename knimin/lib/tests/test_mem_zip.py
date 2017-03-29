import unittest
from knimin.lib.mem_zip import InMemoryZip, extract_zip
import zipfile
import os
import io
from os.path import join, dirname, realpath


class TestInMemoryZip(unittest.TestCase):

    def setUp(self):
        self.test_fname = 'test.zip'
        self.test_out_fname = 'testout.zip'

    def tearDown(self):
        if os.path.exists(self.test_fname):
            os.remove(self.test_fname)
        if os.path.exists(self.test_out_fname):
            os.remove(self.test_out_fname)

    def test_constructor(self):
        mem = InMemoryZip()
        self.assertTrue(mem.in_memory_data is not None)
        self.assertTrue(mem.in_memory_zip is not None)
        self.assertEqual(mem.in_memory_zip.debug, 3)

    def test_append(self):
        exp_contents = 'argh'
        mem = InMemoryZip()
        mem2 = mem.append(self.test_fname, exp_contents)
        self.assertIn('test.zip',
                      mem2.in_memory_data.getvalue(),)

    def test_writetofile(self):
        exp_contents = 'argh'
        mem = InMemoryZip()
        mem2 = mem.append(self.test_fname, exp_contents)
        mem2.writetofile(self.test_out_fname)
        self.assertTrue(os.path.exists(self.test_out_fname))
        zhandle = zipfile.ZipFile(self.test_out_fname, 'r')
        res_contents = zhandle.read(self.test_fname)
        self.assertEqual(res_contents, exp_contents)

    def test_write_to_buffer(self):
        exp_contents = 'argh'
        mem = InMemoryZip()
        mem2 = mem.append(self.test_fname, exp_contents)
        res = mem2.write_to_buffer()
        # http://stackoverflow.com/a/34162395/1167475
        zhandle = zipfile.ZipFile(io.BytesIO(res))
        res_contents = zhandle.read(self.test_fname)
        self.assertEqual(res_contents, exp_contents)

    def test_extract_zip(self):
        fp_zip = join(dirname(realpath(__file__)), '..', '..', 'tests', 'data',
                      'results_multiplesurvey_barcodes.zip')
        obs = extract_zip(fp_zip)
        exp_filenames = ['survey_Surfers_md.txt', 'failures.txt',
                         'survey_Fermented_Foods_md.txt',
                         'surveys_merged_md.txt',
                         'survey_Pet_Information_md.txt']
        # check filenames
        self.assertEqual(sorted(obs.keys()), sorted(exp_filenames))
        # check file contents very briefly
        self.assertIn('SURF_BOARD_TYPE', obs['survey_Surfers_md.txt'])


if __name__ == '__main__':
    unittest.main()

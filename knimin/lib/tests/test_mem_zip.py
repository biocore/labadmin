import unittest
from knimin.lib.mem_zip import InMemoryZip
import zipfile
import zlib
from random import seed
import os
import io


class TestInMemoryZip(unittest.TestCase):

    def setUp(self):
        self.test_fname = 'test.zip'
        self.test_out_fname = 'testout.zip'

    def tearDown(self):
        self.test_fname = 'test.zip'
        if os.path.exists(self.test_fname):
            os.remove(self.test_fname)
        # if os.path.exists(self.test_out_fname):
        #     os.remove(self.test_out_fname)

    def test_constructor(self):
        mem = InMemoryZip()
        self.assertTrue(mem.in_memory_data is not None)
        self.assertTrue(mem.in_memory_zip is not None)
        self.assertEqual(mem.in_memory_zip.debug, 3)

    def test_append(self):

        test_fname = 'test.zip'
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

if __name__=='__main__':
    unittest.main()

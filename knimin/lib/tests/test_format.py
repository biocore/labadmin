import unittest

import numpy as np

from knimin.lib.format import (format_sample_sheet, format_epmotion_file,
                               format_normalization_echo_pick_list,
                               format_pooling_echo_pick_list,
                               format_index_echo_pick_list)


class FormatTests(unittest.TestCase):
    def setUp(self):
        self.basic_details = {'run_name': 'runname',
                              'assay': 'assay',
                              'fwd_cycles': 10,
                              'rev_cycles': 20,
                              'labadmin_id': 123,
                              'pi_name': 'pi',
                              'pi_email': 'pi@place.com',
                              'contact_0_name': 'contact',
                              'contact_0_email': 'contact@place.com'}

    def test_format_epmotion_file(self):
        vol = np.random.rand(8, 12) * 10
        # Put some known values
        vol[0][9] = 0
        vol[0][1] = 1.2
        obs = format_epmotion_file(vol, 1)
        # The first well is not present
        self.assertNotIn('a10', obs)
        # The second one is there
        self.assertIn('a2', obs)
        obs = obs.splitlines()
        self.assertEqual(obs[0], 'Rack,Source,Rack,Destination,Volume,Tool')
        self.assertEqual(obs[2], '1,a2,1,1,1.200,1')
        obs = format_epmotion_file(vol, 5)
        obs = obs.splitlines()
        self.assertEqual(obs[2], '1,a2,1,5,1.200,1')

    def test_format_normalization_echo_pick_list(self):
        vol_sample = np.full((4, 4), 1.5, dtype=np.float)
        vol_water = np.full((4, 4), 2.0, dtype=np.float)

        obs = format_normalization_echo_pick_list(vol_sample, vol_water)
        obs_lines = obs.splitlines()
        self.assertEqual(
            obs_lines[0],
            'Source Plate Name,Source Plate Type,Source Well,Concentration,'
            'Transfer Volume,Destination Plate Name,Destination Well')
        self.assertEqual(
            obs_lines[1],
            "water,384LDV_AQ_B2_HT,A1,,2.00,NormalizedDNA,A1")

        self.assertEqual(
            obs_lines[-1],
            "1,384LDV_AQ_B2_HT,D4,,1.50,NormalizedDNA,D4")

    def test_format_pooling_echo_pick_list(self):
        vol_sample = np.full((4, 4), 1.5, dtype=np.float)
        obs = format_pooling_echo_pick_list(vol_sample)
        obs_lines = obs.splitlines()

        self.assertEqual(
            obs_lines[0],
            'Source Plate Name,Source Plate Type,Source Well,Concentration,'
            'Transfer Volume,Destination Plate Name,Destination Well')
        self.assertEqual(
            obs_lines[1],
            "1,384LDV_AQ_B2_HT,A1,,1.50,NormalizedDNA,A1")

        self.assertEqual(
            obs_lines[-1],
            "1,384LDV_AQ_B2_HT,D4,,1.50,NormalizedDNA,A1")

    def test_format_index_echo_pick_list(self):
        idx_layout = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        volume = 2.0

        obs = format_index_echo_pick_list(idx_layout, volume)
        obs_lines = obs.splitlines()

        self.assertEqual(
            obs_lines[0],
            'Source Plate Name,Source Plate Type,Source Well,Concentration,'
            'Transfer Volume,Destination Plate Name,Destination Well')
        self.assertEqual(
            obs_lines[1],
            "IndexSourcei7,384LDV_AQ_B2_HT,A22,,2.000,IndexedDNAPlate,A1")

        self.assertEqual(
            obs_lines[-1],
            "IndexSourcei5,384LDV_AQ_B2_HT,I1,,2.000,IndexedDNAPlate,C3")

        # Try single plate
        idx_layout = [[1361, 1362, 1363], [1364, 1365, 1366],
                      [1367, 1368, 1369]]
        volume = 1.5

        obs = format_index_echo_pick_list(idx_layout, volume)
        obs_lines = obs.splitlines()

        self.assertEqual(
            obs_lines[0],
            'Source Plate Name,Source Plate Type,Source Well,Concentration,'
            'Transfer Volume,Destination Plate Name,Destination Well')
        self.assertEqual(
            obs_lines[1],
            "IndexSourcei7,384LDV_AQ_B2_HT,A1,,1.500,IndexedDNAPlate,A1")

        self.assertEqual(
            obs_lines[-1],
            "IndexSourcei7,384LDV_AQ_B2_HT,I1,,1.500,IndexedDNAPlate,C3")

    def test_format_sample_sheet_bad_instrument(self):
        self.basic_details['instrument_type'] = 'bad'
        self.basic_details['run_type'] = 'Target Gene'
        self.basic_details['sample_information'] = []

        with self.assertRaisesRegexp(ValueError, 'instrument type'):
            format_sample_sheet(**self.basic_details)

    def test_format_sample_sheet_bad_run_type(self):
        self.basic_details['instrument_type'] = 'miseq'
        self.basic_details['run_type'] = 'bad'
        self.basic_details['sample_information'] = []

        with self.assertRaisesRegexp(ValueError, 'run type'):
            format_sample_sheet(**self.basic_details)

    def test_format_sample_sheet_bad_fwd_cycles(self):
        self.basic_details['instrument_type'] = 'miseq'
        self.basic_details['run_type'] = 'Target Gene'
        self.basic_details['fwd_cycles'] = 'bad'
        self.basic_details['sample_information'] = []

        with self.assertRaisesRegexp(ValueError, 'fwd_cycles'):
            format_sample_sheet(**self.basic_details)

    def test_format_sample_sheet_bad_rev_cycles(self):
        self.basic_details['instrument_type'] = 'miseq'
        self.basic_details['run_type'] = 'Target Gene'
        self.basic_details['rev_cycles'] = 'bad'
        self.basic_details['sample_information'] = []

        with self.assertRaisesRegexp(ValueError, 'rev_cycles'):
            format_sample_sheet(**self.basic_details)

    def test_format_sample_sheet_bad_pi_contact(self):
        self.basic_details['instrument_type'] = 'miseq'
        self.basic_details['run_type'] = 'Target Gene'
        self.basic_details['pi_name'] = None
        self.basic_details['sample_information'] = []

        with self.assertRaisesRegexp(ValueError, 'pi@place.com'):
            format_sample_sheet(**self.basic_details)

    def test_format_sample_sheet_bad_other_contact(self):
        self.basic_details['instrument_type'] = 'bad'
        self.basic_details['run_type'] = 'Target Gene'
        self.basic_details['contact_0_email'] = None
        self.basic_details['sample_information'] = []

        with self.assertRaisesRegexp(ValueError, 'contact'):
            format_sample_sheet(**self.basic_details)

    def test_format_sample_sheet_miseq_target_gene(self):
        self.basic_details['instrument_type'] = 'miseq'
        self.basic_details['run_type'] = 'Target Gene'
        self.basic_details['sample_information'] = ['ignored']

        obs = format_sample_sheet(**self.basic_details)
        lines = obs.splitlines()
        self.assertEqual(lines[-1], "runname,,,,,NNNNNNNNNNNN,,,,,,")
        self.assertEqual(lines[-2], ("Sample_ID,Sample_Name,Sample_Plate,"
                                     "Sample_Well,I7_Index_ID,index,"
                                     "Sample_Project,Description,,,"))

    def test_format_sample_sheet_miseq_shotgun(self):
        self.basic_details['instrument_type'] = 'miseq'
        self.basic_details['run_type'] = 'Shotgun'
        self.basic_details['sample_information'] = [
            {'sample_id': 's1', 'i7_index_id': 'i7ida', 'i7_index': 'i7a',
             'i5_index_id': 'i5ida', 'i5_index': 'i5a'},
            {'sample_id': 's2', 'i7_index_id': 'i7idb', 'i7_index': 'i7b',
             'i5_index_id': 'i5idb', 'i5_index': 'i5b'}]

        obs = format_sample_sheet(**self.basic_details)
        lines = obs.splitlines()
        self.assertEqual(lines[-1], 's2,,,,i7idb,i7b,i5idb,i5b,,,')
        self.assertEqual(lines[-2], 's1,,,,i7ida,i7a,i5ida,i5a,,,')
        self.assertEqual(lines[-3], ('Sample_ID,Sample_Name,Sample_Plate,'
                                     'Sample_Well,I7_Index_ID,index,'
                                     'I5_Index_ID,index2,Sample_Project,'
                                     'Description,'))

    def test_format_sample_sheet_hiseq_target_gene(self):
        self.basic_details['instrument_type'] = 'hiseq'
        self.basic_details['run_type'] = 'Target Gene'
        self.basic_details['sample_information'] = [
            {'lane': 1, 'ignored': 'foo'},
            {'lane': 2, 'ignored': 'x'},
            {'lane': 1, 'ignored': 'y'},
            {'lane': 3, 'ignored': 'z'}]

        obs = format_sample_sheet(**self.basic_details)
        lines = obs.splitlines()
        self.assertEqual(lines[-1], "3,runname2,,,,,NNNNNNNNNNNN,,,,,")
        self.assertEqual(lines[-2], "2,runname1,,,,,NNNNNNNNNNNN,,,,,")
        self.assertEqual(lines[-3], "1,runname0,,,,,NNNNNNNNNNNN,,,,,")
        self.assertEqual(lines[-4], ("Lane,Sample_ID,Sample_Name,Sample_Plate,"
                                     "Sample_Well,I7_Index_ID,index,"
                                     "Sample_Project,Description,,"))

    def test_format_sample_sheet_hiseq_shotgun(self):
        self.basic_details['instrument_type'] = 'hiseq'
        self.basic_details['run_type'] = 'Shotgun'
        self.basic_details['sample_information'] = [
            {'sample_id': 's1', 'i7_index_id': 'i7ida', 'i7_index': 'i7a',
             'i5_index_id': 'i5ida', 'i5_index': 'i5a', 'lane': 1},
            {'sample_id': 's3', 'i7_index_id': 'i7idc', 'i7_index': 'i7c',
             'i5_index_id': 'i5idc', 'i5_index': 'i5c', 'lane': 2},
            {'sample_id': 's4', 'i7_index_id': 'i7idd', 'i7_index': 'i7d',
             'i5_index_id': 'i5idd', 'i5_index': 'i5d', 'lane': 1},
            {'sample_id': 's2', 'i7_index_id': 'i7idb', 'i7_index': 'i7b',
             'i5_index_id': 'i5idb', 'i5_index': 'i5b', 'lane': 2}]

        obs = format_sample_sheet(**self.basic_details)
        lines = obs.splitlines()
        self.assertEqual(lines[-1], '2,s2,,,,i7idb,i7b,i5idb,i5b,,')
        self.assertEqual(lines[-2], '1,s4,,,,i7idd,i7d,i5idd,i5d,,')
        self.assertEqual(lines[-3], '2,s3,,,,i7idc,i7c,i5idc,i5c,,')
        self.assertEqual(lines[-4], '1,s1,,,,i7ida,i7a,i5ida,i5a,,')
        self.assertEqual(lines[-5], ('Lane,Sample_ID,Sample_Name,Sample_Plate,'
                                     'Sample_Well,I7_Index_ID,index,'
                                     'I5_Index_ID,index2,Sample_Project,'
                                     'Description'))


if __name__ == '__main__':
    unittest.main()

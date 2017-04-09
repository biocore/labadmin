from unittest import main
from functools import partial

from knimin.tests.tornado_test_base import TestHandlerBase
from knimin import db


class TestPMPlateListHandler(TestHandlerBase):
    def test_get_not_authed(self):
        response = self.get(
            '/pm_plate_list/')
        self.assertEqual(response.code, 200)
        self.assertTrue(
            response.effective_url.endswith('?next=%2Fpm_plate_list%2F'))

    def test_get(self):
        # Check that the page renders correctly when no plates are present
        # in the system
        self.mock_login_admin()
        response = self.get('/pm_plate_list/')
        self.assertEqual(response.code, 200)
        # Test some information from the page
        self.assertIn('Sample Plate List', response.body)
        self.assertIn('<tbody class="list">\n\n</tbody>', response.body)

        # Add a sample plate to the system
        db.create_study(9999, title='LabAdmin test project', alias='LTP',
                        jira_id='KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))
        pt = db.get_plate_types()[0]
        plate_id = db.create_sample_plate('Test plate', pt['id'],
                                          'test', [9999])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id))

        response = self.get('/pm_plate_list/')
        self.assertEqual(response.code, 200)
        # Test some information from the page
        self.assertIn('Sample Plate List', response.body)
        exp = ('<td><a href="/pm_plate_map?plate_id=%d">Test plate</a></td>'
               % plate_id)
        self.assertIn(exp, response.body)
        self.assertIn('<i class="fa fa-battery-empty"></i>', response.body)

        # Add some samples to the plate
        samples = ['9999.Sample_%d' % i
                   for i in range(pt['cols'] * pt['rows'])]
        db.set_study_samples(9999, samples)
        layout = []
        row = []
        for i in range(pt['rows']):
            for j in range(pt['cols']):
                row.append({'sample_id': samples[i * pt['cols'] + j]})
            layout.append(row)
            row = []
        db.write_sample_plate_layout(plate_id, layout)
        response = self.get('/pm_plate_list/')
        self.assertEqual(response.code, 200)
        # Test some information from the page
        self.assertIn('Sample Plate List', response.body)
        exp = ('<td><a href="/pm_plate_map?plate_id=%d">Test plate</a></td>'
               % plate_id)
        self.assertIn(exp, response.body)
        self.assertIn('<i class="fa fa-battery-full"></i>', response.body)


if __name__ == '__main__':
    main()

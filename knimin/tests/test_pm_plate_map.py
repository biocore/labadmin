# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------
from unittest import main
from functools import partial

from tornado.escape import url_unescape, json_decode

from knimin.tests.tornado_test_base import TestHandlerBase
from knimin import db


class TestPMCreatePlateHandler(TestHandlerBase):
    def test_get_not_authed(self):
        response = self.get('/pm_create_plate/')
        self.assertEqual(response.code, 200)
        self.assertTrue(
            response.effective_url.endswith('?next=%2Fpm_create_plate%2F'))

    def test_get(self):
        self.mock_login_admin()
        response = self.get('/pm_create_plate/')
        self.assertEqual(response.code, 200)
        # Checl that the page is not empty
        self.assertIn('<label><h3>Create new plate</h3></label>',
                      response.body)

    def test_post(self):
        self.mock_login_admin()
        db.create_study(9999, 'LabAdmin test project', 'LTP', 'KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))
        data = {'plate_type': db.get_plate_types()[0]['id'],
                'studies': [9999],
                'plate_name': 'Test plate 1'}
        response = self.post('/pm_create_plate/', data=data)

        # The new plate id is encoded in the url, as the last value
        # after the last '=' character
        plate_id = url_unescape(response.effective_url).rsplit('=', 1)[1]

        # Using insert here to make sure that this clean up operation
        # is executed before the study one is done
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id))

        self.assertEqual(response.code, 200)

        obs = db.read_sample_plate(plate_id)
        # Remove the data as it is not deterministic and its correctness is
        # tested elsewhere
        del obs['created_on']
        exp = {'name': 'Test plate 1', 'plate_type_id': data['plate_type'],
               'email': 'test', 'notes': None, 'studies': [9999]}
        self.assertEqual(obs, exp)


class TestPMPlateNameCheckerHandler(TestHandlerBase):
    def test_get_not_authed(self):
        response = self.get('/pm_sample_plate/name_check?name=TestPlate')
        self.assertEqual(response.code, 200)
        self.assertTrue(
            response.effective_url.endswith(
                '?next=%2Fpm_sample_plate%2Fname_check%3Fname%3DTestPlate'))

    def test_get(self):
        self.mock_login_admin()
        response = self.get('/pm_sample_plate/name_check?name=TestPlate')
        self.assertEqual(response.code, 404)
        # Checl that the page is not empty
        self.assertEqual(json_decode(response.body), {'result': False})

        db.create_study(9999, 'LabAdmin test project', 'LTP', 'KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))
        plate_id = db.create_sample_plate(
            'TestPlate', db.get_plate_types()[0]['id'], 'test', [9999])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id))
        response = self.get('/pm_sample_plate/name_check?name=TestPlate')
        self.assertEqual(response.code, 200)
        # Checl that the page is not empty
        self.assertEqual(json_decode(response.body), {'result': True})


class TestPMPlateMapHandler(TestHandlerBase):
    def test_get_not_authed(self):
        db.create_study(9999, 'LabAdmin test project', 'LTP', 'KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))
        plate_id = db.create_sample_plate(
            'TestPlate', db.get_plate_types()[0]['id'], 'test', [9999])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id))

        response = self.get('/pm_plate_map?plate_id=%s' % plate_id)
        self.assertEqual(response.code, 200)
        exp = '?next=%2Fpm_plate_map%3Fplate_id%3D{}'.format(plate_id)
        self.assertTrue(response.effective_url.endswith(exp))

    def test_get(self):
        self.mock_login_admin()
        db.create_study(9999, 'LabAdmin test project', 'LTP', 'KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))
        plate_id = db.create_sample_plate(
            'TestPlate', db.get_plate_types()[0]['id'], 'test', [9999])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id))

        response = self.get('/pm_plate_map?plate_id=%s' % plate_id)
        self.assertEqual(response.code, 200)
        # Checl that the page is not empty
        self.assertIn("var pm = new PlateMap('plate-map-div', %d);" % plate_id,
                      response.body)


class TestPMSamplePlateHandler(TestHandlerBase):
    def test_get_not_authed(self):
        db.create_study(9999, 'LabAdmin test project', 'LTP', 'KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))
        plate_id = db.create_sample_plate(
            'TestPlate', db.get_plate_types()[0]['id'], 'test', [9999])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id))

        response = self.get('/pm_sample_plate?plate_id=%s' % plate_id)
        self.assertEqual(response.code, 200)
        exp = '?next=%2Fpm_sample_plate%3Fplate_id%3D{}'.format(plate_id)
        self.assertTrue(response.effective_url.endswith(exp))

    def test_get(self):
        self.mock_login_admin()
        db.create_study(9999, 'LabAdmin test project', 'LTP', 'KL9999')
        self._clean_up_funcs.append(partial(db.delete_study, 9999))
        plate_type = db.get_plate_types()[0]
        plate_id = db.create_sample_plate('TestPlate', plate_type['id'],
                                          'test', [9999])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id))

        response = self.get('/pm_sample_plate?plate_id=%s' % plate_id)
        self.assertEqual(response.code, 200)

        plate_info = db.read_sample_plate(plate_id)
        exp = {'created_on': plate_info['created_on'].isoformat(sep=' '),
               'email': 'test',
               'name': 'TestPlate',
               'notes': None,
               'plate_id': str(plate_id),
               'plate_type': {'cols': 12,
                              'name': '96-well',
                              'notes': 'Standard 96-well plate',
                              'plate_type_id': plate_info['plate_type_id'],
                              'rows': 8},
               'studies': [
                {'alias': 'LTP', 'jira_id': 'KL9999', 'study_id': 9999,
                 'title': 'LabAdmin test project',
                 'samples': {'all': [],
                             'plated': {}}}],
               'layout': []}
        self.assertEqual(json_decode(response.body), exp)

        # Add some samples to the study
        samples = ['9999.Sample1', '9999.Sample2', '9999.Sample3']
        db.set_study_samples(9999, samples)
        response = self.get('/pm_sample_plate?plate_id=%s' % plate_id)
        self.assertEqual(response.code, 200)
        exp['studies'][0]['samples']['all'] = samples
        self.assertEqual(json_decode(response.body), exp)

        # Plate some samples in some other plate
        plate_id_2 = db.create_sample_plate('TestPlate2', plate_type['id'],
                                            'test', [9999])
        self._clean_up_funcs.insert(
            0, partial(db.delete_sample_plate, plate_id_2))
        well = {'sample_id': None, 'name': None, 'notes': None}
        # This is crating a layout with empty wells
        layout = [[well] * plate_type['cols']] * plate_type['rows']
        layout[0][0] = {'sample_id': samples[0], 'name': None, 'notes': None}
        db.write_sample_plate_layout(plate_id_2, layout)
        response = self.get('/pm_sample_plate?plate_id=%s' % plate_id)
        self.assertEqual(response.code, 200)
        exp['studies'][0]['samples']['plated'][str(plate_id_2)] = [samples[0]]
        self.assertEqual(json_decode(response.body), exp)

        # Plate some samples in the current plate
        db.write_sample_plate_layout(plate_id, layout)
        response = self.get('/pm_sample_plate?plate_id=%s' % plate_id)
        self.assertEqual(response.code, 200)
        exp['layout'] = layout
        self.assertEqual(json_decode(response.body), exp)

        # Check response when plate doesn't exist
        response = self.get('/pm_sample_plate?plate_id=%s' % (plate_id_2 + 1))
        self.assertEqual(response.code, 404)
        exp = {'message': 'Sample plate ID %d does not exist.'
                          % (plate_id_2 + 1)}
        self.assertEqual(json_decode(response.body), exp)


if __name__ == '__main__':
    main()

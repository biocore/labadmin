from unittest import main

from knimin.tests.tornado_test_base import TestHandlerBase
from knimin import db
import datetime


class TestPMPlateListHandler(TestHandlerBase):
    def test_get_not_authed(self):
        response = self.get(
            '/pm_plate_list/')
        self.assertEqual(response.code, 200)
        self.assertTrue(
            response.effective_url.endswith('?next=%2Fpm_plate_list%2F'))

    def test_get(self):
        email = db.get_emails()[0]
        plate_type = db.get_plate_types()[0]
        created_on = datetime.datetime.combine(datetime.date.today(),
                                               datetime.time.min)
        sid = db.create_study(title='test_study')
        total = plate_type['cols']*plate_type['rows']
        samples = [{'id': 'test_sample_' + str(x), 'study_ids': [sid]}
                   for x in range(total)]
        db.create_samples(samples)
        spinfo = {'name': 'test_plate',
                  'plate_type_id': plate_type['id'],
                  'email': email,
                  'created_on': created_on,
                  'notes': 'A test plate'}
        for n in (0, 1, int(total*0.333)+1, int(total*0.667)+1, total):
            spid = db.create_sample_plate(**spinfo)
            splayout = []
            (col, row) = (1, 1)
            for x in range(n):
                splayout.append({'sample_id': 'test_sample_' + str(x),
                                 'col': col, 'row': row})
                if row == plate_type['rows']:
                    col += 1
                    row = 1
                else:
                    row += 1
            db.write_sample_plate_layout(spid, splayout)
            self.mock_login_admin()
            response = self.get('/pm_plate_list/')
            self.assertEqual(response.code, 200)
            # Test the page title
            self.assertIn('Sample Plate List', response.body)
            # Test the newly created sample plate
            p1 = db.get_sample_plate_list()[-1]
            r = p1['fill'][1]
            battery = ''
            if r == 1.0:
                battery = 'full'
            elif r >= 0.667:
                battery = 'three-quarters'
            elif r > 0.333:
                battery = 'half'
            elif r > 0.0:
                battery = 'quarter'
            else:
                battery = 'empty'
            exp = ('<tr>\n'
                   '<td>' + str(p1['id']) + '</td>\n'
                   '<td><a href="/pm_plate_map/?target=sample&id=' +
                   str(p1['id']) + '">' + p1['name'] + '</a></td>\n'
                   '<td title="' + str(p1['type'][1]) + '">' + p1['type'][0] +
                   '</td>\n'
                   '<td>' + str(p1['fill'][0]) + '\n'
                   '<span style="font-size:80%">\n'
                   '\n'
                   '\n'
                   '<i class="fa fa-battery-' + battery + '"></i>\n'
                   '\n'
                   '</span></td>\n'
                   '<td title="' + p1['study'][3] + '">' +
                   str(p1['study'][1]) + '</td>\n'
                   '<td>' + (p1['person'] or '-') + '</td>\n'
                   '<td>' + (p1['date'] or '-') + '</td>\n')
            self.assertIn(exp, response.body)
            db.delete_sample_plate(spid)
        db.delete_samples(['test_sample_' + str(x) for x in range(total)])
        db.delete_study(sid)

if __name__ == '__main__':
    main()

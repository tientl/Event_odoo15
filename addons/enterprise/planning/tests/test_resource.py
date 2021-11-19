# Part of Odoo. See LICENSE file for full copyright and licensing details
from datetime import datetime
from freezegun import freeze_time

from odoo.tests import tagged

from .common import TestCommonPlanning


@tagged('post_install', '-at_install')
class TestPlanningResource(TestCommonPlanning):
    @classmethod
    def setUpClass(cls):
        super(TestPlanningResource, cls).setUpClass()
        cls.setUpEmployees()

        cls.res_willywaller = cls.env['resource.resource'].create({
            'name': 'Willy Waller 2006',
            'resource_type': 'material'
        })

    def test_resource_conflicts(self):
        slot_a = self.env['planning.slot'].create({
            'resource_id': self.res_willywaller.id,
            'allocated_hours': 4,
            'start_datetime': datetime(2019, 6, 6, 8, 0, 0),
            'end_datetime': datetime(2019, 6, 6, 12, 0, 0)
        })
        self.assertEqual(slot_a.overlap_slot_count, 0)

        slot_b = self.env['planning.slot'].create({
            'resource_id': self.res_willywaller.id,
            'allocated_hours': 4,
            'start_datetime': datetime(2019, 6, 6, 13, 0, 0),
            'end_datetime': datetime(2019, 6, 6, 17, 0, 0)
        })
        self.assertEqual(slot_a.overlap_slot_count, 0)
        self.assertEqual(slot_b.overlap_slot_count, 0)

        slot_b.start_datetime = datetime(2019, 6, 6, 11, 0, 0)
        self.assertEqual(slot_b.overlap_slot_count, 1, 'Should have a conflict')
        self.assertIn(slot_a.id, slot_b.conflicting_slot_ids.ids, 'slot_a should conflict with slot_b')

        slot_a.resource_id = self.resource_bert
        self.assertEqual(slot_a.overlap_slot_count, 0)

    def test_resource_publication_warning(self):
        slot_a = self.env['planning.slot'].create({
            'resource_id': self.res_willywaller.id,
            'start_datetime': datetime(2019, 6, 6, 8, 0, 0),
            'end_datetime': datetime(2019, 6, 6, 12, 0, 0)
        })
        self.assertFalse(slot_a.publication_warning)
        self.assertEqual(slot_a.state, 'draft')

        slot_a.action_publish()
        self.assertFalse(slot_a.publication_warning)
        self.assertEqual(slot_a.state, 'published')

        slot_a.resource_id = self.resource_bert
        self.assertTrue(slot_a.publication_warning)

    @freeze_time('2021-07-15')
    def test_resource_default_hours(self):
        full_calendar = self.env['resource.calendar'].create({
            'name': 'Classic 40h/week',
            'tz': 'UTC',
            'hours_per_day': 8.0,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'})
            ]
        })
        self.resource_bert.calendar_id = full_calendar
        self.resource_bert.tz = 'UTC'

        half_calendar = self.env['resource.calendar'].create({
            'name': 'Classic 20h/week',
            'tz': 'UTC',
            'hours_per_day': 4.0,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
            ]
        })
        self.res_willywaller.calendar_id = half_calendar
        self.res_willywaller.tz = 'UTC'

        self.env.user.tz = 'UTC'

        bert_data = self.env['planning.slot'].with_context(default_resource_id=self.resource_bert.id).default_get(['resource_id', 'start_datetime', 'end_datetime'])
        self.assertDictEqual({
            'resource_id': self.resource_bert.id,
            'start_datetime': datetime(2021, 7, 15, 8, 0, 0),
            'end_datetime': datetime(2021, 7, 15, 17, 0, 0),
        }, bert_data, 'The dault start/date should adapt to the resource calendar')

        willy_data = self.env['planning.slot'].with_context(default_resource_id=self.res_willywaller.id).default_get(['resource_id', 'start_datetime', 'end_datetime'])
        self.assertDictEqual({
            'resource_id': self.res_willywaller.id,
            'start_datetime': datetime(2021, 7, 15, 8, 0, 0),
            'end_datetime': datetime(2021, 7, 15, 12, 0, 0),
        }, willy_data, 'The dault start/date should adapt to the resource calendar')

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details
from datetime import datetime
import pytz

from odoo.addons.resource.models.resource import Intervals
from odoo.tests.common import Form
from .common import TestCommonPlanning


class TestPlanningHr(TestCommonPlanning):
    @classmethod
    def setUpClass(cls):
        super(TestPlanningHr, cls).setUpClass()
        cls.setUpEmployees()
        calendar_joseph = cls.env['resource.calendar'].create({
            'name': 'Calendar 1',
            'tz': 'UTC',
            'hours_per_day': 8.0,
            'attendance_ids': [
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 9, 'hour_to': 13, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 14, 'hour_to': 18, 'day_period': 'afternoon'}),
            ]
        })
        cls.employee_joseph.resource_calendar_id = calendar_joseph

    def test_change_default_planning_role(self):
        self.assertFalse(self.employee_joseph.default_planning_role_id, "Joseph should have no default planning role")
        self.assertFalse(self.employee_joseph.planning_role_ids, "Joseph should have no planning roles")

        role_a = self.env['planning.role'].create({
            'name': 'role a'
        })
        role_b = self.env['planning.role'].create({
            'name': 'role b'
        })

        self.employee_joseph.default_planning_role_id = role_a

        self.assertEqual(self.employee_joseph.default_planning_role_id, role_a, "Joseph should have role a as default role")
        self.assertTrue(role_a in self.employee_joseph.planning_role_ids, "role a should be added to his planning roles")

        self.employee_joseph.write({'planning_role_ids': [(5, 0, 0)]})
        self.assertTrue(role_a in self.employee_joseph.planning_role_ids, "role a should be automatically added to his planning roles")

        self.employee_joseph.default_planning_role_id = role_b
        self.assertTrue(role_a in self.employee_joseph.planning_role_ids, "role a should still be in planning roles")
        self.assertTrue(role_b in self.employee_joseph.planning_role_ids, "role b should be added to planning roles")

    def test_hr_employee_view_planning(self):
        self.env['planning.slot'].create({
            'resource_id': self.resource_bert.id,
            'start_datetime': datetime(2021, 6, 4, 8, 0),
            'end_datetime': datetime(2021, 6, 5, 17, 0),
        }).copy()
        action = self.employee_bert.action_view_planning()
        # just returns action
        slots = self.env['planning.slot'].search(action['domain'])
        self.assertEqual(action['res_model'], 'planning.slot')
        self.assertEqual(len(slots), 2, 'Bert has 2 planning slots')
        self.assertEqual(action['context']['default_resource_id'], self.resource_bert.id)

    def test_employee_contract_validity_per_period(self):
        start = datetime(2015, 11, 8, 00, 00, 00, tzinfo=pytz.UTC)
        end = datetime(2015, 11, 21, 23, 59, 59, tzinfo=pytz.UTC)
        calendars_validity_within_period = self.employee_joseph.resource_id._get_calendars_validity_within_period(start, end, default_company=self.employee_joseph.company_id)

        self.assertEqual(len(calendars_validity_within_period[self.employee_joseph.resource_id.id]), 1, "There should exist 1 calendar within the period")
        interval_calendar_joseph = Intervals([(
            start,
            end,
            self.env['resource.calendar.attendance']
        )])
        computed_interval = calendars_validity_within_period[self.employee_joseph.resource_id.id][self.employee_joseph.resource_calendar_id]
        self.assertFalse(computed_interval - interval_calendar_joseph, "The interval of validity for the 40h calendar must be from 2015-11-16 to 2015-11-21, not more")
        self.assertFalse(interval_calendar_joseph - computed_interval, "The interval of validity for the 40h calendar must be from 2015-11-16 to 2015-11-21, not less")

    def test_employee_work_intervals(self):
        start = datetime(2015, 11, 8, 00, 00, 00, tzinfo=pytz.UTC)
        end = datetime(2015, 11, 21, 23, 59, 59, tzinfo=pytz.UTC)
        work_intervals = self.employee_joseph.resource_id._get_work_intervals_batch(start, end)
        sum_work_intervals = sum(
            (stop - start).total_seconds() / 3600
            for start, stop, _resource in work_intervals[self.employee_joseph.resource_id.id]
        )
        self.assertEqual(16, sum_work_intervals, "Sum of the work intervals for the employee Joseph should be 8h+8h = 16h")

    def test_employee_work_planning_hours_info(self):
        joseph_resource_id = self.employee_joseph.resource_id
        self.env['planning.slot'].create([{
            'resource_id': joseph_resource_id.id,
            'start_datetime': datetime(2015, 11, 8, 8, 0),
            'end_datetime': datetime(2015, 11, 14, 17, 0),
            # allocated_hours will be : 8h (see calendar)
        }, {
            'resource_id': joseph_resource_id.id,
            'start_datetime': datetime(2015, 11, 16, 8, 0),
            'end_datetime': datetime(2015, 11, 16, 17, 0),
            # allocated_hours will be : 9h
        }, {
            'resource_id': joseph_resource_id.id,
            'start_datetime': datetime(2015, 11, 17, 8, 0),
            'end_datetime': datetime(2015, 11, 17, 17, 0),
            # allocated_hours will be : 9h
        }, {
            'resource_id': joseph_resource_id.id,
            'start_datetime': datetime(2015, 11, 18, 8, 0),
            'end_datetime': datetime(2015, 11, 18, 17, 0),
            # allocated_hours will be : 9h
        }, {
            'resource_id': joseph_resource_id.id,
            'start_datetime': datetime(2015, 11, 23, 8, 0),
            'end_datetime': datetime(2015, 11, 27, 17, 0),
            'allocated_percentage': 50.0,
            # allocated_hours will be : 4h (see calendar)
        }])

        planning_hours_info = joseph_resource_id.get_planning_hours_info('2015-11-08 00:00:00', '2015-11-28 23:59:59')
        self.assertEqual(24, planning_hours_info[joseph_resource_id.id]['work_hours'], "Work hours for the employee Jules should be 8h+8h+8h = 24h")
        self.assertEqual(39, planning_hours_info[joseph_resource_id.id]['planned_hours'], "Planned hours for the employee Jules should be 3*9h+8h+4h = 39h")

        planning_hours_info = joseph_resource_id.get_planning_hours_info('2015-11-12 00:00:00', '2015-11-12 23:59:59')
        self.assertEqual(8, planning_hours_info[joseph_resource_id.id]['work_hours'],
                         "Work hours for the employee Jules should be 8h as its a Thursday.")
        self.assertEqual(8, planning_hours_info[joseph_resource_id.id]['planned_hours'],
                         "Planned hours for the employee Jules should be 8h as its a Thursday and hours are computed on a forecast slot.")

        planning_hours_info = joseph_resource_id.get_planning_hours_info('2015-11-26 00:00:00', '2015-11-26 23:59:59')
        self.assertEqual(8, planning_hours_info[joseph_resource_id.id]['work_hours'],
                         "Work hours for the employee Jules should be 8h as its a Thursday.")
        self.assertEqual(4, planning_hours_info[joseph_resource_id.id]['planned_hours'],
                         "Planned hours for the employee Jules should be 4h as its a Thursday and hours are computed on a forecast slot (allocated_percentage = 50).")

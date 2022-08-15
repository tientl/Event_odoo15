# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details
from datetime import datetime
import pytz

from odoo.tests.common import Form, new_test_user
from .common import TestCommonPlanning


class TestPlanningForm(TestCommonPlanning):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.resource_calendar_38_hours_per_week = cls.env['resource.calendar'].create([{
            'name': "Test Calendar : 38 Hours/Week",
            'hours_per_day': 7.6,
            'tz': 'Europe/Brussels',
            'two_weeks_calendar': False,
            'attendance_ids': [(5, 0, 0)] + [(0, 0, {
                'name': "Attendance",
                'dayofweek': dayofweek,
                'hour_from': hour_from,
                'hour_to': hour_to,
                'day_period': day_period,
            }) for dayofweek, hour_from, hour_to, day_period in [
                ("0", 8.0, 12.0, "morning"),
                ("0", 13.0, 16.6, "afternoon"),
                ("1", 8.0, 12.0, "morning"),
                ("1", 13.0, 16.6, "afternoon"),
                ("2", 8.0, 12.0, "morning"),
                ("2", 13.0, 16.6, "afternoon"),
                ("3", 8.0, 12.0, "morning"),
                ("3", 13.0, 16.6, "afternoon"),
                ("4", 8.0, 12.0, "morning"),
                ("4", 13.0, 16.6, "afternoon"),
            ]],
        }])

        cls.setUpEmployees()
        cls.employee_janice.resource_calendar_id = cls.resource_calendar_38_hours_per_week.id

        cls.test_user = new_test_user(cls.env, login='testuser', groups='planning.group_planning_manager', tz='Europe/Brussels', resource_calendar_id='resource_calendar_id')

    def test_planning_no_employee_no_company(self):
        """ test multi day slot without calendar (no employee nor company) """
        with Form(self.env['planning.slot']) as slot:
            start, end = datetime(2020, 1, 1, 8, 0), datetime(2020, 1, 11, 18, 0)
            slot.start_datetime = start
            slot.end_datetime = end
            slot.resource_id = self.env['resource.resource']
            slot.company_id = self.env['res.company']
            slot.allocated_percentage = 100
            self.assertEqual(slot.allocated_hours, (end - start).total_seconds() / (60 * 60))

    def planning_form(self, timezone, start, end, expected_start, expected_end):
        self.resource_calendar_38_hours_per_week.tz = timezone
        self.employee_janice.tz = timezone
        context = dict(
            default_resource_id=self.employee_janice.resource_id.id,
            default_start_datetime=start,
            default_end_datetime=end,
        )
        with Form(self.env['planning.slot'].with_user(self.test_user).with_context(context)) as slot:
            tz = pytz.timezone(self.employee_janice.resource_calendar_id.tz)
            start_decimal_time = slot.start_datetime.astimezone(tz).hour + slot.start_datetime.astimezone(tz).minute / 60
            self.assertEqual(start_decimal_time, expected_start,
                             "The planning slot doesn't start at the same time than the employee's resource calendar")
            end_decimal_time = slot.end_datetime.astimezone(tz).hour + slot.end_datetime.astimezone(tz).minute / 60
            self.assertEqual(end_decimal_time, expected_end,
                             "The planning slot doesn't end at the same time than the employee's resource calendar")

    def test_planning_employee_different_timezone(self):
        # When a slot is selected on the frontend, the start and end datetime are from 00:00:00 to 23:59:59 in the user timezone
        start, end = datetime(2020, 1, 1, 23, 0, 0), datetime(2020, 1, 2, 22, 59, 59)
        self.planning_form('Asia/Calcutta', start, end, 8, 16.6)
        self.planning_form('America/Montreal', start, end, 8, 16.6)

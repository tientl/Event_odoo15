# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo.fields import Command
from odoo.addons.project_enterprise_hr.tests.auto_shift_dates_hr_common import AutoShiftDatesHRCommon
from odoo.addons.project_enterprise.tests.auto_shift_dates_common import fake_now
from odoo.tests.common import tagged


@freeze_time(fake_now)
@tagged('-at_install', 'post_install', 'auto_shift_dates')
class TestTaskDependencies(AutoShiftDatesHRCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contract_1 = cls.env['hr.contract'].create({
            'date_start': cls.task_1_planned_date_begin.date() - relativedelta(days=1),
            'date_end': cls.task_1_planned_date_begin.date() + relativedelta(days=1),
            'name': 'First CDD Contract for Armande ProjectUser',
            'resource_calendar_id': cls.calendar_morning.id,
            'wage': 5000.0,
            'employee_id': cls.armande_employee.id,
            'state': 'close',
        })
        cls.contract_2 = cls.env['hr.contract'].create({
            'date_start': cls.task_1_planned_date_begin.date() + relativedelta(days=2),
            'name': 'CDI Contract for Armande ProjectUser',
            'resource_calendar_id': cls.calendar_afternoon.id,
            'wage': 5000.0,
            'employee_id': cls.armande_employee.id,
            'state': 'close',
        })
        cls.armande_user_calendar = cls.env['resource.calendar'].create({
            'name': 'Wednesday calendar',
            'attendance_ids': [
                Command.create({'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                Command.create({'name': 'Wednesday Evening', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            ],
            'tz': 'UTC',
        })
        cls.armande_employee.write({
            'resource_calendar_id': cls.armande_user_calendar.id,
        })

    def test_auto_shift_employee_contract_integration(self):
        self.task_4.depend_on_ids = [Command.clear()]
        new_task_3_begin_date = self.task_1_planned_date_end - timedelta(hours=2)  # 2021 06 24 10:00
        self.task_3.write({
            'planned_date_begin': new_task_3_begin_date,
            'planned_date_end': new_task_3_begin_date + (self.task_3_planned_date_end - self.task_3_planned_date_begin),
        })
        failed_message = "The auto shift date feature should take the employee's calendar into account."
        self.assertEqual(self.task_1.planned_date_begin,
                         new_task_3_begin_date - relativedelta(days=1, hour=11), failed_message)
        new_task_3_begin_date = self.task_1.planned_date_begin - relativedelta(days=2)  # 2021 06 21 11:00
        self.task_3.write({
            'planned_date_begin': new_task_3_begin_date,
            'planned_date_end': new_task_3_begin_date + (self.task_3_planned_date_end - self.task_3_planned_date_begin),
        })
        failed_message = "The auto shift date feature should take the employee's calendar when no contract cover the period."
        self.assertEqual(self.task_1.planned_date_begin,
                         new_task_3_begin_date + relativedelta(day=16, hour=14), failed_message)
        self.armande_employee.write({
            'resource_calendar_id': False,
        })
        new_task_3_begin_date = self.task_1.planned_date_begin - relativedelta(days=2)  # 2021 06 14 14:00
        self.task_3.write({
            'planned_date_begin': new_task_3_begin_date,
            'planned_date_end': new_task_3_begin_date + (self.task_3_planned_date_end - self.task_3_planned_date_begin),
        })
        failed_message = "The auto shift date feature should take the company's calendar when no contract cover the period and no calendar is set on the employee."
        self.assertEqual(self.task_1.planned_date_begin,
                         new_task_3_begin_date + relativedelta(hour=10), failed_message)
        self.armande_employee.write({
            'resource_calendar_id': self.armande_user_calendar.id,
        })
        new_task_1_begin_date = self.contract_2.date_start + relativedelta(days=1, hour=14)  # 2021 06 27 14:00
        self.task_1.write({
            'planned_date_begin': new_task_1_begin_date,
            'planned_date_end': new_task_1_begin_date + (self.task_1_planned_date_end - self.task_1_planned_date_begin),
        })
        self.assertEqual(self.task_3.planned_date_begin,
                         new_task_1_begin_date + relativedelta(days=1, hour=13), failed_message)

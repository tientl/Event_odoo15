# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo.tests.common import tagged
from odoo.addons.project_enterprise.tests.auto_shift_dates_common import fake_now
from .auto_shift_dates_hr_common import AutoShiftDatesHRCommon
from odoo.fields import Command


@freeze_time(fake_now)
@tagged('-at_install', 'post_install', 'auto_shift_dates')
class TestTaskDependencies(AutoShiftDatesHRCommon):

    def test_auto_shift_employee_integration(self):
        self.task_4.depend_on_ids = [Command.clear()]
        new_task_3_begin_date = self.task_1_planned_date_end - timedelta(hours=2)  # 2021 06 24 10:00
        self.task_3.write({
            'planned_date_begin': new_task_3_begin_date,
            'planned_date_end': new_task_3_begin_date + (self.task_3_planned_date_end - self.task_3_planned_date_begin),
        })
        failed_message = "The auto shift date feature should take the employee's calendar into account."
        self.assertEqual(self.task_1.planned_date_begin,
                         new_task_3_begin_date - relativedelta(days=1, hour=14), failed_message)
        self.armande_employee.write({
            'resource_calendar_id': self.calendar_morning.id,
        })
        new_task_3_begin_date = self.task_1.planned_date_begin + relativedelta(hour=10)  # 2021 06 23 10:00
        self.task_3.write({
            'planned_date_begin': new_task_3_begin_date,
            'planned_date_end': new_task_3_begin_date + (self.task_3_planned_date_end - self.task_3_planned_date_begin),
        })
        self.assertEqual(self.task_1.planned_date_begin,
                         new_task_3_begin_date + relativedelta(days=-1, hour=11), failed_message)
        failed_message = "The auto shift date feature should take the company's calendar into account before employee create_date."
        new_task_3_begin_date = self.armande_employee_create_date - relativedelta(days=3, hour=9)
        self.task_3.write({
            'planned_date_begin': new_task_3_begin_date,
            'planned_date_end': new_task_3_begin_date + (self.task_3_planned_date_end - self.task_3_planned_date_begin),
        })
        self.assertEqual(self.task_1.planned_date_begin,
                         new_task_3_begin_date - relativedelta(days=1, hour=15), failed_message)
        new_task_1_begin_date = self.armande_departure_date + relativedelta(days=1, hour=11)
        self.task_1.write({
            'planned_date_begin': new_task_1_begin_date,
            'planned_date_end': new_task_1_begin_date + (self.task_1_planned_date_end - self.task_1_planned_date_begin),
        })
        self.assertEqual(self.task_3.planned_date_begin,
                         new_task_1_begin_date + relativedelta(hour=14), failed_message)
        failed_message = "The auto shift date feature should work for tasks landing on the edge of employee create_date or on the edge of departure_date."
        self.armande_employee.write({
            'resource_calendar_id': self.calendar_afternoon.id,
        })
        new_task_3_begin_date = self.armande_employee_create_date + relativedelta(hour=13)
        self.task_3.write({
            'planned_date_begin': new_task_3_begin_date,
            'planned_date_end': new_task_3_begin_date + (self.task_3_planned_date_end - self.task_3_planned_date_begin),
        })
        self.assertEqual(self.task_1.planned_date_begin,
                         new_task_3_begin_date + relativedelta(hour=9), failed_message)
        new_task_1_begin_date = self.armande_departure_date - relativedelta(days=1, hour=16)
        self.task_1.write({
            'planned_date_begin': new_task_1_begin_date,
            'planned_date_end': new_task_1_begin_date + (self.task_1_planned_date_end - self.task_1_planned_date_begin),
        })
        self.assertEqual(self.task_3.planned_date_begin,
                         new_task_1_begin_date + relativedelta(days=1, hour=13), failed_message)
        failed_message = "The auto shift date feature should work for tasks landing on the edge of employee create_date or on the edge of departure_date, even when falling in the middle of the planned_hours."
        new_task_3_begin_date = self.armande_employee_create_date + relativedelta(hour=15)
        self.task_3.write({
            'planned_date_begin': new_task_3_begin_date,
            'planned_date_end': new_task_3_begin_date + (self.task_3_planned_date_end - self.task_3_planned_date_begin),
        })
        self.assertEqual(self.task_1.planned_date_begin,
                         new_task_3_begin_date + relativedelta(hour=11), failed_message)
        self.armande_employee.write({
            'resource_calendar_id': self.calendar_morning.id,
        })
        new_task_1_begin_date = self.armande_departure_date + relativedelta(hour=8)
        self.task_1.write({
            'planned_date_begin': new_task_1_begin_date,
            'planned_date_end': new_task_1_begin_date + (self.task_1_planned_date_end - self.task_1_planned_date_begin),
        })
        self.assertEqual(self.task_3.planned_date_end,
                         new_task_1_begin_date + relativedelta(days=1, hour=9), failed_message)

    def test_auto_shift_multiple_assignees(self):
        """
        Tests that the auto shift fallbacks to the company calendar in the case that
        there are multiple assignees to the task.
        """
        self.task_1.user_ids += self.user_projectmanager
        self.task_1.write(self.task_1_date_auto_shift_trigger)
        failed_message = "The auto shift date feature should move forward a dependent tasks."
        self.assertTrue(self.task_1.planned_date_end <= self.task_3.planned_date_begin, failed_message)

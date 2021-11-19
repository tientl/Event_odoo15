# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.fields import Command
from odoo.addons.project.tests.test_project_base import TestProjectCommon

# As the write of the new planned_dates is only made when planned_date_start is in the future, we need to cheat during the tests
fake_now = datetime(2021, 4, 1)


class AutoShiftDatesCommon(TestProjectCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, date_auto_shift=True, mail_create_nolog=True))
        cls.Settings = cls.env["res.config.settings"]
        cls.project_pigs.write({
            'allow_task_dependencies': True,
        })
        cls.task_1 = cls.task_1.with_context(date_auto_shift=True)
        cls.task_1_planned_date_begin = datetime(2021, 6, 24, 9, 0, 0)
        cls.task_1_planned_date_end = datetime(2021, 6, 24, 12, 0, 0)
        cls.task_1.write({
            'planned_date_begin': cls.task_1_planned_date_begin,
            'planned_date_end': cls.task_1_planned_date_end,
            'planned_hours': 3.0,
        })
        cls.task_3_planned_date_begin = datetime(2021, 6, 24, 13, 0, 0)
        cls.task_3_planned_date_end = datetime(2021, 6, 24, 15, 0, 0)
        cls.task_3 = cls.env['project.task'].create({
            'name': 'Pigs UserTask 2',
            'user_ids': cls.user_projectuser,
            'project_id': cls.project_pigs.id,
            'depend_on_ids': [Command.link(cls.task_1.id)],
            'planned_date_begin': cls.task_3_planned_date_begin,
            'planned_date_end': cls.task_3_planned_date_end,
            'planned_hours': 2.0,
        })
        cls.task_4_planned_date_begin = datetime(2021, 6, 30, 15, 0, 0)
        cls.task_4_planned_date_end = datetime(2021, 6, 30, 17, 0, 0)
        cls.task_4 = cls.env['project.task'].create({
            'name': 'Pigs UserTask 3',
            'user_ids': cls.user_projectuser,
            'project_id': cls.project_pigs.id,
            'depend_on_ids': [Command.link(cls.task_3.id)],
            'planned_date_begin': cls.task_4_planned_date_begin,
            'planned_date_end': cls.task_4_planned_date_end,
            'planned_hours': 2.0,
        })
        cls.task_5_planned_date_begin = datetime(2021, 8, 2, 8, 0, 0)
        cls.task_5_planned_date_end = datetime(2021, 8, 3, 17, 0, 0)
        cls.task_5 = cls.env['project.task'].create({
            'name': 'Pigs UserTask 4',
            'user_ids': cls.user_projectuser,
            'project_id': cls.project_pigs.id,
            'depend_on_ids': [Command.link(cls.task_4.id)],
            'planned_date_begin': cls.task_5_planned_date_begin,
            'planned_date_end': cls.task_5_planned_date_end,
            'planned_hours': 16.0,
        })
        cls.task_6_planned_date_begin = datetime(2021, 8, 4, 8, 0, 0)
        cls.task_6_planned_date_end = datetime(2021, 8, 4, 17, 0, 0)
        cls.task_6 = cls.env['project.task'].create({
            'name': 'Pigs UserTask 5',
            'user_ids': cls.user_projectuser,
            'project_id': cls.project_pigs.id,
            'depend_on_ids': [Command.link(cls.task_5.id)],
            'planned_date_begin': cls.task_6_planned_date_begin,
            'planned_date_end': cls.task_6_planned_date_end,
            'planned_hours': 8.0,
        })
        overlapping_delta = cls.task_3_planned_date_begin - cls.task_1_planned_date_end + timedelta(hours=1)
        cls.task_1_date_auto_shift_trigger = {
            'planned_date_begin': cls.task_1.planned_date_begin + overlapping_delta,
            'planned_date_end': cls.task_1.planned_date_end + overlapping_delta,
        }
        cls.task_3_date_auto_shift_trigger = {
            'planned_date_begin': cls.task_3.planned_date_begin - overlapping_delta,
            'planned_date_end': cls.task_3.planned_date_end - overlapping_delta,
        }
        cls.task_1_no_date_auto_shift_trigger = {
            'planned_date_begin': cls.task_1.planned_date_begin + overlapping_delta - timedelta(hours=1),
            'planned_date_end': cls.task_1.planned_date_end + overlapping_delta - timedelta(hours=1),
        }
        cls.calendar_40h = cls.env['resource.calendar'].create({
            'name': '40h calendar',
            'attendance_ids': [
                Command.create({'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                Command.create({'name': 'Monday Evening', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                Command.create({'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                Command.create({'name': 'Tuesday Evening', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                Command.create({'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                Command.create({'name': 'Wednesday Evening', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                Command.create({'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                Command.create({'name': 'Thursday Evening', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                Command.create({'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                Command.create({'name': 'Friday Evening', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            ],
            'tz': 'UTC',
        })
        cls.annual_holiday = cls.env['resource.calendar.leaves'].create({
            'name': 'Building leave',
            'resource_id': False,
            'calendar_id': cls.calendar_40h.id,
            'date_from': datetime(2021, 7, 1, 0, 0, 0),
            'date_to': datetime(2021, 7, 31, 23, 59, 59),
        })
        cls.env.company.write({
            'resource_calendar_id': cls.calendar_40h.id,
        })
        users = cls.user_projectuser | cls.user_projectmanager
        users.write({
            'resource_calendar_id': cls.calendar_40h.id,
        })

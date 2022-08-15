# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details
from datetime import datetime, timedelta

from odoo import tools
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import TestCommonForecast


@tagged('-at_install', 'post_install')
class TestForecastCreationAndEditing(TestCommonForecast):

    @classmethod
    def setUpClass(cls):
        super(TestForecastCreationAndEditing, cls).setUpClass()

        cls.setUpEmployees()
        cls.setUpProjects()

    def test_creating_a_planning_shift_allocated_hours_are_correct(self):
        values = {
            'project_id': self.project_opera.id,
            'employee_id': self.employee_bert.id,
            'allocated_hours': 8,
            'start_datetime': datetime(2019, 6, 6, 8, 0, 0),  # 6/6/2019 is a tuesday, so a working day
            'end_datetime': datetime(2019, 6, 6, 17, 0, 0),
            'allocated_percentage': 100,
        }

        # planning_shift on one day (planning mode)
        planning_shift = self.env['planning.slot'].create(values)
        planning_shift._compute_allocated_hours()
        self.assertEqual(planning_shift.allocated_hours, 9.0, 'resource hours should be a full workday')

        planning_shift.write({'allocated_percentage': 50})
        self.assertEqual(planning_shift.allocated_hours, 4.5, 'resource hours should be a half duration')

        # planning_shift on non working days
        values = {
            'allocated_percentage': 100,
            'start_datetime': datetime(2019, 6, 2, 8, 0, 0),  # sunday morning
            'end_datetime': datetime(2019, 6, 2, 17, 0, 0)  # sunday evening, same sunday, so employee is not working
        }
        planning_shift.write(values)

        self.assertEqual(planning_shift.allocated_hours, 9, 'resource hours should be a full day working hours')

        # planning_shift on multiple days (forecast mode)
        values = {
            'allocated_percentage': 100,   # full week
            'start_datetime': datetime(2019, 6, 3, 0, 0, 0),  # 6/3/2019 is a monday
            'end_datetime': datetime(2019, 6, 8, 23, 59, 0)  # 6/8/2019 is a sunday, so we have a full week
        }
        planning_shift.write(values)

        self.assertEqual(planning_shift.allocated_hours, 40, 'resource hours should be a full week\'s available hours')

    def test_task_in_project(self):
        values = {
            'project_id': self.project_opera.id,
            'task_id': self.task_horizon_dawn.id,  # oops, task_horizon_dawn is into another project
            'employee_id': self.employee_bert.id,
            'allocated_hours': 8,
            'start_datetime': datetime(2019, 6, 2, 8, 0, 0),
            'end_datetime': datetime(2019, 6, 2, 17, 0, 0)
        }
        slot = self.env['planning.slot'].create(values)
        self.assertEqual(slot.project_id, self.project_horizon, 'If we put a task when creation, we take the project of this task for this new slot.')

        # Test when we change the project of the task linked to the shift.
        self.task_horizon_dawn.write({'project_id': self.project_opera.id})
        self.assertEqual(slot.project_id, self.project_opera, 'If the project changed in the task linked to this shift, the new project of this task must be the project linked to this shift.')

        # Add a shift template with a project linked to this shift and see if the project remains the one in project.
        shift_template = self.env['planning.slot.template'].create({
            'project_id': self.project_opera.id,
            'task_id': self.task_opera_place_new_chairs.id,
            'duration': 8,
        })
        slot.write({'template_id': shift_template.id})
        self.assertEqual(slot.task_id, shift_template.task_id, 'the task should be the same of its template.')
        self.assertEqual(slot.task_id, self.task_opera_place_new_chairs, 'The task of the slot should be the one in the template.')
        self.assertEqual(slot.project_id, shift_template.project_id, 'the project should be the same of its template.')
        self.assertEqual(slot.project_id, self.project_opera, 'The project of the slot should be the one in the template.')

        # Change the project of this task to see if the shift has the new project.
        self.task_opera_place_new_chairs.write({'project_id': self.project_horizon.id})
        self.assertEqual(slot.project_id, self.project_horizon, 'The project of the slot should be the new one of the task.')

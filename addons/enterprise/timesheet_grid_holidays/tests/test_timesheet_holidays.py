# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import SUPERUSER_ID
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.addons.hr_timesheet.tests.test_timesheet import TestCommonTimesheet


class TestTimesheetGridHolidays(TestCommonTimesheet):

    def test_overtime_calcution_timesheet_holiday_flow(self):
        """ Employee's leave is not calculated as overtime hours when employee is on time off."""

        HrEmployee = self.env['hr.employee']
        employees_grid_data = [{'employee_id': self.empl_employee.id}]
        start_date = '2021-10-04'
        end_date = '2021-10-09'
        result = HrEmployee.get_timesheet_and_working_hours_for_employees(employees_grid_data, start_date, end_date)
        self.assertEqual(result[self.empl_employee.id]['units_to_work'], 40, "Employee weekly working hours should be 40.")
        self.assertEqual(result[self.empl_employee.id].get('worked_hours'), None, "Employee's working hours should be None.")

        leave_start_datetime = datetime(2021, 10, 5, 7, 0, 0, 0)  # this is Tuesday
        leave_end_datetime = leave_start_datetime + relativedelta(days=1)
        # all company have those internal project/task (created by default)
        internal_project = self.env.company.internal_project_id
        internal_task_leaves = self.env.company.leave_timesheet_task_id
        hr_leave_type = self.env['hr.leave.type'].create({
            'name': 'Leave Type with timesheet generation',
            'requires_allocation': 'no',
            'timesheet_generate': True,
            'timesheet_project_id': internal_project.id,
            'timesheet_task_id': internal_task_leaves.id,
        })
        HrLeave = self.env['hr.leave'].with_context(mail_create_nolog=True, mail_notrack=True)
        # employee creates a leave request
        number_of_days = (leave_end_datetime - leave_start_datetime).days
        holiday = HrLeave.with_user(self.user_employee).create({
            'name': 'Leave 1',
            'employee_id': self.empl_employee.id,
            'holiday_status_id': hr_leave_type.id,
            'date_from': leave_start_datetime,
            'date_to': leave_end_datetime,
            'number_of_days': number_of_days,
        })
        holiday.with_user(SUPERUSER_ID).action_validate()
        result = HrEmployee.get_timesheet_and_working_hours_for_employees(employees_grid_data, start_date, end_date)
        self.assertTrue(len(holiday.timesheet_ids) > 0 ,'Timesheet entry should be created in Internal project for time off.')
        # working hours for employee after leave creations
        self.assertEqual(result[self.empl_employee.id]['units_to_work'], 32, "Employee's weekly units of work after the leave creation should be 32.")
        self.assertEqual(result[self.empl_employee.id].get('worked_hours'), None, "Employee's working hours shouldn't be altered after the leave creation.")

        # Timesheet created for same project
        timesheet1 = self.env['account.analytic.line'].with_user(self.user_employee).create({
            'name': "my timesheet 1",
            'project_id': internal_project.id,
            'task_id': internal_task_leaves.id,
            'date': '2021-10-04',
            'unit_amount': 8.0,
        })
        timesheet1.with_user(self.user_manager).action_validate_timesheet()
        result = HrEmployee.get_timesheet_and_working_hours_for_employees(employees_grid_data, start_date, end_date)
        # working hours for employee after Timesheet creations
        self.assertEqual(result[self.empl_employee.id]['units_to_work'], 32, "Employee's one week units of work after the Timesheet creation should be 32.")
        self.assertEqual(result[self.empl_employee.id].get('worked_hours'), 8, "Employee's working hours after the Timesheet creation should be 8.")


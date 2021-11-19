# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta
import pytz

from odoo.tests.common import tagged
from odoo.addons.hr_payroll.tests.common import TestPayslipBase


@tagged('work_entry')
class TestWorkEntry(TestPayslipBase):
    def setUp(self):
        super(TestWorkEntry, self).setUp()
        self.tz = pytz.timezone(self.richard_emp.tz)
        self.start = datetime(2015, 11, 1, 1, 0, 0)
        self.end = datetime(2015, 11, 30, 23, 59, 59)
        self.resource_calendar_id = self.env['resource.calendar'].create({'name': 'Zboub'})
        contract = self.env['hr.contract'].create({
            'date_start': self.start.date() - relativedelta(days=5),
            'name': 'dodo',
            'resource_calendar_id': self.resource_calendar_id.id,
            'wage': 1000,
            'employee_id': self.richard_emp.id,
            'structure_type_id': self.structure_type.id,
            'state': 'open',
            'date_generated_from': self.end.date() + relativedelta(days=5),
        })
        self.richard_emp.resource_calendar_id = self.resource_calendar_id
        self.richard_emp.contract_id = contract

    def test_time_normal_work_entry(self):
        # Normal attendances (global to all employees)
        work_entries = self.richard_emp.contract_id._generate_work_entries(self.start, self.end)
        work_entries.action_validate()
        hours = self.richard_emp.contract_id._get_work_hours(self.start, self.end)
        sum_hours = sum(v for k, v in hours.items() if k in self.env.ref('hr_work_entry.work_entry_type_attendance').ids)

        self.assertEqual(sum_hours, 168.0)

    def test_time_extra_work_entry(self):
        start = datetime(2015, 11, 1, 10, 0, 0)
        end = datetime(2015, 11, 1, 17, 0, 0)
        work_entry = self.env['hr.work.entry'].create({
            'name': '1',
            'employee_id': self.richard_emp.id,
            'contract_id': self.richard_emp.contract_id.id,
            'work_entry_type_id': self.work_entry_type.id,
            'date_start': start,
            'date_stop': end,
        })
        work_entry.action_validate()

        work_entries = self.richard_emp.contract_id._generate_work_entries(self.start, self.end)
        work_entries.action_validate()
        hours = self.richard_emp.contract_id._get_work_hours(self.start, self.end)
        sum_hours = sum(v for k, v in hours.items() if k in self.work_entry_type.ids)

        self.assertEqual(sum_hours, 7.0)

# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Datetime
from odoo.tests.common import tagged
from odoo.addons.hr_payroll_holidays.tests.common import TestPayrollHolidaysBase

from dateutil.relativedelta import relativedelta

@tagged('payroll_holidays_defer')
class TestTimeoffDefer(TestPayrollHolidaysBase):

    def test_no_defer(self):
        #create payslip -> waiting or draft
        payslip = self.env['hr.payslip'].create({
            'name': 'Donald Payslip',
            'employee_id': self.emp.id,
        })

        # Puts the payslip to draft/waiting
        payslip.compute_sheet()

        #create a time off for our employee, validating it now should not put it as to_defer
        leave = self.env['hr.leave'].create({
            'name': 'Golf time',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.emp.id,
            'date_from': (Datetime.today() + relativedelta(day=13)),
            'date_to': (Datetime.today() + relativedelta(day=16)),
            'number_of_days': 3,
        })
        leave.action_approve()

        self.assertNotEqual(leave.payslip_state, 'blocked', 'Leave should not be to defer')

    def test_to_defer(self):
        #create payslip
        payslip = self.env['hr.payslip'].create({
            'name': 'Donald Payslip',
            'employee_id': self.emp.id,
        })

        # Puts the payslip to draft/waiting
        payslip.compute_sheet()
        payslip.action_payslip_done()

        #create a time off for our employee, validating it now should put it as to_defer
        leave = self.env['hr.leave'].create({
            'name': 'Golf time',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.emp.id,
            'date_from': (Datetime.today() + relativedelta(day=13)),
            'date_to': (Datetime.today() + relativedelta(day=16)),
            'number_of_days': 3,
        })
        leave.action_approve()
        self.assertEqual(leave.payslip_state, 'blocked', 'Leave should be to defer')

    def test_multi_payslip_defer(self):
        #A leave should only be set to defer if ALL colliding with the time period of the time off are in a done state
        # it should not happen if a payslip for that time period is still in a waiting state

        #create payslip -> waiting
        waiting_payslip = self.env['hr.payslip'].create({
            'name': 'Donald Payslip draft',
            'employee_id': self.emp.id,
        })
        #payslip -> done
        done_payslip = self.env['hr.payslip'].create({
            'name': 'Donald Payslip done',
            'employee_id': self.emp.id,
        })

        # Puts the waiting payslip to draft/waiting
        waiting_payslip.compute_sheet()
        # Puts the done payslip to the done state
        done_payslip.compute_sheet()
        done_payslip.action_payslip_done()

        #create a time off for our employee, validating it now should not put it as to_defer
        leave = self.env['hr.leave'].create({
            'name': 'Golf time',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.emp.id,
            'date_from': (Datetime.today() + relativedelta(day=13)),
            'date_to': (Datetime.today() + relativedelta(day=16)),
            'number_of_days': 3,
        })
        leave.action_approve()

        self.assertNotEqual(leave.payslip_state, 'blocked', 'Leave should not be to defer')

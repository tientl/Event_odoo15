# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import ValidationError
from datetime import datetime


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def compute_sheet(self):
        if self.filtered(lambda p: p.is_regular) and not self.env.context.get('salary_simulation', False):
            employees = self.mapped('employee_id')
            leaves = self.env['hr.leave'].search([
                ('employee_id', 'in', employees.ids),
                ('state', '!=', 'refuse'),
            ])
            leaves_to_defer = leaves.filtered(lambda l: l.payslip_state == 'blocked')
            if leaves_to_defer:
                raise ValidationError(_(
                    'There is some remaining time off to defer for these employees: \n\n %s',
                    ', '.join(e.display_name for e in leaves_to_defer.mapped('employee_id'))))
            dates = self.mapped('date_to')
            max_date = datetime.combine(max(dates), datetime.max.time())
            leaves_to_green = leaves.filtered(lambda l: l.payslip_state != 'blocked' and l.date_to <= max_date)
            leaves_to_green.write({'payslip_state': 'done'})
        return super().compute_sheet()

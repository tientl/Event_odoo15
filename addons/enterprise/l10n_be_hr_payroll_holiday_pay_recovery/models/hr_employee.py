# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    l10n_be_holiday_pay_to_recover_n = fields.Float(
        string="Simple Holiday Pay to Recover (N)", tracking=True, groups="hr_payroll.group_hr_payroll_user",
        help="Amount of the holiday pay paid by the previous employer to recover.")
    l10n_be_holiday_pay_number_of_days_n = fields.Float(
        string="Number of days to recover (N)", tracking=True, groups="hr_payroll.group_hr_payroll_user",
        help="Number of days on which you should recover the holiday pay.")
    l10n_be_holiday_pay_recovered_n = fields.Float(
        string="Recovered Simple Holiday Pay (N)", tracking=True,
        compute='_compute_l10n_be_holiday_pay_recovered', groups="hr_payroll.group_hr_payroll_user",
        help="Amount of the holiday pay paid by the previous employer already recovered.")

    l10n_be_holiday_pay_to_recover_n1 = fields.Float(
        string="Simple Holiday Pay to Recover (N-1)", tracking=True, groups="hr_payroll.group_hr_payroll_user",
        help="Amount of the holiday pay paid by the previous employer to recover.")
    l10n_be_holiday_pay_number_of_days_n1 = fields.Float(
        string="Number of days to recover (N-1)", tracking=True, groups="hr_payroll.group_hr_payroll_user",
        help="Number of days on which you should recover the holiday pay.")
    l10n_be_holiday_pay_recovered_n1 = fields.Float(
        string="Recovered Simple Holiday Pay (N-1)", tracking=True,
        compute='_compute_l10n_be_holiday_pay_recovered', groups="hr_payroll.group_hr_payroll_user",
        help="Amount of the holiday pay paid by the previous employer already recovered.")

    def _compute_l10n_be_holiday_pay_recovered(self):
        payslips = self.env['hr.payslip'].search([
            ('employee_id', 'in', self.ids),
            ('struct_id', '=', self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id),
            ('company_id', '=', self.env.company.id),
            ('state', 'in', ['done', 'paid']),
        ])
        line_values = payslips._get_line_values(['HolPayRecN', 'HolPayRecN1'])
        for employee in self:
            employee_payslips = payslips.filtered(lambda p: p.employee_id == employee)
            employee.l10n_be_holiday_pay_recovered_n = - sum(line_values['HolPayRecN'][p.id]['total'] for p in employee_payslips)
            employee.l10n_be_holiday_pay_recovered_n1 = - sum(line_values['HolPayRecN1'][p.id]['total'] for p in employee_payslips)

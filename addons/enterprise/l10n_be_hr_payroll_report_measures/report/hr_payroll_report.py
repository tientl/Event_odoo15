# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrPayrollReport(models.Model):
    _inherit = "hr.payroll.report"

    struct_id = fields.Many2one('hr.payroll.structure', 'Structure', readonly=True)
    l10n_be_accounting_remuneration = fields.Float('Accounting: Remuneration', readonly=True)
    l10n_be_ip = fields.Float('IP', readonly=True)
    l10n_be_ip_deduction = fields.Float('IP Deduction', readonly=True)
    l10n_be_rep_fees = fields.Float('Representation Fees', readonly=True)
    # l10n_be_rep_fees_volatile = fields.Float('Representation Fees (Without Serious Standards)', readonly=True)
    l10n_be_car_priv = fields.Float('Private car', readonly=True)
    l10n_be_car_atn = fields.Float('Benefit in Kind (Company Car)', readonly=True)
    l10n_be_mobile_atn = fields.Float('Benefit in Kind (Mobile)', readonly=True)
    l10n_be_internet_atn = fields.Float('Benefit in Kind (Internet)', readonly=True)
    l10n_be_laptop_atn = fields.Float('Benefit in Kind (Laptop)', readonly=True)
    l10n_be_atn_deduction = fields.Float('Benefit in Kind Deductions (All)', readonly=True)
    l10n_be_onss_employer = fields.Float('ONSS (Employer)', readonly=True)
    l10n_be_onss_ffe = fields.Float('ONSS (Company Closure Fund)', readonly=True)
    l10n_be_meal_voucher_count = fields.Float('Meal Voucher Count', readonly=True)
    l10n_be_meal_voucher_employer = fields.Float('Meal Voucher (Employer)', readonly=True)
    l10n_be_withholding_taxes_exemption = fields.Float('Withholding Taxes Exemption', readonly=True)

    def _select(self):
        worker_count = len(self.env['hr.contract'].search([
            ('state', '=', 'open'),
            ('company_id', '=', self.env.company.id)]).employee_id)
        ffe_rate = self.env.company._get_ffe_contribution_rate(worker_count)
        return super()._select() + """,
                p.struct_id as struct_id,
                CASE WHEN wd.id = min_id.min_line THEN l10n_be_meal_voucher_count.quantity ELSE 0 END as l10n_be_meal_voucher_count,
                CASE WHEN wd.id = min_id.min_line THEN (c.meal_voucher_amount - 1.09) * l10n_be_meal_voucher_count.quantity ELSE 0 END as l10n_be_meal_voucher_employer,
                CASE WHEN wd.id = min_id.min_line THEN l10n_be_plar.total ELSE 0 END as l10n_be_accounting_remuneration,
                CASE WHEN wd.id = min_id.min_line THEN l10n_be_ip.total ELSE 0 END as l10n_be_ip,
                CASE WHEN wd.id = min_id.min_line THEN l10n_be_ip_deduction.total ELSE 0 END as l10n_be_ip_deduction,
                CASE WHEN wd.id = min_id.min_line THEN l10n_be_rep_fees.total ELSE 0 END as l10n_be_rep_fees,
                CASE WHEN wd.id = min_id.min_line THEN l10n_be_car_priv.total ELSE 0 END as l10n_be_car_priv,
                CASE WHEN wd.id = min_id.min_line THEN l10n_be_car_atn.total ELSE 0 END as l10n_be_car_atn,
                CASE WHEN wd.id = min_id.min_line THEN l10n_be_mobile_atn.total ELSE 0 END as l10n_be_mobile_atn,
                CASE WHEN wd.id = min_id.min_line THEN l10n_be_internet_atn.total ELSE 0 END as l10n_be_internet_atn,
                CASE WHEN wd.id = min_id.min_line THEN l10n_be_laptop_atn.total ELSE 0 END as l10n_be_laptop_atn,
                CASE WHEN wd.id = min_id.min_line THEN -SUM(COALESCE(l10n_be_deduction_atn.total, 0)) ELSE 0 END as l10n_be_atn_deduction,
                CASE WHEN wd.id = min_id.min_line THEN l10n_be_onss_employer.total ELSE 0 END as l10n_be_onss_employer,
                CASE WHEN wd.id = min_id.min_line THEN l10n_be_onss_employer.total * %s ELSE 0 END as l10n_be_onss_ffe,
                l10n_be_274_xx_line.amount as l10n_be_withholding_taxes_exemption
                """ % (ffe_rate)
                # CASE WHEN wd.id = min_id.min_line THEN l10n_be_rep_fees_volatile.total ELSE 0 END as l10n_be_rep_fees_volatile,

    def _from(self):
        return super()._from() + """
                left join l10n_be_274_xx l10n_be_274_xx on (l10n_be_274_xx.date_start BETWEEN p.date_from AND p.date_to AND l10n_be_274_xx.date_end BETWEEN p.date_from AND p.date_to)
                left join l10n_be_274_xx_line l10n_be_274_xx_line on (l10n_be_274_xx_line.sheet_id = l10n_be_274_xx.id AND p.employee_id = l10n_be_274_xx_line.employee_id)
                left join hr_payslip_line l10n_be_meal_voucher_count on (l10n_be_meal_voucher_count.slip_id = p.id and l10n_be_meal_voucher_count.code = 'MEAL_V_EMP')
                left join hr_payslip_line l10n_be_plar on (l10n_be_plar.slip_id = p.id and l10n_be_plar.code = 'REMUNERATION')
                left join hr_payslip_line l10n_be_ip on (l10n_be_ip.slip_id = p.id and l10n_be_ip.code = 'IP')
                left join hr_payslip_line l10n_be_ip_deduction on (l10n_be_ip_deduction.slip_id = p.id and l10n_be_ip_deduction.code = 'IP.DED')
                left join hr_payslip_line l10n_be_rep_fees on (l10n_be_rep_fees.slip_id = p.id and l10n_be_rep_fees.code = 'REP.FEES')
                left join hr_payslip_line l10n_be_car_priv on (l10n_be_car_priv.slip_id = p.id and l10n_be_car_priv.code = 'CAR.PRIV')
                left join hr_payslip_line l10n_be_car_atn on (l10n_be_car_atn.slip_id = p.id and l10n_be_car_atn.code = 'ATN.CAR')
                left join hr_payslip_line l10n_be_mobile_atn on (l10n_be_mobile_atn.slip_id = p.id and l10n_be_mobile_atn.code = 'ATN.MOB')
                left join hr_payslip_line l10n_be_internet_atn on (l10n_be_internet_atn.slip_id = p.id and l10n_be_internet_atn.code = 'ATN.INT')
                left join hr_payslip_line l10n_be_laptop_atn on (l10n_be_laptop_atn.slip_id = p.id and l10n_be_laptop_atn.code = 'ATN.LAP')
                left join hr_payslip_line l10n_be_deduction_atn on (l10n_be_deduction_atn.slip_id = p.id and l10n_be_deduction_atn.code in ('ATN.LAP', 'ATN.INT', 'ATN.MOB', 'ATN.CAR'))
                left join hr_payslip_line l10n_be_onss_employer on (l10n_be_onss_employer.slip_id = p.id and l10n_be_onss_employer.code = 'ONSSEMPLOYER')"""
                # left join hr_payslip_line l10n_be_rep_fees_volatile on (l10n_be_rep_fees_volatile.slip_id = p.id and l10n_be_rep_fees_volatile.code = 'REP.FEES.VOLATILE')

    def _group_by(self):
        return super()._group_by() + """,
                p.struct_id,
                l10n_be_plar.total,
                l10n_be_meal_voucher_count.quantity,
                l10n_be_ip.total,
                l10n_be_ip_deduction.total,
                l10n_be_rep_fees.total,
                l10n_be_car_priv.total,
                l10n_be_car_atn.total,
                l10n_be_mobile_atn.total,
                l10n_be_internet_atn.total,
                l10n_be_laptop_atn.total,
                l10n_be_onss_employer.total,
                l10n_be_274_xx_line.amount"""
                # l10n_be_rep_fees_volatile.total,

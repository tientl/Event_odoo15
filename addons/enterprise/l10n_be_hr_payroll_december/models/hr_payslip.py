#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class Payslip(models.Model):
    _inherit = 'hr.payslip'

    l10n_be_is_december = fields.Boolean(compute='_compute_l10n_be_is_december')

    @api.depends('struct_id', 'date_from')
    def _compute_l10n_be_is_december(self):
        for payslip in self:
            payslip.l10n_be_is_december = payslip.struct_id.code == "CP200MONTHLY" and payslip.date_from and payslip.date_from.month == 12

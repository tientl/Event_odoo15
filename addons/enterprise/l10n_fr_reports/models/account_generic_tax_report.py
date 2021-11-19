# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class AccountGenericTaxReport(models.AbstractModel):
    _inherit = 'account.generic.tax.report'

    def _get_popup_messages(self, line_balance, carryover_balance, options, tax_report_line):
        country_id = self.env['account.tax.report'].browse(options['tax_report']).country_id
        if country_id.code != 'FR':
            return super()._get_popup_messages(line_balance, carryover_balance, options, tax_report_line)
        return {
            'out_of_bounds': {
                'description1': _("This amount will be reported to the grid 22 of the next period."),
            }
        }

    def _get_column_styles(self, report_line):
        report_id = report_line['tax_report_line'].report_id.id
        country_id = self.env['account.tax.report'].browse(report_id).country_id
        if country_id.code != 'FR':
            return super()._get_column_styles(report_line)

        return {}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class AccountGenericTaxReport(models.AbstractModel):
    _inherit = 'account.generic.tax.report'

    def _build_total_line(self, report_line, parent_id, balances_by_code, formulas_dict, number_periods, deferred_line, options):
        r = super()._build_total_line(report_line, parent_id, balances_by_code, formulas_dict, number_periods, deferred_line, options)

        # We don't need the currency on those lines
        if r['line_code'] in ('BG_TR_33', 'BG_TR_43'):
            r['columns'][0]['name'] = r['columns'][0]['no_format']

        return r

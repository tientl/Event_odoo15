# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class GenericTaxReport(models.AbstractModel):
    _inherit = 'account.generic.tax.report'

    def _get_total_line_eval_dict(self, period_balances_by_code, period_date_from, period_date_to, options):
        """ Overridden in order to add the net profit of the period to the variables
        available for the computation of total lines in GST Return F5 report.
        """
        eval_dict = super(GenericTaxReport, self)._get_total_line_eval_dict(period_balances_by_code, period_date_from, period_date_to, options)

        if self._get_report_country_code(options) == 'SG':
            net_profit_query = """select coalesce(-sum(balance), 0)
                                  from account_move_line aml
                                  join account_account account
                                  on account.id = aml.account_id
                                  join account_move move
                                  on move.id = aml.move_id
                                  where
                                  account.user_type_id in %(account_types)s
                                  and (%(show_draft)s or move.state = 'posted')
                                  and aml.date <= %(date_to)s
                                  and aml.date >= %(date_from)s
                                  and move.company_id in %(company_ids)s;"""

            account_types = tuple(self.env['ir.model.data']._xmlid_to_res_id(xmlid) for xmlid in ['account.data_account_type_revenue', 'account.data_account_type_expenses', 'account.data_account_type_depreciation'])
            params = {
                'account_types': account_types,
                'show_draft': options['all_entries'],
                'date_to': period_date_to,
                'date_from': period_date_from,
                'company_ids': tuple(self.get_report_company_ids(options)),
            }
            self.env.cr.execute(net_profit_query, params)
            eval_dict['net_profit'] = self.env.cr.fetchall()[0][0]

        return eval_dict

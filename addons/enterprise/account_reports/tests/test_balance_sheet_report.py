# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# pylint: disable=bad-whitespace
from .common import TestAccountReportsCommon

from odoo import fields
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestBalanceSheetReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.report = cls.env.ref('account_reports.account_financial_report_balancesheet0')

    def test_balance_sheet_custom_date(self):
        line_id = self.env.ref('account_reports.account_financial_report_bank_view0').id
        options = self._init_options(self.report, fields.Date.from_string('2020-02-01'), fields.Date.from_string('2020-02-28'))
        options['date']['filter'] = 'custom'
        options['unfolded_lines'] = [line_id]
        options.pop('multi_company', None)

        invoices = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'date': '2020-0%s-15' % i,
            'invoice_date': '2020-0%s-15' % i,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
                'tax_ids': [(6, 0, self.tax_sale_a.ids)],
            })],
        } for i in range(1, 4)])
        invoices.action_post()

        dummy, lines = self.report._get_table(options)
        self.assertLinesValues(
            lines,
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('ASSETS',                                      2300.00),
                ('Current Assets',                              2300.00),
                ('Bank and Cash Accounts',                      0.00),
                ('Receivables',                                 2300.00),
                ('Current Assets',                              0.00),
                ('Prepayments',                                 0.00),
                ('Total Current Assets',                        2300.00),
                ('Plus Fixed Assets',                           0.00),
                ('Plus Non-current Assets',                     0.00),
                ('Total ASSETS',                                2300.00),

                ('LIABILITIES',                                 300.00),
                ('Current Liabilities',                         300.00),
                ('Current Liabilities',                         300.00),
                ('Payables',                                    0.00),
                ('Total Current Liabilities',                   300.00),
                ('Plus Non-current Liabilities',                0.00),
                ('Total LIABILITIES',                           300.00),

                ('EQUITY',                                      2000.00),
                ('Unallocated Earnings',                        2000.00),
                ('Current Year Unallocated Earnings',           2000.00),
                ('Current Year Earnings',                       2000.00),
                ('Current Year Allocated Earnings',             0.00),
                ('Total Current Year Unallocated Earnings',     2000.00),
                ('Previous Years Unallocated Earnings',         0.00),
                ('Total Unallocated Earnings',                  2000.00),
                ('Retained Earnings',                           0.00),
                ('Total EQUITY',                                2000.00),
                ('LIABILITIES + EQUITY',                        2300.00),
            ],
        )

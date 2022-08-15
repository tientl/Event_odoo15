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

    def test_report_lines_ordering(self):
        """ Check that the report lines are correctly ordered with nested account groups """
        self.env['account.group'].create(
            [
                {
                    'name': 'A',
                    'code_prefix_start': '101402',
                    'code_prefix_end': '101601',
                },
                {
                    'name': 'A1',
                    'code_prefix_start': '1014040',
                    'code_prefix_end': '1015010',
                },
            ]
        )
        bank_and_cash_type = self.env.ref('account.data_account_type_liquidity')

        def find_account(code):
            return self.env['account.account'].search([('code', '=', code), ('company_id', '=', self.env.company.id)])

        account_debit = find_account('101000')
        account_bank = find_account('101404')
        account_cash = find_account('101501')
        account_a = self.env['account.account'].create([{'code': '1014040', 'name': 'A', 'user_type_id': bank_and_cash_type.id}])
        account_c = self.env['account.account'].create([{'code': '101600', 'name': 'C', 'user_type_id': bank_and_cash_type.id}])

        # Create a journal entry for each account
        for account in [account_a, account_c, account_bank, account_cash]:
            move = self.env['account.move'].create({
                'move_type': 'entry',
                'date': '2020-02-02',
                'line_ids': [
                    (0, 0, {
                        'account_id': account.id,
                        'name': 'line_debit',
                    }),
                    (0, 0, {
                        'name': 'line_credit',
                        'account_id': account_debit.id,
                    }),
                ],
            })
            move.action_post()

        # Create the report hierachy with the Bank and Cash Accounts lines unfolded
        line_id = self.env.ref('account_reports.account_financial_report_bank_view0').id
        options = self._init_options(
            self.report,
            fields.Date.from_string('2020-02-01'),
            fields.Date.from_string('2020-02-28')
        )
        options['date']['filter'] = 'custom'
        options['unfolded_lines'] = [self.report._get_generic_line_id('account.financial.html.report.line', line_id)]
        options.pop('multi_company', None)
        headers, lines = self.report._get_table(options)
        lines = self.report._create_hierarchy(lines, options)

        # The Bank and Cash Accounts section start at index 2
        # Since we created 4 lines + 2 groups, we keep the 6 following lines
        lines = [{'name': line['name'], 'level': line['level']} for line in lines][2:9]

        expected_lines = [
            {'level': 2, 'name': 'Bank and Cash Accounts'},
            {'level': 3, 'name': '101402-101601 A'},
            {'level': 4, 'name': '101404 Bank'},
            {'level': 4, 'name': '1014040-1015010 A1'},
            {'level': 5, 'name': '1014040 A'},
            {'level': 5, 'name': '101501 Cash'},
            {'level': 4, 'name': '101600 C'}
        ]
        self.assertEqual(lines, expected_lines)

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

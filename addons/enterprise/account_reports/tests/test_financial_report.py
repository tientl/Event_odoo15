# -*- coding: utf-8 -*-
# pylint: disable=C0326

from .common import TestAccountReportsCommon

from odoo import fields
from odoo.tests import tagged
from odoo.osv.expression import OR
from odoo.tools import ustr

import ast

from freezegun import freeze_time


@tagged('post_install', '-at_install')
class TestFinancialReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # ==== Partners ====

        cls.partner_a = cls.env['res.partner'].create({'name': 'partner_a', 'company_id': False})
        cls.partner_b = cls.env['res.partner'].create({'name': 'partner_b', 'company_id': False})
        cls.partner_c = cls.env['res.partner'].create({'name': 'partner_c', 'company_id': False})

        # ==== Accounts ====

        # Cleanup existing "Current year earnings" accounts since we can only have one by company.
        cls.env['account.account'].search([
            ('company_id', 'in', (cls.company_data['company'] + cls.company_data_2['company']).ids),
            ('user_type_id', '=', cls.env.ref('account.data_unaffected_earnings').id),
        ]).unlink()

        account_type_data = [
            (cls.env.ref('account.data_account_type_receivable'),           {'reconcile': True}),
            (cls.env.ref('account.data_account_type_payable'),              {'reconcile': True}),
            (cls.env.ref('account.data_account_type_liquidity'),            {}),
            (cls.env.ref('account.data_account_type_current_assets'),       {}),
            (cls.env.ref('account.data_account_type_prepayments'),          {}),
            (cls.env.ref('account.data_account_type_fixed_assets'),         {}),
            (cls.env.ref('account.data_account_type_non_current_assets'),   {}),
            (cls.env.ref('account.data_account_type_equity'),               {}),
            (cls.env.ref('account.data_unaffected_earnings'),               {}),
            (cls.env.ref('account.data_account_type_revenue'),              {}),
        ]

        accounts = cls.env['account.account'].create([{
            **data[1],
            'name': 'account%s' % i,
            'code': 'code%s' % i,
            'user_type_id': data[0].id,
            'company_id': cls.company_data['company'].id,
        } for i, data in enumerate(account_type_data)])

        accounts_2 = cls.env['account.account'].create([{
            **data[1],
            'name': 'account%s' % (i + 100),
            'code': 'code%s' % (i + 100),
            'user_type_id': data[0].id,
            'company_id': cls.company_data_2['company'].id,
        } for i, data in enumerate(account_type_data)])

        # ==== Custom filters ====

        cls.filter = cls.env['ir.filters'].create({
            'name': 'filter',
            'model_id': 'account.move.line',
            'context': str({'group_by': ['date', 'partner_id']}),
            'domain': str([('partner_id.name', '=', 'partner_a')]),
        })

        # ==== Journal entries ====

        cls.move_2019 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2019-01-01'),
            'line_ids': [
                (0, 0, {'debit': 25.0,      'credit': 0.0,      'account_id': accounts[0].id,   'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 25.0,      'credit': 0.0,      'account_id': accounts[0].id,   'partner_id': cls.partner_b.id}),
                (0, 0, {'debit': 25.0,      'credit': 0.0,      'account_id': accounts[0].id,   'partner_id': cls.partner_c.id}),
                (0, 0, {'debit': 25.0,      'credit': 0.0,      'account_id': accounts[0].id,   'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 200.0,     'credit': 0.0,      'account_id': accounts[1].id,   'partner_id': cls.partner_b.id}),
                (0, 0, {'debit': 0.0,       'credit': 300.0,    'account_id': accounts[2].id,   'partner_id': cls.partner_c.id}),
                (0, 0, {'debit': 400.0,     'credit': 0.0,      'account_id': accounts[3].id,   'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 0.0,       'credit': 1100.0,   'account_id': accounts[4].id,   'partner_id': cls.partner_b.id}),
                (0, 0, {'debit': 700.0,     'credit': 0.0,      'account_id': accounts[6].id,   'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 0.0,       'credit': 800.0,    'account_id': accounts[7].id,   'partner_id': cls.partner_b.id}),
                (0, 0, {'debit': 800.0,     'credit': 0.0,      'account_id': accounts[8].id,   'partner_id': cls.partner_c.id}),
            ],
        })
        cls.move_2019.action_post()

        cls.move_2018 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2018-01-01'),
            'line_ids': [
                (0, 0, {'debit': 1000.0,    'credit': 0.0,      'account_id': accounts[0].id,   'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 0.0,       'credit': 1000.0,   'account_id': accounts[2].id,   'partner_id': cls.partner_b.id}),
                (0, 0, {'debit': 250.0,     'credit': 0.0,      'account_id': accounts[0].id,   'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 0.0,       'credit': 250.0,    'account_id': accounts[9].id,   'partner_id': cls.partner_a.id}),
            ],
        })
        cls.move_2018.action_post()

        cls.move_2017 = cls.env['account.move'].with_company(cls.company_data_2['company']).create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2017-01-01'),
            'line_ids': [
                (0, 0, {'debit': 2000.0,    'credit': 0.0,      'account_id': accounts_2[0].id, 'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 0.0,       'credit': 4000.0,   'account_id': accounts_2[2].id, 'partner_id': cls.partner_b.id}),
                (0, 0, {'debit': 0.0,       'credit': 5000.0,   'account_id': accounts_2[4].id, 'partner_id': cls.partner_c.id}),
                (0, 0, {'debit': 7000.0,    'credit': 0.0,      'account_id': accounts_2[6].id, 'partner_id': cls.partner_a.id}),
            ],
        })
        cls.move_2017.action_post()

        cls.report = cls.env.ref('account_reports.account_financial_report_balancesheet0')
        cls.report.applicable_filters_ids |= cls.filter

        cls.report_no_parent_id = cls.env["account.financial.html.report"].create({"name": "Test report"})
        cls.report_no_parent_id["line_ids"] = [
            (0, 0, {
                "name": "Invisible Partner A line",
                "code": "INVA",
                "domain": [("partner_id", "=", cls.partner_a.id)],
                "level": 2,
                "groupby": "account_id",
                "formulas": "sum",
                "special_date_changer": "strict_range"
            }),
            (0, 0, {
                "name": "Invisible Partner B line",
                "code": "INVB",
                "domain": [("partner_id", "=", cls.partner_b.id)],
                "level": 2,
                "groupby": "account_id",
                "formulas": "sum",
                "special_date_changer": "strict_range"
            }),
            (0, 0, {
                "name": "Total of Invisible lines",
                "code": "INVT",
                "parent_id": cls.report_no_parent_id.id,
                "level": 1,
                "formulas": "INVA + INVB"
            })
        ]

    def _build_generic_id_from_financial_line(self, financial_rep_ln_xmlid):
        report_line = self.env.ref(financial_rep_ln_xmlid)
        return '-account.financial.html.report.line-%s' % report_line.id

    def test_financial_report_strict_range_on_report_lines_with_no_parent_id(self):
        """ Tests that lines with no parent can be correctly filtered by date range """
        options = self._init_options(self.report_no_parent_id, fields.Date.from_string('2019-01-01'), fields.Date.from_string('2019-12-31'))
        options.pop('multi_company', None)

        _headers, lines = self.report_no_parent_id._get_table(options)
        self.assertLinesValues(
            lines,
            #   Name                         Balance
            [   0,                           1],
            [
                ('Invisible Partner A line', 1150.0),
                ('Invisible Partner B line', -1675.0),
                ('Total of Invisible lines', -525.0),
            ])

    def test_financial_report_strict_empty_range_on_report_lines_with_no_parent_id(self):
        """ Tests that lines with no parent can be correctly filtered by date range with no invoices"""
        options = self._init_options(self.report_no_parent_id, fields.Date.from_string('2019-03-01'), fields.Date.from_string('2019-03-31'))
        options.pop('multi_company', None)

        _headers, lines = self.report_no_parent_id._get_table(options)
        self.assertLinesValues(
            lines,
            #   Name                         Balance
            [   0,                           1],
            [
                ('Invisible Partner A line', 0.0),
                ('Invisible Partner B line', 0.0),
                ('Total of Invisible lines', 0.0),
            ])

    @freeze_time("2016-06-06")
    def test_balance_sheet_today_current_year_earnings(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'date': '2016-02-02',
            'invoice_line_ids': [(0, 0, {'product_id': self.product_a.id, 'price_unit': 110})]
        })
        invoice.action_post()

        options = self._init_options(self.report, fields.Date.from_string('2016-06-01'), fields.Date.from_string('2016-06-06'))
        options['date']['filter'] = 'today'
        options.pop('multi_company', None)

        headers, lines = self.report._get_table(options)
        self.assertLinesValues(
            lines,
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('ASSETS',                                      110.0),
                ('Current Assets',                              110.0),
                ('Bank and Cash Accounts',                      0.0),
                ('Receivables',                                 110.0),
                ('Current Assets',                              0.0),
                ('Prepayments',                                 0.0),
                ('Total Current Assets',                        110.0),
                ('Plus Fixed Assets',                           0.0),
                ('Plus Non-current Assets',                     0.0),
                ('Total ASSETS',                                110.0),

                ('LIABILITIES',                                 0.0),
                ('Current Liabilities',                         0.0),
                ('Current Liabilities',                         0.0),
                ('Payables',                                    0.0),
                ('Total Current Liabilities',                   0.0),
                ('Plus Non-current Liabilities',                0.0),
                ('Total LIABILITIES',                           0.0),

                ('EQUITY',                                      110.0),
                ('Unallocated Earnings',                        110.0),
                ('Current Year Unallocated Earnings',           110.0),
                ('Current Year Earnings',                       110.0),
                ('Current Year Allocated Earnings',             0.0),
                ('Total Current Year Unallocated Earnings',     110.0),
                ('Previous Years Unallocated Earnings',         0.0),
                ('Total Unallocated Earnings',                  110.0),
                ('Retained Earnings',                           0.0),
                ('Total EQUITY',                                110.0),

                ('LIABILITIES + EQUITY',                        110.0),
            ],
        )

    @freeze_time("2016-05-05")
    def test_balance_sheet_last_month_vs_custom_current_year_earnings(self):
        """
        Checks the balance sheet calls the right period of the P&L when using last_month date filter, or an equivalent custom filter
        (this used to fail due to options regeneration made by the P&L's _get_options())"
        """
        to_invoice = [('15', '11'), ('15', '12'), ('16', '01'), ('16', '02'), ('16', '03'), ('16', '04')]
        for year, month in to_invoice:
            invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': f'20{year}-{month}-01',
                'invoice_line_ids': [(0, 0, {'product_id': self.product_a.id, 'price_unit': 1000})]
            })
            invoice.action_post()
        expected_result =[
                ('ASSETS',                                      6000.0),
                ('Current Assets',                              6000.0),
                ('Bank and Cash Accounts',                      0.0),
                ('Receivables',                                 6000.0),
                ('Current Assets',                              0.0),
                ('Prepayments',                                 0.0),
                ('Total Current Assets',                        6000.0),
                ('Plus Fixed Assets',                           0.0),
                ('Plus Non-current Assets',                     0.0),
                ('Total ASSETS',                                6000.0),

                ('LIABILITIES',                                 0.0),
                ('Current Liabilities',                         0.0),
                ('Current Liabilities',                         0.0),
                ('Payables',                                    0.0),
                ('Total Current Liabilities',                   0.0),
                ('Plus Non-current Liabilities',                0.0),
                ('Total LIABILITIES',                           0.0),

                ('EQUITY',                                      6000.0),
                ('Unallocated Earnings',                        6000.0),
                ('Current Year Unallocated Earnings',           4000.0),
                ('Current Year Earnings',                       4000.0),
                ('Current Year Allocated Earnings',             0.0),
                ('Total Current Year Unallocated Earnings',     4000.0),
                ('Previous Years Unallocated Earnings',         2000.0),
                ('Total Unallocated Earnings',                  6000.0),
                ('Retained Earnings',                           0.0),
                ('Total EQUITY',                                6000.0),
                ('LIABILITIES + EQUITY',                        6000.0),

            ]
        options = self._init_options(self.report, fields.Date.from_string('2016-05-05'), fields.Date.from_string('2016-05-05'))
        options.pop('multi_company', None)

        # End of Last Month
        options['date']['filter'] = 'last_month'
        lines = self.report._get_table(options)[1]
        self.assertLinesValues(
            lines,
            #   Name                                            Balance
            [   0,                                              1],
            expected_result,
        )
        # Custom
        options['date']['filter'] = 'custom'
        lines = self.report._get_table(options)[1]
        self.assertLinesValues(
            lines,
            #   Name                                            Balance
            [   0,                                              1],
            expected_result,
        )

    def test_financial_report_single_company(self):
        line_id = self._build_generic_id_from_financial_line('account_reports.account_financial_report_bank_view0')
        options = self._init_options(self.report, fields.Date.from_string('2019-01-01'), fields.Date.from_string('2019-12-31'))
        options['unfolded_lines'] = [line_id]
        options.pop('multi_company', None)

        headers, lines = self.report._get_table(options)
        self.assertLinesValues(
            lines,
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('ASSETS',                                      50.0),
                ('Current Assets',                              -650.0),
                ('Bank and Cash Accounts',                      -1300.0),
                ('code2 account2',                              -1300.0),
                ('Total Bank and Cash Accounts',                -1300.0),
                ('Receivables',                                 1350.0),
                ('Current Assets',                              400.0),
                ('Prepayments',                                 -1100.0),
                ('Total Current Assets',                        -650.0),
                ('Plus Fixed Assets',                           0.0),
                ('Plus Non-current Assets',                     700.0),
                ('Total ASSETS',                                50.0),

                ('LIABILITIES',                                 -200.0),
                ('Current Liabilities',                         -200.0),
                ('Current Liabilities',                         0.0),
                ('Payables',                                    -200.0),
                ('Total Current Liabilities',                   -200.0),
                ('Plus Non-current Liabilities',                0.0),
                ('Total LIABILITIES',                           -200.0),

                ('EQUITY',                                      250.0),
                ('Unallocated Earnings',                        -550.0),
                ('Current Year Unallocated Earnings',           -800.0),
                ('Current Year Earnings',                       0.0),
                ('Current Year Allocated Earnings',             -800.0),
                ('Total Current Year Unallocated Earnings',     -800.0),
                ('Previous Years Unallocated Earnings',         250.0),
                ('Total Unallocated Earnings',                  -550.0),
                ('Retained Earnings',                           800.0),
                ('Total EQUITY',                                250.0),

                ('LIABILITIES + EQUITY',                        50.0),
            ],
        )

        self.assertLinesValues(
            self.report._get_lines(options, line_id=line_id),
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('Bank and Cash Accounts',                      -1300.0),
                ('code2 account2',                              -1300.0),
                ('Total Bank and Cash Accounts',                -1300.0),
            ],
        )

    def test_financial_report_multi_company_currency(self):
        line_id = self._build_generic_id_from_financial_line('account_reports.account_financial_report_bank_view0')
        options = self._init_options(self.report, fields.Date.from_string('2019-01-01'), fields.Date.from_string('2019-12-31'))
        options['unfolded_lines'] = [line_id]

        headers, lines = self.report._get_table(options)
        self.assertLinesValues(
            lines,
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('ASSETS',                                      50.0),
                ('Current Assets',                              -4150.0),
                ('Bank and Cash Accounts',                      -3300.0),
                ('code102 account102',                          -2000.0),
                ('code2 account2',                              -1300.0),
                ('Total Bank and Cash Accounts',                -3300.0),
                ('Receivables',                                 2350.0),
                ('Current Assets',                              400.0),
                ('Prepayments',                                 -3600.0),
                ('Total Current Assets',                        -4150.0),
                ('Plus Fixed Assets',                           0.0),
                ('Plus Non-current Assets',                     4200.0),
                ('Total ASSETS',                                50.0),

                ('LIABILITIES',                                 -200.0),
                ('Current Liabilities',                         -200.0),
                ('Current Liabilities',                         0.0),
                ('Payables',                                    -200.0),
                ('Total Current Liabilities',                   -200.0),
                ('Plus Non-current Liabilities',                0.0),
                ('Total LIABILITIES',                           -200.0),

                ('EQUITY',                                      250.0),
                ('Unallocated Earnings',                        -550.0),
                ('Current Year Unallocated Earnings',           -800.0),
                ('Current Year Earnings',                       0.0),
                ('Current Year Allocated Earnings',             -800.0),
                ('Total Current Year Unallocated Earnings',     -800.0),
                ('Previous Years Unallocated Earnings',         250.0),
                ('Total Unallocated Earnings',                  -550.0),
                ('Retained Earnings',                           800.0),
                ('Total EQUITY',                                250.0),

                ('LIABILITIES + EQUITY',                        50.0),
            ],
        )

        self.assertLinesValues(
            self.report._get_lines(options, line_id=line_id),
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('Bank and Cash Accounts',                      -3300.0),
                ('code102 account102',                          -2000.0),
                ('code2 account2',                              -1300.0),
                ('Total Bank and Cash Accounts',                -3300.0),
            ],
        )

    def test_financial_report_comparison(self):
        line_id = self._build_generic_id_from_financial_line('account_reports.account_financial_report_bank_view0')
        options = self._init_options(self.report, fields.Date.from_string('2019-01-01'), fields.Date.from_string('2019-12-31'))
        options = self._update_comparison_filter(options, self.report, 'custom', 1, date_to=fields.Date.from_string('2018-12-31'))
        options['unfolded_lines'] = [line_id]

        headers, lines = self.report._get_table(options)
        self.assertLinesValues(
            lines,
            #   Name                                            Balance     Comparison  %
            [   0,                                              1,          2,          3],
            [
                ('ASSETS',                                      50.0,       250.0,      '-80.0%'),
                ('Current Assets',                              -4150.0,    -3250.0,    '27.7%'),
                ('Bank and Cash Accounts',                      -3300.0,    -3000.0,    '10.0%'),
                ('code102 account102',                          -2000.0,    -2000.0,    '0.0%'),
                ('code2 account2',                              -1300.0,    -1000.0,    '30.0%'),
                ('Total Bank and Cash Accounts',                -3300.0,    -3000.0,    '10.0%'),
                ('Receivables',                                 2350.0,     2250.0,     '4.4%'),
                ('Current Assets',                              400.0,      0.0,        'n/a'),
                ('Prepayments',                                 -3600.0,    -2500.0,    '44.0%'),
                ('Total Current Assets',                        -4150.0,    -3250.0,    '27.7%'),
                ('Plus Fixed Assets',                           0.0,        0.0,        'n/a'),
                ('Plus Non-current Assets',                     4200.0,     3500.0,     '20.0%'),
                ('Total ASSETS',                                50.0,       250.0,      '-80.0%'),

                ('LIABILITIES',                                 -200.0,     0.0,        'n/a'),
                ('Current Liabilities',                         -200.0,     0.0,        'n/a'),
                ('Current Liabilities',                         0.0,        0.0,        'n/a'),
                ('Payables',                                    -200.0,     0.0,        'n/a'),
                ('Total Current Liabilities',                   -200.0,     0.0,        'n/a'),
                ('Plus Non-current Liabilities',                0.0,        0.0,        'n/a'),
                ('Total LIABILITIES',                           -200.0,     0.0,        'n/a'),

                ('EQUITY',                                      250.0,      250.0,      '0.0%'),
                ('Unallocated Earnings',                        -550.0,     250.0,      '-320.0%'),
                ('Current Year Unallocated Earnings',           -800.0,     250.0,      '-420.0%'),
                ('Current Year Earnings',                       0.0,        250.0,      '-100.0%'),
                ('Current Year Allocated Earnings',             -800.0,     0.0,        'n/a'),
                ('Total Current Year Unallocated Earnings',     -800.0,     250.0,      '-420.0%'),
                ('Previous Years Unallocated Earnings',         250.0,      0.0,        'n/a'),
                ('Total Unallocated Earnings',                  -550.0,     250.0,      '-320.0%'),
                ('Retained Earnings',                           800.0,      0.0,        'n/a'),
                ('Total EQUITY',                                250.0,      250.0,      '0.0%'),

                ('LIABILITIES + EQUITY',                        50.0,       250.0,      '-80.0%'),
            ],
        )

        self.assertLinesValues(
            self.report._get_lines(options, line_id=line_id),
            #   Name                                            Balance     Comparison  %
            [   0,                                              1,          2,          3],
            [
                ('Bank and Cash Accounts',                      -3300.0,    -3000.0,    '10.0%'),
                ('code102 account102',                          -2000.0,    -2000.0,    '0.0%'),
                ('code2 account2',                              -1300.0,    -1000.0,    '30.0%'),
                ('Total Bank and Cash Accounts',                -3300.0,    -3000.0,    '10.0%'),
            ],
        )

    def test_financial_report_custom_filters(self):
        line_id = self._build_generic_id_from_financial_line('account_reports.account_financial_report_receivable0')
        options = self._init_options(self.report, fields.Date.from_string('2019-01-01'), fields.Date.from_string('2019-12-31'))
        options = self._update_comparison_filter(options, self.report, 'custom', 1, date_to=fields.Date.from_string('2018-12-31'))
        options = self._update_multi_selector_filter(options, 'ir_filters', self.filter.ids)
        options['unfolded_lines'] = [line_id]

        headers, lines = self.report._get_table(options)
        self.assertHeadersValues(headers, [
            [   ('', 1),                                                ('As of 12/31/2019',  3),                                   ('As of 12/31/2018', 3)],
            [   ('', 1),                                    ('2017-01-01', 1),  ('2018-01-01', 1),  ('2019-01-01', 1),  ('2017-01-01', 1),  ('2018-01-01', 1),  ('2019-01-01', 1)],
            [   ('', 1),                                    ('partner_a', 1),   ('partner_a', 1),   ('partner_a', 1),   ('partner_a', 1),   ('partner_a', 1),   ('partner_a', 1)],
        ])
        self.assertLinesValues(
            lines,
            [   0,                                          1,                  2,                  3,                  4,                  5,                  6],
            [
                ('ASSETS',                                  4500.0,             1250.0,             1150.0,             4500.0,             1250.0,             0.0),
                ('Current Assets',                          1000.0,             1250.0,             450.0,              1000.0,             1250.0,             0.0),
                ('Bank and Cash Accounts',                  0.0,                0.0,                0.0,                0.0,                0.0,                0.0),
                ('Receivables',                             1000.0,             1250.0,             50.0,               1000.0,             1250.0,             0.0),
                ('code0 account0',                          0.0,                1250.0,             50.0,               0.0,                1250.0,             0.0),
                ('code100 account100',                      1000.0,             0.0,                0.0,                1000.0,             0.0,                0.0),
                ('Total Receivables',                       1000.0,             1250.0,             50.0,               1000.0,             1250.0,             0.0),
                ('Current Assets',                          0.0,                0.0,                400.0,              0.0,                0.0,                0.0),
                ('Prepayments',                             0.0,                0.0,                0.0,                0.0,                0.0,                0.0),
                ('Total Current Assets',                    1000.0,             1250.0,             450.0,              1000.0,             1250.0,             0.0),
                ('Plus Fixed Assets',                       0.0,                0.0,                0.0,                0.0,                0.0,                0.0),
                ('Plus Non-current Assets',                 3500.0,             0.0,                700.0,              3500.0,             0.0,                0.0),
                ('Total ASSETS',                            4500.0,             1250.0,             1150.0,             4500.0,             1250.0,             0.0),

                ('LIABILITIES',                             0.0,                0.0,                0.0,                0.0,                0.0,                0.0),
                ('Current Liabilities',                     0.0,                0.0,                0.0,                0.0,                0.0,                0.0),
                ('Current Liabilities',                     0.0,                0.0,                0.0,                0.0,                0.0,                0.0),
                ('Payables',                                0.0,                0.0,                0.0,                0.0,                0.0,                0.0),
                ('Total Current Liabilities',               0.0,                0.0,                0.0,                0.0,                0.0,                0.0),
                ('Plus Non-current Liabilities',            0.0,                0.0,                0.0,                0.0,                0.0,                0.0),
                ('Total LIABILITIES',                       0.0,                0.0,                0.0,                0.0,                0.0,                0.0),

                ('EQUITY',                                  0.0,                250.0,              0.0,                0.0,                250.0,              0.0),
                ('Unallocated Earnings',                    0.0,                250.0,              0.0,                0.0,                250.0,              0.0),
                ('Current Year Unallocated Earnings',       0.0,                0.0,                0.0,                0.0,                250.0,              0.0),
                ('Current Year Earnings',                   0.0,                0.0,                0.0,                0.0,                250.0,              0.0),
                ('Current Year Allocated Earnings',         0.0,                0.0,                0.0,                0.0,                0.0,                0.0),
                ('Total Current Year Unallocated Earnings', 0.0,                0.0,                0.0,                0.0,                250.0,              0.0),
                ('Previous Years Unallocated Earnings',     0.0,                250.0,              0.0,                0.0,                0.0,                0.0),
                ('Total Unallocated Earnings',              0.0,                250.0,              0.0,                0.0,                250.0,              0.0),
                ('Retained Earnings',                       0.0,                0.0,                0.0,                0.0,                0.0,                0.0),
                ('Total EQUITY',                            0.0,                250.0,              0.0,                0.0,                250.0,              0.0),

                ('LIABILITIES + EQUITY',                    0.0,                250.0,              0.0,                0.0,                250.0,              0.0),
            ],
        )

        self.assertLinesValues(
            self.report._get_lines(options, line_id=line_id),
            [   0,                                          1,                  2,                  3,                  4,                  5,                  6],
            [
                ('Receivables',                             1000.0,             1250.0,             50.0,               1000.0,             1250.0,             0.0),
                ('code0 account0',                          0.0,                1250.0,             50.0,               0.0,                1250.0,             0.0),
                ('code100 account100',                      1000.0,             0.0,                0.0,                1000.0,             0.0,                0.0),
                ('Total Receivables',                       1000.0,             1250.0,             50.0,               1000.0,             1250.0,             0.0),
            ],
        )

    def test_financial_report_control_domain(self):
        def check_missing_exceeding(lines, missing, excess):
            map_missing = {line['id']: line.get('has_missing') for line in lines}
            map_excess = {line['id']: line.get('has_excess') for line in lines}
            for line_id in map_missing:
                if line_id in missing:
                    self.assertTrue(map_missing[line_id], line_id)
                else:
                    self.assertFalse(map_missing[line_id], line_id)
            for line_id in map_excess:
                if line_id in excess:
                    self.assertTrue(map_excess[line_id], line_id)
                else:
                    self.assertFalse(map_excess[line_id], line_id)

        options = self._init_options(self.report, fields.Date.from_string('2019-01-01'), fields.Date.from_string('2019-12-31'))
        options['unfold_all'] = True
        options.pop('multi_company', None)

        # Activate debug mode to enable control domain feature
        with self.debug_mode(self.report):

            # 1. Test for each scenario separately
            report_line = self.env.ref('account_reports.account_financial_report_current_assets_view0')
            line_id_current_assets = self.env['account.financial.html.report']._get_generic_line_id(
                'account.financial.html.report.line',
                report_line.id,
            )

            # 1.0. Base case : no control domain
            lines = self.report._get_table(options)[1]
            check_missing_exceeding(lines, {}, {})

            # 1.1. Base case : nothing missing or in excess
            report_line.control_domain = OR([ast.literal_eval(ustr(line.domain)) for line in report_line.children_ids])
            lines = self.report._get_table(options)[1]
            check_missing_exceeding(lines, {}, {})

            # 1.2. Excess journal items
            report_line.control_domain = "[('account_id', '=', False)]"
            lines = self.report._get_table(options)[1]
            check_missing_exceeding(lines, {}, {line_id_current_assets})

            # 1.3. Missing journal items
            report_line.control_domain = "[('account_id', '!=', False)]"
            lines = self.report._get_table(options)[1]
            check_missing_exceeding(lines, {line_id_current_assets}, {})

            # 2. Test for both missing and excess journal items
            report_line = self.env.ref('account_reports.account_financial_unaffected_earnings0')
            line_id_unaffected_earnings = self.env['account.financial.html.report']._get_generic_line_id(
                'account.financial.html.report.line',
                report_line.id,
            )

            report_line.control_domain = "[('account_id', '!=', False)]"
            lines = self.report._get_table(options)[1]
            check_missing_exceeding(lines, {line_id_current_assets, line_id_unaffected_earnings}, {line_id_unaffected_earnings})

    def test_financial_report_sum_if_x_groupby(self):
        account1 = self.env['account.account'].create({
            'name': "test_financial_report_sum_if_x_groupby1",
            'code': "42241",
            'user_type_id': self.env.ref('account.data_account_type_fixed_assets').id,
        })
        account2 = self.env['account.account'].create({
            'name': "test_financial_report_sum_if_x_groupby2",
            'code': "42242",
            'user_type_id': self.env.ref('account.data_account_type_fixed_assets').id,
        })

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2019-01-01',
            'line_ids': [
                # pylint: disable=C0326
                (0, 0, {'debit': 1000.0,    'credit': 0.0,          'account_id': account1.id}),
                (0, 0, {'debit': 0.0,       'credit': 10000.0,      'account_id': account1.id}),

                (0, 0, {'debit': 50000.0,   'credit': 0.0,          'account_id': account2.id}),
                (0, 0, {'debit': 0.0,       'credit': 5000.0,       'account_id': account2.id}),

                (0, 0, {'debit': 0.0,       'credit': 36000.0,      'account_id': self.company_data['default_account_revenue'].id}),
            ],
        })
        move.action_post()

        report = self.env["account.financial.html.report"].create({
            'name': "test_financial_report_sum_if_x_groupby",
            'unfold_all_filter': True,
            'line_ids': [
                (0, 0, {
                    'name': "report_line_1",
                    'code': 'TEST_L1',
                    'level': 1,
                    'domain': [('account_id', 'in', (account1 + account2).ids)],
                    'groupby': 'account_id',
                    'formulas': 'sum_if_pos_groupby',
                }),
                (0, 0, {
                    'name': "report_line_2",
                    'code': 'TEST_L2',
                    'level': 1,
                    'domain': [('account_id', 'in', (account1 + account2).ids)],
                    'groupby': 'account_id',
                    'formulas': '-sum_if_neg_groupby',
                }),
                (0, 0, {
                    'name': "report_line_3",
                    'code': 'TEST_L3',
                    'level': 1,
                    'domain': [('account_id', 'in', (account1 + account2).ids)],
                    'groupby': 'account_id',
                    'formulas': 'sum_if_pos',
                }),
                (0, 0, {
                    'name': "report_line_4",
                    'code': 'TEST_L4',
                    'level': 1,
                    'domain': [('account_id', 'in', (account1 + account2).ids)],
                    'groupby': 'account_id',
                    'formulas': '-sum_if_neg',
                }),
            ],
        })
        options = self._init_options(report, fields.Date.from_string('2019-01-01'), fields.Date.from_string('2019-01-01'))
        options['unfold_all'] = True

        self.assertLinesValues(
            # pylint: disable=C0326
            report._get_table(options)[1],
            [   0,                          1],
            [
                ("report_line_1",           45000.0),
                (account2.display_name,     45000.0),
                ("Total report_line_1",     45000.0),
                ("report_line_2",           9000.0),
                (account1.display_name,     9000.0),
                ("Total report_line_2",     9000.0),
                ("report_line_3",           36000.0),
                (account1.display_name,     -9000.0),
                (account2.display_name,     45000.0),
                ("Total report_line_3",     36000.0),
                ("report_line_4",           0.0),
            ],
        )

    def test_hide_if_zero_with_no_formulas(self):
        """
        Check if a report line stays displayed when hide_if_zero is True and no formulas
        is set on the line but has some child which have balance != 0
        We check also if the line is hidden when all its children have balance == 0
        """
        account1, account2 = self.env['account.account'].create([{
            'name': "test_financial_report_1",
            'code': "42241",
            'user_type_id': self.env.ref('account.data_account_type_fixed_assets').id,
        }, {
            'name': "test_financial_report_2",
            'code': "42242",
            'user_type_id': self.env.ref('account.data_account_type_fixed_assets').id,
        }])

        moves = self.env['account.move'].create([
            {
                'move_type': 'entry',
                'date': '2019-04-01',
                'line_ids': [
                    (0, 0, {'debit': 3.0, 'credit': 0.0, 'account_id': account1.id}),
                    (0, 0, {'debit': 0.0, 'credit': 3.0, 'account_id': self.company_data['default_account_revenue'].id}),
                ],
            },
            {
                'move_type': 'entry',
                'date': '2019-05-01',
                'line_ids': [
                    (0, 0, {'debit': 0.0, 'credit': 1.0, 'account_id': account2.id}),
                    (0, 0, {'debit': 1.0, 'credit': 0.0, 'account_id': self.company_data['default_account_revenue'].id}),
                ],
            },
            {
                'move_type': 'entry',
                'date': '2019-04-01',
                'line_ids': [
                    (0, 0, {'debit': 0.0, 'credit': 3.0, 'account_id': account2.id}),
                    (0, 0, {'debit': 3.0, 'credit': 0.0, 'account_id': self.company_data['default_account_revenue'].id}),
                ],
            },
        ])
        moves.action_post()

        report = self.env["account.financial.html.report"].create({
            'name': "test_financial_report_sum",
            'unfold_all_filter': True,
            'line_ids': [
                (0, 0, {
                    'name': "Title",
                    'code': 'TT',
                    'level': 1,
                    'hide_if_zero': True,
                    'children_ids': [
                        (0, 0, {
                            'name': "report_line_1",
                            'code': 'TEST_L1',
                            'level': 2,
                            'domain': [('account_id', '=', account1.id)],
                            'groupby': 'account_id',
                            'formulas': 'sum',
                        }),
                        (0, 0, {
                            'name': "report_line_2",
                            'code': 'TEST_L2',
                            'level': 2,
                            'domain': [('account_id', '=', account2.id)],
                            'groupby': 'account_id',
                            'formulas': 'sum',
                        }),
                    ]
                }),
            ],
        })

        options = self._init_options(report, fields.Date.from_string('2019-05-01'), fields.Date.from_string('2019-05-01'))
        options = self._update_comparison_filter(options, report, 'previous_period', 2)
        options['unfolded_lines'] = report.line_ids.ids

        expected_values = [
            # pylint: disable=C0326
            ("Title",              '',      '',     ''),
            ("report_line_1",     3.0,     3.0,    0.0),
            ("report_line_2",    -4.0,    -3.0,    0.0),
            ("Total Title",        '',      '',     ''),
        ]

        self.assertLinesValues(report._get_table(options)[1], [0, 1, 2, 3], expected_values)

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2019-05-01',
            'line_ids': [
                (0, 0, {'debit': 1.0, 'credit': 0.0, 'account_id': account1.id}),
                (0, 0, {'debit': 0.0, 'credit': 1.0, 'account_id': self.company_data['default_account_revenue'].id}),
            ],
        })

        move.action_post()

        self.assertLinesValues(report._get_table(options)[1], [0, 1, 2, 3], [])

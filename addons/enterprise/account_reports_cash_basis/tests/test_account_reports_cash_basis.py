# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo import fields

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@tagged('post_install', '-at_install')
class TestAccountReports(TestAccountReportsCommon):

    @classmethod
    def _reconcile_on(cls, lines, account):
        lines.filtered(lambda line: line.account_id == account and not line.reconciled).reconcile()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.liquidity_journal_1 = cls.company_data['default_journal_bank']
        cls.liquidity_account = cls.liquidity_journal_1.default_account_id
        cls.receivable_account_1 = cls.company_data['default_account_receivable']
        cls.revenue_account_1 = cls.company_data['default_account_revenue']

        # Invoice having two receivable lines on the same account.

        invoice = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': cls.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 345.0,     'credit': 0.0,      'account_id': cls.receivable_account_1.id}),
                (0, 0, {'debit': 805.0,     'credit': 0.0,      'account_id': cls.receivable_account_1.id}),
                (0, 0, {'debit': 0.0,       'credit': 1150.0,   'account_id': cls.revenue_account_1.id}),
            ],
        })
        invoice.action_post()

        # First payment (20% of the invoice).

        payment_1 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-02-01',
            'journal_id': cls.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,       'credit': 230.0,    'account_id': cls.receivable_account_1.id}),
                (0, 0, {'debit': 230.0,     'credit': 0.0,      'account_id': cls.liquidity_account.id}),
            ],
        })
        payment_1.action_post()

        cls._reconcile_on((invoice + payment_1).line_ids, cls.receivable_account_1)

        # Second payment (also 20% but will produce two partials, one on each receivable line).

        payment_2 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-03-01',
            'journal_id': cls.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,       'credit': 230.0,    'account_id': cls.receivable_account_1.id}),
                (0, 0, {'debit': 230.0,     'credit': 0.0,      'account_id': cls.liquidity_account.id}),
            ],
        })
        payment_2.action_post()

        cls._reconcile_on((invoice + payment_2).line_ids, cls.receivable_account_1)

    def test_general_ledger_cash_basis(self):
        # Check the cash basis option.
        self.env['res.currency'].search([('name', '!=', 'USD')]).active = False
        report = self.env['account.general.ledger']
        options = self._init_options(report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-12-31'))
        options['cash_basis'] = True
        report = report.with_context(report._set_context(options))

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                            Debit       Credit      Balance
            [   0,                              4,          5,          6],
            [
                # Accounts.
                ('101404 Bank',                 460.0,      0.0,        460.0),
                ('121000 Account Receivable',   460.0,      460.0,      0.0),
                ('400000 Product Sales',        0.0,        460.0,      -460.0),
                # Report Total.
                ('Total',                       920.0,      920.0,     0.0),
            ],
        )

        # Mark the '101200 Account Receivable' line to be unfolded.
        line_id = lines[1]['id']
        options['unfolded_lines'] = [line_id]
        options['cash_basis'] = False  # Because we are in the same transaction, the table temp_account_move_line still exists
        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            # pylint: disable=C0326
            #   Name                                    Date            Debit           Credit          Balance
            [   0,                                      1,                    4,             5,             6],
            [
                # Account.
                ('121000 Account Receivable',           '',              460.00,        460.00,          0.00),
                ('Initial Balance',                     '',                0.00,          0.00,          0.00),
                # Account Move Lines.
                ('MISC/2016/01/0001',                   '02/01/2016',     69.00,            '',         69.00),
                ('MISC/2016/01/0001',                   '02/01/2016',    161.00,            '',        230.00),
                ('BNK1/2016/02/0001',                   '02/01/2016',        '',        230.00,          0.00),
                ('MISC/2016/01/0001',                   '03/01/2016',     34.50,            '',         34.50),
                ('MISC/2016/01/0001',                   '03/01/2016',     34.50,            '',         69.00),
                ('MISC/2016/01/0001',                   '03/01/2016',     80.50,            '',        149.50),
                ('MISC/2016/01/0001',                   '03/01/2016',     80.50,            '',        230.00),
                ('BNK1/2016/03/0001',                   '03/01/2016',        '',        230.00,          0.00),
                # Account Total.
                ('Total 121000 Account Receivable',     '',              460.00,        460.00,          0.00),
            ],
        )

    def test_balance_sheet_cash_basis(self):
        # Check the cash basis option.
        report = self.env.ref('account_reports.account_financial_report_balancesheet0')
        options = self._init_options(report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-12-31'))
        options['cash_basis'] = True
        report = report.with_context(report._set_context(options))

        self.assertLinesValues(
            report._get_table(options)[1],
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('ASSETS',                                      460.0),
                ('Current Assets',                              460.0),
                ('Bank and Cash Accounts',                      460.0),
                ('Receivables',                                 0.0),
                ('Current Assets',                              0.0),
                ('Prepayments',                                 0.0),
                ('Total Current Assets',                        460.0),
                ('Plus Fixed Assets',                           0.0),
                ('Plus Non-current Assets',                     0.0),
                ('Total ASSETS',                                460.0),

                ('LIABILITIES',                                 0.0),
                ('Current Liabilities',                         0.0),
                ('Current Liabilities',                         0.0),
                ('Payables',                                    0.0),
                ('Total Current Liabilities',                   0.0),
                ('Plus Non-current Liabilities',                0.0),
                ('Total LIABILITIES',                           0.0),

                ('EQUITY',                                      460.0),
                ('Unallocated Earnings',                        460.0),
                ('Current Year Unallocated Earnings',           460.0),
                ('Current Year Earnings',                       460.0),
                ('Current Year Allocated Earnings',             0.0),
                ('Total Current Year Unallocated Earnings',     460.0),
                ('Previous Years Unallocated Earnings',         0.0),
                ('Total Unallocated Earnings',                  460.0),
                ('Retained Earnings',                           0.0),
                ('Total EQUITY',                                460.0),

                ('LIABILITIES + EQUITY',                        460.0),
            ],
        )

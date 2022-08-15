# -*- coding: utf-8 -*-
from unittest.mock import patch

from .common import TestAccountReportsCommon

from odoo import fields
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestGeneralLedgerReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # Entries in 2016 for company_1 to test the initial balance.
        cls.move_2016_1 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2016-01-01'),
            'journal_id': cls.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 100.0,     'credit': 0.0,      'name': '2016_1_1',     'account_id': cls.company_data['default_account_payable'].id}),
                (0, 0, {'debit': 200.0,     'credit': 0.0,      'name': '2016_1_2',     'account_id': cls.company_data['default_account_expense'].id}),
                (0, 0, {'debit': 0.0,       'credit': 300.0,    'name': '2016_1_3',     'account_id': cls.company_data['default_account_revenue'].id}),
            ],
        })
        cls.move_2016_1.action_post()

        # Entries in 2016 for company_2 to test the initial balance in multi-companies/multi-currencies.
        cls.move_2016_2 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2016-06-01'),
            'journal_id': cls.company_data_2['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 100.0,     'credit': 0.0,      'name': '2016_2_1',     'account_id': cls.company_data_2['default_account_payable'].id}),
                (0, 0, {'debit': 0.0,       'credit': 100.0,    'name': '2016_2_2',     'account_id': cls.company_data_2['default_account_revenue'].id}),
            ],
        })
        cls.move_2016_2.action_post()

        # Entry in 2017 for company_1 to test the report at current date.
        cls.move_2017_1 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2017-01-01'),
            'journal_id': cls.company_data['default_journal_sale'].id,
            'line_ids': [
                (0, 0, {'debit': 1000.0,    'credit': 0.0,      'name': '2017_1_1',     'account_id': cls.company_data['default_account_receivable'].id}),
                (0, 0, {'debit': 2000.0,    'credit': 0.0,      'name': '2017_1_2',     'account_id': cls.company_data['default_account_revenue'].id}),
                (0, 0, {'debit': 3000.0,    'credit': 0.0,      'name': '2017_1_3',     'account_id': cls.company_data['default_account_revenue'].id}),
                (0, 0, {'debit': 4000.0,    'credit': 0.0,      'name': '2017_1_4',     'account_id': cls.company_data['default_account_revenue'].id}),
                (0, 0, {'debit': 5000.0,    'credit': 0.0,      'name': '2017_1_5',     'account_id': cls.company_data['default_account_revenue'].id}),
                (0, 0, {'debit': 6000.0,    'credit': 0.0,      'name': '2017_1_6',     'account_id': cls.company_data['default_account_revenue'].id}),
                (0, 0, {'debit': 0.0,       'credit': 6000.0,   'name': '2017_1_7',     'account_id': cls.company_data['default_account_expense'].id}),
                (0, 0, {'debit': 0.0,       'credit': 7000.0,   'name': '2017_1_8',     'account_id': cls.company_data['default_account_expense'].id}),
                (0, 0, {'debit': 0.0,       'credit': 8000.0,   'name': '2017_1_9',     'account_id': cls.company_data['default_account_expense'].id}),
            ],
        })
        cls.move_2017_1.action_post()

        # Entry in 2017 for company_2 to test the current period in multi-companies/multi-currencies.
        cls.move_2017_2 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2017-06-01'),
            'journal_id': cls.company_data_2['default_journal_bank'].id,
            'line_ids': [
                (0, 0, {'debit': 400.0,     'credit': 0.0,      'name': '2017_2_1',     'account_id': cls.company_data_2['default_account_expense'].id}),
                (0, 0, {'debit': 0.0,       'credit': 400.0,    'name': '2017_2_2',     'account_id': cls.company_data_2['default_account_revenue'].id}),
            ],
        })
        cls.move_2017_2.action_post()

        # Archive 'default_journal_bank' to ensure archived entries are not filtered out.
        cls.company_data_2['default_journal_bank'].active = False
        # Deactive all currencies to ensure group_multi_currency is disabled.
        cls.env['res.currency'].search([('name', '!=', 'USD')]).active = False

    # -------------------------------------------------------------------------
    # TESTS: General Ledger
    # -------------------------------------------------------------------------

    def test_general_ledger_unfold_1_whole_report(self):
        ''' Test unfolding a line when rendering the whole report. '''
        report = self.env['account.general.ledger']
        line_id = 'account_%s' % self.company_data['default_account_revenue'].id
        options = self._init_options(report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))
        options['unfolded_lines'] = [line_id]

        self.assertLinesValues(
            # pylint: disable=C0326
            report._get_lines(options),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      4,              5,              6],
            [
                ('121000 Account Receivable',           1000.0,         0.0,            1000.0),
                ('211000 Account Payable',              100.0,          0.0,            100.0),
                ('211000 Account Payable',              50.0,           0.0,            50.0),
                ('400000 Product Sales',                20000.0,        0.0,            20000.0),
                ('Initial Balance',                     0.0,            0.0,            0.0),
                ('INV/2017/00001',                      2000.0,         '',             2000.0),
                ('INV/2017/00001',                      3000.0,         '',             5000.0),
                ('INV/2017/00001',                      4000.0,         '',             9000.0),
                ('INV/2017/00001',                      5000.0,         '',             14000.0),
                ('INV/2017/00001',                      6000.0,         '',             20000.0),
                ('Total 400000 Product Sales',          20000.0,        0.0,            20000.0),
                ('400000 Product Sales',                0.0,            200.0,          -200.0),
                ('600000 Expenses',                     0.0,            21000.0,        -21000.0),
                ('600000 Expenses',                     200.0,          0.0,            200.0),
                ('999999 Undistributed Profits/Losses', 200.0,          300.0,          -100.0),
                ('999999 Undistributed Profits/Losses', 0.0,            50.0,           -50.0),
                ('Total',                               21550.0,        21550.0,        0.0),
            ],
        )

    def test_general_ledger_unfold_2_folded_line(self):
        ''' Test unfolding a line when "clicking" on a folded line. '''
        report = self.env['account.general.ledger']
        line_id = 'account_%s' % self.company_data['default_account_revenue'].id
        options = self._init_options(report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))
        options['unfolded_lines'] = [line_id]

        self.assertLinesValues(
            # pylint: disable=C0326
            report._get_lines(options, line_id=line_id),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      4,              5,              6],
            [
                ('400000 Product Sales',                20000.0,        0.0,            20000.0),
                ('Initial Balance',                     0.0,            0.0,            0.0),
                ('INV/2017/00001',                      2000.0,         '',             2000.0),
                ('INV/2017/00001',                      3000.0,         '',             5000.0),
                ('INV/2017/00001',                      4000.0,         '',             9000.0),
                ('INV/2017/00001',                      5000.0,         '',             14000.0),
                ('INV/2017/00001',                      6000.0,         '',             20000.0),
                ('Total 400000 Product Sales',          20000.0,        0.0,            20000.0),
            ],
        )

    def test_general_ledger_unfold_3_load_more(self):
        ''' Test unfolding a line to use the load more. '''
        report = self.env['account.general.ledger']
        line_id = 'account_%s' % self.company_data['default_account_revenue'].id
        options = self._init_options(report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))
        options['unfolded_lines'] = [line_id]

        with patch.object(type(report), 'MAX_LINES', 2):
            report_lines = report._get_lines(options, line_id=line_id)
            self.assertLinesValues(
                # pylint: disable=C0326
                report_lines,
                #   Name                                    Debit           Credit          Balance
                [   0,                                      4,              5,              6],
                [
                    ('400000 Product Sales',                20000.0,        0.0,            20000.0),
                    ('Initial Balance',                     0.0,            0.0,            0.0),
                    ('INV/2017/00001',                      2000.0,         '',             2000.0),
                    ('INV/2017/00001',                      3000.0,         '',             5000.0),
                    ('Load more... (3 remaining)',          '',             '',             ''),
                    ('Total 400000 Product Sales',          20000.0,        0.0,            20000.0),
                ],
            )

            line_id = report_lines[4]['id']
            options['unfolded_lines'] = [line_id]
            options.update({
                'lines_offset': report_lines[4]['offset'],
                'lines_progress': report_lines[4]['progress'],
                'lines_remaining': report_lines[4]['remaining'],
            })

            report_lines = report._get_lines(options, line_id=line_id)
            self.assertLinesValues(
                # pylint: disable=C0326
                report_lines,
                #   Name                                    Debit           Credit          Balance
                [   0,                                      4,              5,              6],
                [
                    ('INV/2017/00001',                      4000.0,         '',             9000.0),
                    ('INV/2017/00001',                      5000.0,         '',             14000.0),
                    ('Load more... (1 remaining)',          '',             '',             ''),
                ],
            )

            line_id = report_lines[2]['id']
            options['unfolded_lines'] = [line_id]
            options.update({
                'lines_offset': report_lines[2]['offset'],
                'lines_progress': report_lines[2]['progress'],
                'lines_remaining': report_lines[2]['remaining'],
            })

            report_lines = report._get_lines(options, line_id=line_id)
            self.assertLinesValues(
                # pylint: disable=C0326
                report_lines,
                #   Name                                    Debit           Credit          Balance
                [   0,                                      4,              5,              6],
                [
                    ('INV/2017/00001',                      6000.0,         '',             20000.0),
                ],
            )

    def test_general_ledger_foreign_currency_account(self):
        ''' Ensure the total in foreign currency of an account is displayed only if all journal items are sharing the
        same currency.
        '''
        self.env.user.groups_id |= self.env.ref('base.group_multi_currency')

        foreign_curr_account = self.env['account.account'].create({
            'name': "foreign_curr_account",
            'code': "test",
            'user_type_id': self.env.ref('account.data_account_type_current_liabilities').id,
            'currency_id': self.currency_data['currency'].id,
            'company_id': self.company_data['company'].id,
        })

        move_2016 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.company_data['default_journal_sale'].id,
            'line_ids': [
                (0, 0, {
                    'name': 'curr_1',
                    'debit': 100.0,
                    'credit': 0.0,
                    'amount_currency': 100.0,
                    'currency_id': self.company_data['currency'].id,
                    'account_id': self.company_data['default_account_receivable'].id,
                }),
                (0, 0, {
                    'name': 'curr_2',
                    'debit': 0.0,
                    'credit': 100.0,
                    'amount_currency': -300.0,
                    'currency_id': self.currency_data['currency'].id,
                    'account_id': foreign_curr_account.id,
                }),
            ],
        })
        move_2016.action_post()

        move_2017 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2017-01-01',
            'journal_id': self.company_data['default_journal_sale'].id,
            'line_ids': [
                (0, 0, {
                    'name': 'curr_1',
                    'debit': 1000.0,
                    'credit': 0.0,
                    'amount_currency': 1000.0,
                    'currency_id': self.company_data['currency'].id,
                    'account_id': self.company_data['default_account_receivable'].id,
                }),
                (0, 0, {
                    'name': 'curr_2',
                    'debit': 0.0,
                    'credit': 1000.0,
                    'amount_currency': -2000.0,
                    'currency_id': self.currency_data['currency'].id,
                    'account_id': foreign_curr_account.id,
                }),
            ],
        })
        move_2017.action_post()

        # Init options.
        report = self.env['account.general.ledger']
        line_id = 'account_%s' % foreign_curr_account.id
        options = self._init_options(report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))
        options['unfolded_lines'] = [line_id]

        self.assertLinesValues(
            # pylint: disable=C0326
            report._get_lines(options),
            #   Name                                    Amount_currency Debit           Credit          Balance
            [   0,                                      4,              5,              6,              7],
            [
                ('121000 Account Receivable',           '',             2100.0,         0.0,            2100.0),
                ('211000 Account Payable',              '',             100.0,          0.0,            100.0),
                ('211000 Account Payable',              '',             50.0,           0.0,            50.0),
                ('400000 Product Sales',                '',             20000.0,        0.0,            20000.0),
                ('400000 Product Sales',                '',             0.0,            200.0,          -200.0),
                ('600000 Expenses',                     '',             0.0,            21000.0,        -21000.0),
                ('600000 Expenses',                     '',             200.0,          0.0,            200.0),
                ('999999 Undistributed Profits/Losses', '',             200.0,          300.0,          -100.0),
                ('999999 Undistributed Profits/Losses', '',             0.0,            50.0,           -50.0),
                ('test foreign_curr_account',           -2300.0,        0.0,            1100.0,         -1100.0),
                ('Initial Balance',                     -300.0,         0.0,            100.0,          -100.0),
                ('INV/2017/00002',                      -2000.0,        '',             1000.0,         -1100.0),
                ('Total test foreign_curr_account',     -2300.0,        0.0,            1100.0,         -1100.0),
                ('Total',                               '',             22650.0,        22650.0,        0.0),
            ],
            currency_map={4: {'currency': self.currency_data['currency']}},
        )

    def test_general_ledger_filter_accounts(self):
        """ Test when a user filter on an account """
        # Init options.
        report = self.env['account.general.ledger']
        options = self._init_options(report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))
        options['filter_accounts'] = '40'
        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      4,              5,              6],
            [
                ('400000 Product Sales',                20000.0,        0.0,            20000.0),
                ('400000 Product Sales',                0.0,            200.0,          -200.0),
                ('Total',                               20000.0,        200.0,          19800.0),
            ],
        )

        options['filter_accounts'] = '9999'
        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      4,              5,              6],
            [
                ('999999 Undistributed Profits/Losses', 200.0,          300.0,          -100.0),
                ('999999 Undistributed Profits/Losses', 0.0,            50.0,           -50.0),
                ('Total',                               200.0,          350.0,          -150.0),
            ],
        )

    # -------------------------------------------------------------------------
    # TESTS: Trial Balance
    # -------------------------------------------------------------------------

    def test_trial_balance_whole_report(self):
        report = self.env['account.coa.report']
        options = self._init_options(report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))

        self.assertLinesValues(
            report._get_lines(options),
            #                                           [  Initial Balance   ]          [       Balance      ]          [       Total        ]
            #   Name                                    Debit           Credit          Debit           Credit          Debit           Credit
            [   0,                                      1,              2,              3,              4,              5,              6],
            [
                ('121000 Account Receivable',           '',             '',             1000.0,         '',             1000.0,         ''),
                ('211000 Account Payable',              100.0,          '',             '',             '',             100.0,          ''),
                ('211000 Account Payable',              50.0,           '',             '',             '',             50.0,           ''),
                ('400000 Product Sales',                '',             '',             20000.0,        '',             20000.0,        ''),
                ('400000 Product Sales',                '',             '',             '',             200.0,          '',             200.0),
                ('600000 Expenses',                     '',             '',             '',             21000.0,        '',             21000.0),
                ('600000 Expenses',                     '',             '',             200.0,          '',             200.0,          ''),
                ('999999 Undistributed Profits/Losses', '',             100.0,          '',             '',             '',             100.0),
                ('999999 Undistributed Profits/Losses', '',             50.0,           '',             '',             '',             50.0),
                ('Total',                               150.0,          150.0,          21200.0,        21200.0,        21350.0,        21350.0),
            ],
        )

    def test_trial_balance_filter_journals(self):
        report = self.env['account.coa.report']
        options = self._init_options(report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))
        options = self._update_multi_selector_filter(options, 'journals', self.company_data['default_journal_sale'].ids)

        self.assertLinesValues(
            report._get_lines(options),
            #                                           [  Initial Balance   ]          [       Balance      ]          [       Total        ]
            #   Name                                    Debit           Credit          Debit           Credit          Debit           Credit
            [   0,                                      1,              2,              3,              4,              5,              6],
            [
                ('121000 Account Receivable',           '',             '',             1000.0,         '',             1000.0,         ''),
                ('400000 Product Sales',                '',             '',             20000.0,        '',             20000.0,        ''),
                ('600000 Expenses',                     '',             '',             '',             21000.0,        '',             21000.0),
                ('Total',                               0.0,            0.0,            21000.0,        21000.0,        21000.0,        21000.0),
            ],
        )

    def test_trial_balance_comparisons(self):
        report = self.env['account.coa.report']
        options = self._init_options(report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))
        options = self._update_comparison_filter(options, report, 'previous_period', 1)

        self.assertLinesValues(
            report._get_lines(options),
            #                                           [  Initial Balance   ]          [        2016        ]          [        2017        ]          [       Total        ]
            #   Name                                    Debit           Credit          Debit           Credit          Debit           Credit          Debit           Credit
            [   0,                                      1,              2,              3,              4,              5,              6,              7,              8],
            [
                ('121000 Account Receivable',           '',             '',             '',             '',             1000.0,         '',             1000.0,         ''),
                ('211000 Account Payable',              '',             '',             100.0,          '',             '',             '',             100.0,          ''),
                ('211000 Account Payable',              '',             '',             50.0,           '',             '',             '',             50.0,           ''),
                ('400000 Product Sales',                '',             '',             '',             300.0,          20000.0,        '',             19700.0,        ''),
                ('400000 Product Sales',                '',             '',             '',             50.0,           '',             200.0,          '',             250.0),
                ('600000 Expenses',                     '',             '',             200.0,          '',             '',             21000.0,        '',             20800.0),
                ('600000 Expenses',                     '',             '',             '',             '',             200.0,          '',             200.0,          ''),
                ('Total',                               0.0,            0.0,            350.0,          350.0,          21200.0,        21200.0,        21050.0,        21050.0),
            ],
        )

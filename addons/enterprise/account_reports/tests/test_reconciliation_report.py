# -*- coding: utf-8 -*-
# pylint: disable=C0326
from freezegun import freeze_time

from .common import TestAccountReportsCommon
from odoo import fields
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestReconciliationReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.currency_data_2 = cls.setup_multi_currency_data({
            'name': 'Dark Chocolate Coin',
            'symbol': '🍫',
            'currency_unit_label': 'Dark Choco',
            'currency_subunit_label': 'Dark Cacao Powder',
        }, rate2016=10.0, rate2017=20.0)

    def test_reconciliation_report_single_currency(self):
        ''' Tests the impact of positive/negative payments/statements on the reconciliation report in a single-currency
        environment.
        '''

        bank_journal = self.env['account.journal'].create({
            'name': 'Bank',
            'code': 'BNKKK',
            'type': 'bank',
            'company_id': self.company_data['company'].id,
        })

        # ==== Statements ====

        statement_1 = self.env['account.bank.statement'].create({
            'name': 'statement_1',
            'date': '2014-12-31',
            'balance_start': 0.0,
            'balance_end_real': 100.0,
            'journal_id': bank_journal.id,
            'line_ids': [
                (0, 0, {'payment_ref': 'line_1',    'amount': 600.0,    'date': '2014-12-31'}),
                (0, 0, {'payment_ref': 'line_2',    'amount': -500.0,   'date': '2014-12-31'}),
            ],
        })

        statement_2 = self.env['account.bank.statement'].create({
            'name': 'statement_2',
            'date': '2015-01-05',
            'balance_start': 200.0, # create an unexplained difference of 100.0.
            'balance_end_real': -200.0,
            'journal_id': bank_journal.id,
            'line_ids': [
                (0, 0, {'payment_ref': 'line_1',    'amount': 100.0,    'date': '2015-01-01',   'partner_id': self.partner_a.id}),
                (0, 0, {'payment_ref': 'line_2',    'amount': 200.0,    'date': '2015-01-02'}),
                (0, 0, {'payment_ref': 'line_3',    'amount': -300.0,   'date': '2015-01-03',   'partner_id': self.partner_a.id}),
                (0, 0, {'payment_ref': 'line_4',    'amount': -400.0,   'date': '2015-01-04'}),
            ],
        })

        (statement_1 + statement_2).button_post()

        # ==== Payments ====

        payment_1 = self.env['account.payment'].create({
            'amount': 150.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'date': '2015-01-01',
            'journal_id': bank_journal.id,
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.inbound_payment_method_line.id,
        })

        payment_2 = self.env['account.payment'].create({
            'amount': 250.0,
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'date': '2015-01-02',
            'journal_id': bank_journal.id,
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.outbound_payment_method_line.id,
        })

        payment_3 = self.env['account.payment'].create({
            'amount': 350.0,
            'payment_type': 'outbound',
            'partner_type': 'customer',
            'date': '2015-01-03',
            'journal_id': bank_journal.id,
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.inbound_payment_method_line.id,
        })

        payment_4 = self.env['account.payment'].create({
            'amount': 450.0,
            'payment_type': 'inbound',
            'partner_type': 'supplier',
            'date': '2015-01-04',
            'journal_id': bank_journal.id,
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.outbound_payment_method_line.id,
        })

        (payment_1 + payment_2 + payment_3 + payment_4).action_post()

        # ==== Reconciliation ====

        st_line = statement_2.line_ids.filtered(lambda line: line.payment_ref == 'line_1')
        payment_line = payment_1.line_ids.filtered(lambda line: line.account_id == bank_journal.company_id.account_journal_payment_debit_account_id)
        st_line.reconcile([{'id': payment_line.id}])

        st_line = statement_2.line_ids.filtered(lambda line: line.payment_ref == 'line_3')
        payment_line = payment_2.line_ids.filtered(lambda line: line.account_id == bank_journal.company_id.account_journal_payment_credit_account_id)
        st_line.reconcile([{'id': payment_line.id}])

        # ==== Report ====

        report = self.env['account.bank.reconciliation.report'].with_context(active_id=bank_journal.id)

        # report._get_lines() makes SQL queries without flushing
        report.flush()

        with freeze_time('2016-01-02'):

            options = report._get_options(None)

            self.assertLinesValues(
                report._get_lines(options),
                #   Name                                                            Date            Amount
                [   0,                                                              1,              3],
                [
                    ('Balance of 101405 Bank',                                      '01/02/2016',   -300.0),

                    ('Including Unreconciled Bank Statement Receipts',              '',             800.0),
                    ('BNKKK/2015/01/0002',                                          '01/02/2015',   200.0),
                    ('BNKKK/2014/12/0001',                                          '12/31/2014',   600.0),
                    ('Total Including Unreconciled Bank Statement Receipts',        '',             800.0),

                    ('Including Unreconciled Bank Statement Payments',              '',             -900.0),
                    ('BNKKK/2015/01/0004',                                          '01/04/2015',   -400.0),
                    ('BNKKK/2014/12/0002',                                          '12/31/2014',   -500.0),
                    ('Total Including Unreconciled Bank Statement Payments',        '',             -900.0),

                    ('Total Balance of 101405 Bank',                                '01/02/2016',   -300.0),

                    ('Outstanding Payments/Receipts',                               '',             100.0),

                    ('(+) Outstanding Receipts',                                    '',             450.0),
                    ('BNKKK/2015/01/0008',                                          '01/04/2015',   450.0),
                    ('Total (+) Outstanding Receipts',                              '',             450.0),

                    ('(-) Outstanding Payments',                                    '',             -350.0),
                    ('BNKKK/2015/01/0007',                                          '01/03/2015',   -350.0),
                    ('Total (-) Outstanding Payments',                              '',             -350.0),

                    ('Total Outstanding Payments/Receipts',                         '',             100.0),
                ],
                currency_map={3: {'currency': bank_journal.currency_id}},
            )

    def test_reconciliation_report_multi_currencies(self):
        ''' Tests the management of multi-currencies in the reconciliation report. '''
        self.env.user.groups_id |= self.env.ref('base.group_multi_currency')
        self.env.user.groups_id |= self.env.ref('base.group_no_one')

        company_currency = self.company_data['currency']
        journal_currency = self.currency_data['currency']
        choco_currency = self.currency_data_2['currency']

        # ==== Journal with a foreign currency ====

        bank_journal = self.env['account.journal'].create({
            'name': 'Bank',
            'code': 'BNKKK',
            'type': 'bank',
            'company_id': self.company_data['company'].id,
            'currency_id': journal_currency.id
        })

        # ==== Statement ====

        statement = self.env['account.bank.statement'].create({
            'name': 'statement',
            'date': '2016-01-01',
            'journal_id': bank_journal.id,
            'line_ids': [

                # Transaction in the company currency.
                (0, 0, {
                    'payment_ref': 'line_1',
                    'amount': 100.0,
                    'amount_currency': 50.01,
                    'foreign_currency_id': company_currency.id,
                }),

                # Transaction in a third currency.
                (0, 0, {
                    'payment_ref': 'line_3',
                    'amount': 100.0,
                    'amount_currency': 999.99,
                    'foreign_currency_id': choco_currency.id,
                }),

            ],
        })
        statement.button_post()

        # ==== Payments ====

        # Payment in the company's currency.
        payment_1 = self.env['account.payment'].create({
            'amount': 1000.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'date': '2016-01-01',
            'journal_id': bank_journal.id,
            'partner_id': self.partner_a.id,
            'currency_id': company_currency.id,
            'payment_method_line_id': self.inbound_payment_method_line.id,
        })
        payment_1.action_post()

        # Payment in the same foreign currency as the journal.
        payment_2 = self.env['account.payment'].create({
            'amount': 2000.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'date': '2016-01-01',
            'journal_id': bank_journal.id,
            'partner_id': self.partner_a.id,
            'currency_id': journal_currency.id,
            'payment_method_line_id': self.inbound_payment_method_line.id,
        })
        payment_2.action_post()

        # Payment in a third foreign currency.
        payment_3 = self.env['account.payment'].create({
            'amount': 3000.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'date': '2016-01-01',
            'journal_id': bank_journal.id,
            'partner_id': self.partner_a.id,
            'currency_id': choco_currency.id,
            'payment_method_line_id': self.inbound_payment_method_line.id,
        })
        payment_3.action_post()

        # ==== Report ====

        report = self.env['account.bank.reconciliation.report'].with_context(active_id=bank_journal.id)

        # report._get_lines() makes SQL queries without flushing
        report.flush()

        with freeze_time('2016-01-02'), self.debug_mode(report):

            options = report._get_options(None)
            lines = report._get_lines(options)

            self.assertLinesValues(
                lines,
                #   Name                                                            Date            Amount  Currency                Amount
                [   0,                                                              1,              3,      4,                      5],
                [
                    ('Balance of 101405 Bank',                                      '01/02/2016',   '',     '',                     200.0),

                    ('Including Unreconciled Bank Statement Receipts',              '',             '',     '',                     200.0),
                    ('BNKKK/2016/01/0002',                                          '01/01/2016',   999.99, choco_currency.name,    100.0),
                    ('BNKKK/2016/01/0001',                                          '01/01/2016',   50.01,  company_currency.name,  100.0),
                    ('Total Including Unreconciled Bank Statement Receipts',        '',             '',     '',                     200.0),

                    ('Total Balance of 101405 Bank',                                '01/02/2016',   '',     '',                     200.0),

                    ('Outstanding Payments/Receipts',                               '',             '',     '',                     5900.0),

                    ('(+) Outstanding Receipts',                                    '',             '',     '',                     5900.0),
                    ('BNKKK/2016/01/0005',                                          '01/01/2016',   3000.0, choco_currency.name,    900.0),
                    ('BNKKK/2016/01/0004',                                          '01/01/2016',   '',     '',                     2000.0),
                    ('BNKKK/2016/01/0003',                                          '01/01/2016',   1000.0, company_currency.name,  3000.0),
                    ('Total (+) Outstanding Receipts',                              '',             '',     '',                     5900.0),

                    ('Total Outstanding Payments/Receipts',                         '',             '',     '',                     5900.0),
                ],
                currency_map={
                    3: {'currency_code_index': 4},
                    5: {'currency': journal_currency},
                },
            )

    def test_reconciliation_change_date(self):
        ''' Tests the impact of positive/negative payments/statements on the reconciliation report in a single-currency
        environment.
        '''
        bank_journal = self.company_data['default_journal_bank']

        statement = self.env['account.bank.statement'].create({
            'name': 'statement_1',
            'date': '2019-01-10',
            'balance_start': 0.0,
            'balance_end_real': 130.0,
            'journal_id': bank_journal.id,
            'line_ids': [
                (0, 0, {'payment_ref': 'line_1',    'amount': 10.0,     'date': '2019-01-01'}),
                (0, 0, {'payment_ref': 'line_2',    'amount': 20.0,     'date': '2019-01-02'}),
                (0, 0, {'payment_ref': 'line_3',    'amount': 30.0,     'date': '2019-01-03'}),
                (0, 0, {'payment_ref': 'line_4',    'amount': -40.0,    'date': '2019-01-04'}),
                (0, 0, {'payment_ref': 'line_5',    'amount': 50.0,     'date': '2019-01-05'}),
                (0, 0, {'payment_ref': 'line_6',    'amount': 60.0,     'date': '2019-01-06'}),
            ],
        })

        # Ensure all move names are computed.
        statement.button_post()
        statement.button_reopen()
        statement['balance_end_real'] = 140.0

        payment = self.env['account.payment'].create({
            'amount': 1000.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'date': '2019-01-03',
            'journal_id': bank_journal.id,
            'partner_id': self.partner_a.id,
        })
        payment.action_post()

        # report._get_lines() makes SQL queries without flushing
        statement.flush()
        report = self.env['account.bank.reconciliation.report'].with_context(active_id=bank_journal.id)

        options = self._init_options(report, fields.Date.from_string('2019-01-01'), fields.Date.from_string('2019-01-01'))
        options['all_entries'] = True
        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                                            Date            Amount
            [   0,                                                              1,              3],
            [
                ('Balance of 101404 Bank',                                      '01/01/2019',   10.0),

                ('Including Unreconciled Bank Statement Receipts',              '',             10.0),
                ('BNK1/2019/01/0001',                                           '01/01/2019',   10.0),
                ('Total Including Unreconciled Bank Statement Receipts',        '',             10.0),

                ('Total Balance of 101404 Bank',                                '01/01/2019',   10.0),
            ],
            currency_map={3: {'currency': bank_journal.currency_id}},
        )

        options = self._init_options(report, fields.Date.from_string('2019-01-01'), fields.Date.from_string('2019-01-04'))
        options['all_entries'] = True
        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                                            Date            Amount
            [   0,                                                              1,              3],
            [
                ('Balance of 101404 Bank',                                      '01/04/2019',   20.0),

                ('Including Unreconciled Bank Statement Receipts',              '',             60.0),
                ('BNK1/2019/01/0001',                                           '01/01/2019',   10.0),
                ('BNK1/2019/01/0002',                                           '01/02/2019',   20.0),
                ('BNK1/2019/01/0003',                                           '01/03/2019',   30.0),
                ('Total Including Unreconciled Bank Statement Receipts',        '',             60.0),

                ('Including Unreconciled Bank Statement Payments',              '',             -40.0),
                ('BNK1/2019/01/0004',                                           '01/04/2019',   -40.0),
                ('Total Including Unreconciled Bank Statement Payments',        '',             -40.0),

                ('Total Balance of 101404 Bank',                                '01/04/2019',   20.0),

                ('Outstanding Payments/Receipts',                               '',             1000.0),
                ('(+) Outstanding Receipts',                                    '',             1000.0),
                ('BNK1/2019/01/0007',                                           '01/03/2019',   1000.0),
                ('Total (+) Outstanding Receipts',                              '',             1000.0),
                ('Total Outstanding Payments/Receipts',                         '',             1000.0),

            ],
            currency_map={3: {'currency': bank_journal.currency_id}},
        )

    def test_reconciliation_report_non_statement_payment(self):
        ''' Test that moves not linked to a bank statement/payment but linked for example to expanses are used in the
        report
        '''

        bank_journal = self.env['account.journal'].create({
            'name': 'Bank',
            'code': 'BNKKK',
            'type': 'bank',
            'company_id': self.company_data['company'].id,
        })

        # ==== Misc ====

        self.env['account.move'].create({
            'journal_id': bank_journal.id,
            'date': '2014-12-31',
            'line_ids': [
                (0, 0, {
                    'name': 'Source',
                    'debit': 800,
                    'credit': 0,
                    'account_id': self.company_data['default_account_expense'].id,
                }),
                (0, 0, {
                    'name': 'Destination',
                    'debit': 0,
                    'credit': 800,
                    'account_id': bank_journal.company_id.account_journal_payment_credit_account_id.id,
                }),
            ]
        }).action_post()

        # ==== Report ====

        report = self.env['account.bank.reconciliation.report'].with_context(active_id=bank_journal.id)

        # report._get_lines() makes SQL queries without flushing
        report.flush()

        with freeze_time('2016-01-02'):

            options = report._get_options()

            self.assertLinesValues(
                report._get_lines(options),
                #   Name                                                            Date            Amount
                [   0,                                                              1,              3],
                [
                    ('Balance of 101405 Bank',                                      '01/02/2016',   0.0),

                    ('Total Balance of 101405 Bank',                                '01/02/2016',   0.0),

                    ('Outstanding Payments/Receipts',                               '',             -800.0),

                    ('(-) Outstanding Payments',                                    '',             -800.0),
                    ('BNKKK/2014/12/0001',                                          '12/31/2014',   -800.0),
                    ('Total (-) Outstanding Payments',                              '',             -800.0),

                    ('Total Outstanding Payments/Receipts',                         '',             -800.0),
                ],
                currency_map={3: {'currency': bank_journal.currency_id}},
            )

# -*- coding: utf-8 -*-
from unittest.mock import patch

from .common import TestAccountReportsCommon

from odoo import fields
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestPartnerLedgerReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.partner_category_a = cls.env['res.partner.category'].create({'name': 'partner_categ_a'})
        cls.partner_category_b = cls.env['res.partner.category'].create({'name': 'partner_categ_b'})

        cls.partner_a = cls.env['res.partner'].create(
            {'name': 'partner_a', 'company_id': False, 'category_id': [(6, 0, [cls.partner_category_a.id, cls.partner_category_b.id])]})
        cls.partner_b = cls.env['res.partner'].create(
            {'name': 'partner_b', 'company_id': False, 'category_id': [(6, 0, [cls.partner_category_a.id])]})
        cls.partner_c = cls.env['res.partner'].create(
            {'name': 'partner_c', 'company_id': False, 'category_id': [(6, 0, [cls.partner_category_b.id])]})

        # Entries in 2016 for company_1 to test the initial balance.
        cls.move_2016_1 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2016-01-01'),
            'journal_id': cls.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 100.0,     'credit': 0.0,      'name': '2016_1_1',     'account_id': cls.company_data['default_account_payable'].id,       'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 200.0,     'credit': 0.0,      'name': '2016_1_1',     'account_id': cls.company_data['default_account_payable'].id,       'partner_id': cls.partner_b.id}),
                (0, 0, {'debit': 0.0,       'credit': 300.0,    'name': '2016_1_2',     'account_id': cls.company_data['default_account_receivable'].id,    'partner_id': cls.partner_c.id}),
            ],
        })
        cls.move_2016_1.action_post()

        # Entries in 2016 for company_2 to test the initial balance in multi-companies/multi-currencies.
        cls.move_2016_2 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2016-06-01'),
            'journal_id': cls.company_data_2['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 100.0,     'credit': 0.0,      'name': '2016_2_1',     'account_id': cls.company_data_2['default_account_payable'].id,     'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 0.0,       'credit': 100.0,    'name': '2016_2_2',     'account_id': cls.company_data_2['default_account_receivable'].id,  'partner_id': cls.partner_c.id}),
            ],
        })
        cls.move_2016_2.action_post()

        # Entry in 2017 for company_1 to test the report at current date.
        cls.move_2017_1 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2017-01-01'),
            'journal_id': cls.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 1000.0,    'credit': 0.0,      'name': '2017_1_1',     'account_id': cls.company_data['default_account_payable'].id,       'partner_id': cls.partner_b.id}),
                (0, 0, {'debit': 2000.0,    'credit': 0.0,      'name': '2017_1_2',     'account_id': cls.company_data['default_account_payable'].id,       'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 3000.0,    'credit': 0.0,      'name': '2017_1_3',     'account_id': cls.company_data['default_account_payable'].id,       'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 4000.0,    'credit': 0.0,      'name': '2017_1_4',     'account_id': cls.company_data['default_account_receivable'].id,    'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 5000.0,    'credit': 0.0,      'name': '2017_1_5',     'account_id': cls.company_data['default_account_receivable'].id,    'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 6000.0,    'credit': 0.0,      'name': '2017_1_6',     'account_id': cls.company_data['default_account_receivable'].id,    'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 0.0,       'credit': 6000.0,   'name': '2017_1_7',     'account_id': cls.company_data['default_account_receivable'].id,    'partner_id': cls.partner_c.id}),
                (0, 0, {'debit': 0.0,       'credit': 7000.0,   'name': '2017_1_8',     'account_id': cls.company_data['default_account_receivable'].id,    'partner_id': cls.partner_c.id}),
                (0, 0, {'debit': 0.0,       'credit': 8000.0,   'name': '2017_1_9',     'account_id': cls.company_data['default_account_receivable'].id,    'partner_id': cls.partner_c.id}),
            ],
        })
        cls.move_2017_1.action_post()

        # Entry in 2017 for company_2 to test the current period in multi-companies/multi-currencies.
        cls.move_2017_2 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2017-06-01'),
            'journal_id': cls.company_data_2['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 400.0,     'credit': 0.0,      'name': '2017_2_1',     'account_id': cls.company_data_2['default_account_receivable'].id}),
                (0, 0, {'debit': 0.0,       'credit': 400.0,    'name': '2017_2_2',     'account_id': cls.company_data_2['default_account_receivable'].id}),
            ],
        })
        cls.move_2017_2.action_post()
        # Deactive all currencies to ensure group_multi_currency is disabled.
        cls.env['res.currency'].search([('name', '!=', 'USD')]).active = False

    def test_partner_ledger_unfold_1_whole_report(self):
        ''' Test unfolding a line when rendering the whole report. '''
        report = self.env['account.partner.ledger']
        line_id = 'partner_%s' % self.partner_a.id
        options = self._init_options(report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))
        options['unfolded_lines'] = [line_id]

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                    Init. Balance   Debit           Credit          Balance
            [   0,                                      6,              7,              8,              9],
            [
                ('partner_a',                           150.0,          20000.0,        0.0,            20150.0),
                ('01/01/2017',                          150.0,          2000.0,         '',             2150.0),
                ('01/01/2017',                          2150.0,         3000.0,         '',             5150.0),
                ('01/01/2017',                          5150.0,         4000.0,         '',             9150.0),
                ('01/01/2017',                          9150.0,         5000.0,         '',             14150.0),
                ('01/01/2017',                          14150.0,        6000.0,         '',             20150.0),
                ('partner_b',                           200.0,          1000.0,         0.0,            1200.0),
                ('partner_c',                           -350.0,         0.0,            21000.0,        -21350.0),
                ('Unknown Partner',                     0.0,            200.0,          200.0,          0.0),
                ('Total',                               0.0,            21200.0,        21200.0,        0.0),
            ],
        )

    def test_partner_ledger_unfold_2_folded_line(self):
        ''' Test unfolding a line when "clicking" on a folded line. '''
        report = self.env['account.partner.ledger']
        line_id = 'partner_%s' % self.partner_a.id
        options = self._init_options(report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))
        options['unfolded_lines'] = [line_id]

        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            #   Name                                    Init. Balance   Debit           Credit          Balance
            [   0,                                      6,              7,              8,              9],
            [
                ('partner_a',                           150.0,          20000.0,        0.0,            20150.0),
                ('01/01/2017',                          150.0,          2000.0,         '',             2150.0),
                ('01/01/2017',                          2150.0,         3000.0,         '',             5150.0),
                ('01/01/2017',                          5150.0,         4000.0,         '',             9150.0),
                ('01/01/2017',                          9150.0,         5000.0,         '',             14150.0),
                ('01/01/2017',                          14150.0,        6000.0,         '',             20150.0),
            ],
        )

    def test_partner_ledger_unfold_3_load_more(self):
        ''' Test unfolding a line to use the load more. '''
        report = self.env['account.partner.ledger']
        line_id = 'partner_%s' % self.partner_a.id
        options = self._init_options(report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))
        options['unfolded_lines'] = [line_id]

        with patch.object(type(report), 'MAX_LINES', 2):
            report_lines = report._get_lines(options, line_id=line_id)
            self.assertLinesValues(
                report_lines,
                #   Name                                    Init. Balance   Debit           Credit          Balance
                [   0,                                      6,              7,              8,              9],
                [
                    ('partner_a',                           150.0,          20000.0,        0.0,            20150.0),
                    ('01/01/2017',                          150.0,          2000.0,         '',             2150.0),
                    ('01/01/2017',                          2150.0,         3000.0,         '',             5150.0),
                    ('Load more... (3 remaining)',          '',             '',             '',             ''),
                ],
            )

            line_id = report_lines[3]['id']
            options['unfolded_lines'] = [line_id]
            options.update({
                'lines_offset': report_lines[3]['offset'],
                'lines_progress': report_lines[3]['progress'],
                'lines_remaining': report_lines[3]['remaining'],
            })

            report_lines = report._get_lines(options, line_id=line_id)
            self.assertLinesValues(
                report_lines,
                #   Name                                    Init. Balance   Debit           Credit          Balance
                [   0,                                      6,              7,              8,              9],
                [
                    ('01/01/2017',                          5150.0,         4000.0,         '',             9150.0),
                    ('01/01/2017',                          9150.0,         5000.0,         '',             14150.0),
                    ('Load more... (1 remaining)',          '',             '',             '',             ''),
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
                report_lines,
                #   Name                                    Init. Balance   Debit           Credit          Balance
                [   0,                                      6,              7,              8,              9],
                [
                    ('01/01/2017',                          14150.0,        6000.0,         '',             20150.0),
                ],
            )

    def test_partner_ledger_filter_account_types(self):
        ''' Test building the report with a filter on account types.
        When filtering on receivable accounts, partner_b should disappear from the report.
        '''
        report = self.env['account.partner.ledger']
        line_id = 'partner_%s' % self.partner_a.id
        options = self._init_options(report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))
        options['unfolded_lines'] = [line_id]
        options = self._update_multi_selector_filter(options, 'account_type', ['receivable'])

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                    Init. Balance   Debit           Credit          Balance
            [   0,                                      6,              7,              8,              9],
            [
                ('partner_a',                           0.0,            15000.0,        0.0,            15000.0),
                ('01/01/2017',                          0.0,            4000.0,         '',             4000.0),
                ('01/01/2017',                          4000.0,         5000.0,         '',             9000.0),
                ('01/01/2017',                          9000.0,         6000.0,         '',             15000.0),
                ('partner_c',                           -350.0,         0.0,            21000.0,        -21350.0),
                ('Unknown Partner',                     0.0,            200.0,          200.0,          0.0),
                ('Total',                               -350.0,         15200.0,        21200.0,        -6350.0),
            ],
        )

    def test_partner_ledger_filter_partners(self):
        ''' Test the filter on top allowing to filter on res.partner.'''
        report = self.env['account.partner.ledger']
        options = self._init_options(report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))
        options['partner_ids'] = (self.partner_a + self.partner_c).ids

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                    Init. Balance   Debit           Credit          Balance
            [   0,                                      6,              7,              8,              9],
            [
                ('partner_a',                           150.0,          20000.0,        0.0,            20150.0),
                ('partner_c',                           -350.0,         0.0,            21000.0,        -21350.0),
                ('Total',                               -200.0,         20000.0,        21000.0,        -1200.0),
            ],
        )

    def test_partner_ledger_filter_partner_categories(self):
        ''' Test the filter on top allowing to filter on res.partner.category.'''
        report = self.env['account.partner.ledger']
        options = self._init_options(report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))
        options['partner_categories'] = self.partner_category_a.ids

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                    Init. Balance   Debit           Credit          Balance
            [   0,                                      6,              7,              8,              9],
            [
                ('partner_a',                           150.0,          20000.0,        0.0,            20150.0),
                ('partner_b',                           200.0,          1000.0,         0.0,            1200.0),
                ('Total',                               350.0,          21000.0,        0.0,            21350.0),
            ],
        )

    def test_partner_ledger_unknown_partner(self):
        ''' Test the partner ledger for whennever a line appearing in it has no partner assigned. Check that
        reconciling this line with an invoice/bill of a partner does effect his balance.
        '''
        report = self.env['account.partner.ledger']
        options = self._init_options(report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))

        misc_move = self.env['account.move'].create({
            'date': '2017-03-31',
            'line_ids': [
                (0, 0, {'debit': 1000.0, 'credit': 0.0, 'account_id': self.company_data['default_account_revenue'].id}),
                (0, 0, {'debit': 0.0, 'credit': 1000.0, 'account_id': self.company_data['default_account_receivable'].id}),
            ],
        })
        misc_move.action_post()

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                    Init. Balance   Debit           Credit          Balance
            [   0,                                      6,              7,              8,              9],
            [
                ('partner_a',                           150.0,          20000.0,        0.0,            20150.0),
                ('partner_b',                           200.0,          1000.0,         0.0,            1200.0),
                ('partner_c',                           -350.0,         0.0,            21000.0,        -21350.0),
                ('Unknown Partner',                     0.0,            200.0,          1200.0,         -1000.0),
                ('Total',                               0.0,            21200.0,        22200.0,        -1000.0),
            ],
        )

        debit_line = self.move_2017_1.line_ids.filtered(lambda line: line.debit == 4000.0)
        credit_line = misc_move.line_ids.filtered(lambda line: line.credit == 1000.0)
        (debit_line + credit_line).reconcile()

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                    Init. Balance   Debit           Credit          Balance
            [   0,                                      6,              7,              8,              9],
            [
                ('partner_a',                           150.0,          20000.0,        1000.0,         19150.0),
                ('partner_b',                           200.0,          1000.0,         0.0,            1200.0),
                ('partner_c',                           -350.0,         0.0,            21000.0,        -21350.0),
                ('Unknown Partner',                     0.0,            1200.0,         1200.0,         0.0),
                ('Total',                               0.0,            22200.0,        23200.0,        -1000.0),
            ],
        )

        # Mark the 'partner_a' line to be unfolded.
        line_id = lines[0]['id']
        options['unfolded_lines'] = [line_id]

        lines = report._get_lines(options)
        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            #   Name                                    Init. Balance   Debit           Credit          Balance
            [   0,                                      6,              7,              8,              9],
            [
                ('partner_a',                           150.0,          20000.0,        1000.0,         19150.0),
                ('01/01/2017',                          150.0,          2000.0,         '',             2150.0),
                ('01/01/2017',                          2150.0,         3000.0,         '',             5150.0),
                ('01/01/2017',                          5150.0,         4000.0,         '',             9150.0),
                ('01/01/2017',                          9150.0,         5000.0,         '',             14150.0),
                ('01/01/2017',                          14150.0,        6000.0,         '',             20150.0),
                ('03/31/2017',                          20150.0,        '',             1000.0,         19150.0),
            ],
        )

        # Mark the 'unknown partner' line to be unfolded.
        line_id = lines[-2]['id']
        options['unfolded_lines'] = [line_id]

        lines = report._get_lines(options)
        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            #   Name                                    Init. Balance   Debit           Credit          Balance
            [   0,                                      6,              7,              8,              9],
            [
                ('Unknown Partner',                     0.0,            1200.0,         1200.0,         0.0),
                ('03/31/2017',                          0.0,            '',             1000.0,         -1000.0),
                ('06/01/2017',                          -1000.0,        200.0,          '',             -800.0),
                ('06/01/2017',                          -800.0,         '',             200.0,          -1000.0),
                ('03/31/2017',                          -1000.0,        1000.0,         '',             0.0),
            ],
        )

        # change the dates to exclude the reconciliation max date: situation is back to the beginning
        options = self._init_options(report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-03-30'))

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                    Init. Balance   Debit           Credit          Balance
            [   0,                                      6,              7,              8,              9],
            [
                ('partner_a',                           150.0,          20000.0,        0.0,            20150.0),
                ('partner_b',                           200.0,          1000.0,         0.0,            1200.0),
                ('partner_c',                           -350.0,         0.0,            21000.0,        -21350.0),
                ('Total',                               0.0,            21000.0,        21000.0,        0.0),
            ],
        )

        #change the dates to have a date_from > to the reconciliation max date and check the initial balances are correct
        options = self._init_options(report, fields.Date.from_string('2017-04-01'), fields.Date.from_string('2017-04-01'))
        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                    Init. Balance   Debit           Credit          Balance
            [   0,                                      6,              7,              8,              9],
            [
                ('partner_a',                           19150.0,        0.0,            0.0,            19150.0),
                ('partner_b',                           1200.0,         0.0,            0.0,            1200.0),
                ('partner_c',                           -21350.0,       0.0,            0.0,            -21350.0),
                ('Unknown Partner',                     0.0,            0.0,            0.0,            0.0),
                ('Total',                               -1000.0,        0.0,            0.0,            -1000.0),
            ],
        )

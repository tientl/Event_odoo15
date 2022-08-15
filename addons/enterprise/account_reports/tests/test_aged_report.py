# -*- coding: utf-8 -*-
from .common import TestAccountReportsCommon

from odoo import fields
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAgedReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.partner_category_a = cls.env['res.partner.category'].create({'name': 'partner_categ_a'})
        cls.partner_category_b = cls.env['res.partner.category'].create({'name': 'partner_categ_b'})

        cls.partner_a = cls.env['res.partner'].create({'name': 'partner_a', 'company_id': False, 'category_id': [(6, 0, [cls.partner_category_a.id, cls.partner_category_b.id])]})
        cls.partner_b = cls.env['res.partner'].create({'name': 'partner_b', 'company_id': False, 'category_id': [(6, 0, [cls.partner_category_a.id])]})

        receivable_1 = cls.company_data['default_account_receivable']
        receivable_2 = cls.company_data['default_account_receivable'].copy()
        receivable_3 = cls.company_data['default_account_receivable'].copy()
        receivable_4 = cls.company_data_2['default_account_receivable']
        receivable_5 = cls.company_data_2['default_account_receivable'].copy()
        receivable_6 = cls.company_data_2['default_account_receivable'].copy()
        misc_1 = cls.company_data['default_account_revenue']
        misc_2 = cls.company_data_2['default_account_revenue']

        # Test will use the following dates:
        # As of                  2017-02-01
        # 1 - 30:   2017-01-31 - 2017-01-02
        # 31 - 60:  2017-01-01 - 2016-12-03
        # 61 - 90:  2016-12-02 - 2016-11-03
        # 91 - 120: 2016-11-02 - 2016-10-04
        # Older:    2016-10-03

        # ==== Journal entries in company_1 for partner_a ====

        move_1 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2016-11-03'),
            'journal_id': cls.company_data['default_journal_sale'].id,
            'line_ids': [
                # 1000.0 in 61 - 90.
                (0, 0, {'debit': 1000.0,    'credit': 0.0,      'date_maturity': False,         'account_id': receivable_1.id,      'partner_id': cls.partner_a.id}),
                # -800.0 in 31 - 60
                (0, 0, {'debit': 0.0,       'credit': 800.0,    'date_maturity': '2017-01-01',  'account_id': receivable_2.id,      'partner_id': cls.partner_a.id}),
                # Ignored line.
                (0, 0, {'debit': 0.0,       'credit': 200.0,    'date_maturity': False,         'account_id': misc_1.id,            'partner_id': cls.partner_a.id}),
            ],
        })

        move_2 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2016-10-05'),
            'journal_id': cls.company_data['default_journal_sale'].id,
            'line_ids': [
                # -200.0 in 61 - 90
                (0, 0, {'debit': 0.0,       'credit': 200.0,    'date_maturity': '2016-12-02',  'account_id': receivable_1.id,      'partner_id': cls.partner_a.id}),
                # -300.0 in 31 - 60
                (0, 0, {'debit': 0.0,       'credit': 300.0,    'date_maturity': '2016-12-03',  'account_id': receivable_1.id,      'partner_id': cls.partner_a.id}),
                # 1000.0 in 91 - 120
                (0, 0, {'debit': 1000.0,    'credit': 0.0,      'date_maturity': False,         'account_id': receivable_2.id,      'partner_id': cls.partner_a.id}),
                # 100.0 in all dates
                (0, 0, {'debit': 100.0,     'credit': 0.0,      'date_maturity': '2017-02-01',  'account_id': receivable_3.id,      'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 100.0,     'credit': 0.0,      'date_maturity': '2017-01-02',  'account_id': receivable_3.id,      'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 100.0,     'credit': 0.0,      'date_maturity': '2016-12-03',  'account_id': receivable_3.id,      'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 100.0,     'credit': 0.0,      'date_maturity': '2016-11-03',  'account_id': receivable_3.id,      'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 100.0,     'credit': 0.0,      'date_maturity': '2016-10-04',  'account_id': receivable_3.id,      'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 100.0,     'credit': 0.0,      'date_maturity': '2016-01-01',  'account_id': receivable_3.id,      'partner_id': cls.partner_a.id}),
                # Ignored line.
                (0, 0, {'debit': 0.0,       'credit': 1100.0,   'date_maturity': '2016-10-05',  'account_id': misc_1.id,            'partner_id': cls.partner_a.id}),
            ],
        })
        (move_1 + move_2).action_post()
        (move_1 + move_2).line_ids.filtered(lambda line: line.account_id == receivable_1).reconcile()
        (move_1 + move_2).line_ids.filtered(lambda line: line.account_id == receivable_2).reconcile()

        # ==== Journal entries in company_2 for partner_b ====

        move_3 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2016-11-03'),
            'journal_id': cls.company_data_2['default_journal_sale'].id,
            'line_ids': [
                # 1000.0 in 61 - 90.
                (0, 0, {'debit': 1000.0,    'credit': 0.0,      'date_maturity': False,         'account_id': receivable_4.id,      'partner_id': cls.partner_b.id}),
                # -200.0 in 31 - 60
                (0, 0, {'debit': 0.0,       'credit': 800.0,    'date_maturity': '2017-01-01',  'account_id': receivable_5.id,      'partner_id': cls.partner_b.id}),
                # Ignored line.
                (0, 0, {'debit': 0.0,       'credit': 200.0,    'date_maturity': False,         'account_id': misc_2.id,            'partner_id': cls.partner_b.id}),
            ],
        })

        move_4 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2016-10-05'),
            'journal_id': cls.company_data_2['default_journal_sale'].id,
            'line_ids': [
                # -200.0 in 61 - 90
                (0, 0, {'debit': 0.0,       'credit': 200.0,    'date_maturity': '2016-12-02',  'account_id': receivable_4.id,      'partner_id': cls.partner_b.id}),
                # -300.0 in 31 - 60
                (0, 0, {'debit': 0.0,       'credit': 300.0,    'date_maturity': '2016-12-03',  'account_id': receivable_4.id,      'partner_id': cls.partner_b.id}),
                # 1000.0 in 91 - 120
                (0, 0, {'debit': 1000.0,    'credit': 0.0,      'date_maturity': False,         'account_id': receivable_5.id,      'partner_id': cls.partner_b.id}),
                # 100.0 in all dates
                (0, 0, {'debit': 100.0,     'credit': 0.0,      'date_maturity': '2017-02-01',  'account_id': receivable_6.id,      'partner_id': cls.partner_b.id}),
                (0, 0, {'debit': 100.0,     'credit': 0.0,      'date_maturity': '2017-01-02',  'account_id': receivable_6.id,      'partner_id': cls.partner_b.id}),
                (0, 0, {'debit': 100.0,     'credit': 0.0,      'date_maturity': '2016-12-03',  'account_id': receivable_6.id,      'partner_id': cls.partner_b.id}),
                (0, 0, {'debit': 100.0,     'credit': 0.0,      'date_maturity': '2016-11-03',  'account_id': receivable_6.id,      'partner_id': cls.partner_b.id}),
                (0, 0, {'debit': 100.0,     'credit': 0.0,      'date_maturity': '2016-10-04',  'account_id': receivable_6.id,      'partner_id': cls.partner_b.id}),
                (0, 0, {'debit': 100.0,     'credit': 0.0,      'date_maturity': '2016-01-01',  'account_id': receivable_6.id,      'partner_id': cls.partner_b.id}),
                # Ignored line.
                (0, 0, {'debit': 0.0,       'credit': 1100.0,   'date_maturity': False,         'account_id': misc_2.id,            'partner_id': cls.partner_b.id}),
            ],
        })
        (move_3 + move_4).action_post()
        (move_3 + move_4).line_ids.filtered(lambda line: line.account_id == receivable_4).reconcile()
        (move_3 + move_4).line_ids.filtered(lambda line: line.account_id == receivable_5).reconcile()
        cls.env['res.currency'].search([('name', '!=', 'USD')]).active = False
        company_ids = (cls.company_data['company'] + cls.company_data_2['company']).ids
        cls.report = cls.env['account.aged.receivable'].with_context(allowed_company_ids=company_ids)

    def test_aged_receivable_unfold_1_whole_report(self):
        ''' Test unfolding a line when rendering the whole report. '''
        line_id = 'partner_id-res.partner-%s' % self.partner_a.id
        options = self._init_options(self.report, fields.Date.from_string('2017-02-01'), fields.Date.from_string('2017-02-01'))
        options['unfolded_lines'] = [line_id]

        report_lines = self.report._get_lines(options)
        self.assertLinesValues(
            # pylint: disable=C0326
            report_lines,
            #   Name                    Due Date   Not Due On      1 - 30     31 - 60     61 - 90    91 - 120       Older        Total
            [   0,                      1,                  4,          5,          6,          7,          8,          9,          10],
            [
                ('partner_a',           '',             100.0,      100.0,      100.0,      600.0,      300.0,      100.0,      1300.0),
                ('INV/2016/00002',      '01/01/2016',      '',         '',         '',         '',         '',      100.0,          ''),
                ('INV/2016/00002',      '10/04/2016',      '',         '',         '',         '',      100.0,         '',          ''),
                ('INV/2016/00002',      '10/05/2016',      '',         '',         '',         '',      200.0,         '',          ''),
                ('INV/2016/00002',      '11/03/2016',      '',         '',         '',      100.0,         '',         '',          ''),
                ('INV/2016/00001',      '11/03/2016',      '',         '',         '',      500.0,         '',         '',          ''),
                ('INV/2016/00002',      '12/03/2016',      '',         '',      100.0,         '',         '',         '',          ''),
                ('INV/2016/00002',      '01/02/2017',      '',      100.0,         '',         '',         '',         '',          ''),
                ('INV/2016/00002',      '02/01/2017',   100.0,         '',         '',         '',         '',         '',          ''),
                ('partner_b',           '',              50.0,       50.0,       50.0,       300.0,     150.0,       50.0,       650.0),
                ('Total',               '',             150.0,      150.0,      150.0,       900.0,     450.0,      150.0,      1950.0),
            ],
        )

        # Sort 61 - 90 decreasing.
        options['selected_column'] = 8
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._sort_lines(report_lines, options),
            #   Name                    Due Date   Not Due On      1 - 30     31 - 60     61 - 90    91 - 120       Older        Total
            [   0,                      1,                  4,          5,          6,          7,          8,          9,          10],
            [
                ('partner_a',           '',             100.0,      100.0,      100.0,      600.0,      300.0,      100.0,      1300.0),
                ('INV/2016/00001',      '11/03/2016',      '',         '',         '',      500.0,         '',         '',          ''),
                ('INV/2016/00002',      '11/03/2016',      '',         '',         '',      100.0,         '',         '',          ''),
                ('INV/2016/00002',      '01/01/2016',      '',         '',         '',         '',         '',      100.0,          ''),
                ('INV/2016/00002',      '10/04/2016',      '',         '',         '',         '',      100.0,         '',          ''),
                ('INV/2016/00002',      '10/05/2016',      '',         '',         '',         '',      200.0,         '',          ''),
                ('INV/2016/00002',      '12/03/2016',      '',         '',      100.0,         '',         '',         '',          ''),
                ('INV/2016/00002',      '01/02/2017',      '',      100.0,         '',         '',         '',         '',          ''),
                ('INV/2016/00002',      '02/01/2017',   100.0,         '',         '',         '',         '',         '',          ''),
                ('partner_b',           '',              50.0,       50.0,       50.0,      300.0,      150.0,       50.0,       650.0),
                ('Total',               '',             150.0,      150.0,      150.0,      900.0,      450.0,      150.0,      1950.0),
            ],
        )

        # Sort 61 - 90 increasing.
        options['selected_column'] = -8
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._sort_lines(report_lines, options),
            #   Name                    Due Date    Not Due On      1 - 30     31 - 60      61 - 90    91 - 120       Older        Total
            [   0,                      1,                   4,          5,          6,           7,          8,          9,          10],
            [
                ('partner_b',           '',               50.0,       50.0,       50.0,       300.0,      150.0,       50.0,       650.0),
                ('partner_a',           '',              100.0,      100.0,      100.0,       600.0,      300.0,      100.0,      1300.0),
                ('INV/2016/00002',      '01/01/2016',       '',         '',         '',          '',         '',      100.0,          ''),
                ('INV/2016/00002',      '10/04/2016',       '',         '',         '',          '',      100.0,         '',          ''),
                ('INV/2016/00002',      '10/05/2016',       '',         '',         '',          '',      200.0,         '',          ''),
                ('INV/2016/00002',      '12/03/2016',       '',         '',      100.0,          '',         '',         '',          ''),
                ('INV/2016/00002',      '01/02/2017',       '',      100.0,         '',          '',         '',         '',          ''),
                ('INV/2016/00002',      '02/01/2017',    100.0,         '',         '',          '',         '',         '',          ''),
                ('INV/2016/00002',      '11/03/2016',       '',         '',         '',       100.0,         '',         '',          ''),
                ('INV/2016/00001',      '11/03/2016',       '',         '',         '',       500.0,         '',         '',          ''),
                ('Total',               '',              150.0,      150.0,      150.0,       900.0,      450.0,      150.0,      1950.0),
            ],
        )

    def test_aged_receivable_unfold_2_folded_line(self):
        ''' Test unfolding a line when "clicking" on a folded line. '''
        line_id = 'partner_id-res.partner-%s' % self.partner_b.id
        options = self._init_options(self.report, fields.Date.from_string('2017-02-01'), fields.Date.from_string('2017-02-01'))
        options['unfolded_lines'] = [line_id]

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options, line_id=line_id),
            #   Name                    Due Date    Not Due On      1 - 30     31 - 60     61 - 90    91 - 120       Older        Total
            [   0,                      1,                   4,          5,          6,          7,          8,          9,         10],
            [
                ('partner_b',           '',               50.0,       50.0,       50.0,      300.0,      150.0,       50.0,      650.0),
                ('INV/2016/00002',      '01/01/2016',       '',         '',         '',         '',         '',       50.0,         ''),
                ('INV/2016/00002',      '10/04/2016',       '',         '',         '',         '',       50.0,         '',         ''),
                ('INV/2016/00002',      '10/05/2016',       '',         '',         '',         '',      100.0,         '',         ''),
                ('INV/2016/00002',      '11/03/2016',       '',         '',         '',       50.0,         '',         '',         ''),
                ('INV/2016/00001',      '11/03/2016',       '',         '',         '',      250.0,         '',         '',         ''),
                ('INV/2016/00002',      '12/03/2016',       '',         '',       50.0,         '',         '',         '',         ''),
                ('INV/2016/00002',      '01/02/2017',       '',       50.0,         '',         '',         '',         '',         ''),
                ('INV/2016/00002',      '02/01/2017',     50.0,         '',         '',         '',         '',         '',         ''),
            ],
        )

    def test_aged_receivable_unknown_partner(self):
        ''' Test that journal items without a partner in the receivable account appear as unknown partner.'''

        misc_move = self.env['account.move'].create({
            'date': '2017-03-31',
            'line_ids': [
                (0, 0, {'debit': 1000.0, 'credit': 0.0, 'account_id': self.company_data['default_account_revenue'].id}),
                (0, 0, {'debit': 0.0, 'credit': 1000.0, 'account_id': self.company_data['default_account_receivable'].id}),
            ],
        })
        misc_move.action_post()

        options = self._init_options(self.report, fields.Date.from_string('2017-03-01'), fields.Date.from_string('2017-04-01'))

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name              Due Date     Not Due On      1 - 30     31 - 60     61 - 90    91 - 120       Older        Total
            [   0,                       1,             4,          5,          6,          7,          8,          9,          10],
            [
                ('partner_a',           '',           0.0,        0.0,      100.0,      100.0,      100.0,     1000.0,      1300.0),
                ('partner_b',           '',           0.0,        0.0,       50.0,       50.0,       50.0,      500.0,       650.0),
                ('Unknown Partner',     '',           0.0,    -1000.0,        0.0,        0.0,        0.0,        0.0,     -1000.0),
                ('Total',               '',           0.0,    -1000.0,      150.0,      150.0,      150.0,     1500.0,       950.0),
            ],
        )

    def test_aged_receivable_filter_partners(self):
        ''' Test the filter on top allowing to filter on res.partner.'''
        options = self._init_options(self.report, fields.Date.from_string('2017-02-01'), fields.Date.from_string('2017-02-01'))
        options['partner_ids'] = self.partner_a.ids

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name              Due Date     Not Due On      1 - 30     31 - 60     61 - 90    91 - 120       Older        Total
            [   0,                      1,              4,          5,          6,          7,          8,          9,          10],
            [
                ('partner_a',           '',         100.0,      100.0,      100.0,      600.0,      300.0,      100.0,      1300.0),
                ('Total',               '',         100.0,      100.0,      100.0,      600.0,      300.0,      100.0,      1300.0),
            ],
        )

    def test_aged_receivable_filter_partner_categories(self):
        ''' Test the filter on top allowing to filter on res.partner.category.'''
        options = self._init_options(self.report, fields.Date.from_string('2017-02-01'), fields.Date.from_string('2017-02-01'))
        options['partner_categories'] = self.partner_category_a.ids

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name             Due Date  Not Due On      1 - 30     31 - 60     61 - 90    91 - 120       Older        Total
            [   0,                      1,          4,          5,          6,          7,          8,          9,          10],
            [
                ('partner_a',           '',     100.0,      100.0,      100.0,      600.0,      300.0,      100.0,      1300.0),
                ('partner_b',           '',      50.0,       50.0,       50.0,      300.0,      150.0,       50.0,       650.0),
                ('Total',               '',     150.0,      150.0,      150.0,      900.0,      450.0,      150.0,      1950.0),
            ],
        )

    def test_aged_receivable_reconciliation_date(self):
        """Check the values at a date before some reconciliations are done."""
        options = self._init_options(self.report, fields.Date.from_string('2016-10-31'), fields.Date.from_string('2016-10-31'))

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name             Due Date  Not Due On      1 - 30     31 - 60     61 - 90    91 - 120       Older       Total
            [   0,                      1,          4,          5,          6,          7,          8,          9,         10],
            [
                ('partner_a',           '',   -100.00,    1100.00,        0.0,        0.0,        0.0,     100.00,    1100.00),
                ('partner_b',           '',    -33.35,     366.66,        0.0,        0.0,        0.0,      33.33,     366.64),
                ('Total',               '',   -133.35,    1466.66,        0.0,        0.0,        0.0,     133.33,    1466.64),
            ],
        )

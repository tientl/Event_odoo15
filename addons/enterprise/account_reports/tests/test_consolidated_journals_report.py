# -*- coding: utf-8 -*-
# pylint: disable=C0326
from .common import TestAccountReportsCommon

from odoo import fields
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestConsolidatedJournalsReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        counterpart_account = cls.company_data['default_account_revenue']

        cls.journals = cls.env['account.journal']
        for i, journal_type in enumerate(('sale', 'purchase', 'cash', 'bank', 'general')):
            account_1 = cls.env['account.account'].create({
                'name': 'account_%s_1' % i,
                'code': '%s_1' % i,
                'user_type_id': cls.env.ref('account.data_account_type_current_assets').id,
                'company_id': cls.company_data['company'].id,
            })
            account_2 = cls.env['account.account'].create({
                'name': 'account_%s_1' % i,
                'code': '%s_2' % i,
                'user_type_id': cls.env.ref('account.data_account_type_current_assets').id,
                'company_id': cls.company_data['company'].id,
            })

            journal = cls.env['account.journal'].create({
                'name': f'journal {journal_type}',
                'code': str(i),
                'type': journal_type,
                'company_id': cls.company_data['company'].id,
            })
            cls.journals += journal

            for period_index in range(6):
                amount = 100.0 * (period_index + 1)
                cls.env['account.move'].create({
                    'move_type': 'entry',
                    'date': '2016-0%s-01' % (period_index + 1),
                    'journal_id': journal.id,
                    'line_ids': [
                        (0, 0, {'debit': amount / 2,    'credit': 0.0,      'account_id': account_1.id}),
                        (0, 0, {'debit': amount / 2,    'credit': 0.0,      'account_id': account_2.id}),
                        (0, 0, {'debit': 0.0,           'credit': amount,   'account_id': counterpart_account.id}),
                    ],
                }).action_post()

    def test_consolidated_journals_unfold_1_whole_report(self):
        line_id = 'journal_%s' % self.journals[0].id
        report = self.env['account.consolidated.journal']
        options = self._init_options(report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-12-31'))
        report = report.with_context(report._set_context(options))
        options['unfolded_lines'] = [line_id]

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      1,              2,              3],
            [
                ('journal sale (0)',                    2100.0,         2100.0,         0.0),
                ('0_1 account_0_1',                     1050.0,         0.0,            1050.0),
                ('0_2 account_0_1',                     1050.0,         0.0,            1050.0),
                ('400000 Product Sales',                0.0,            2100.0,         -2100.0),
                ('journal purchase (1)',                2100.0,         2100.0,         0.0),
                ('journal cash (2)',                    2100.0,         2100.0,         0.0),
                ('journal bank (3)',                    2100.0,         2100.0,         0.0),
                ('journal general (4)',                 2100.0,         2100.0,         0.0),
                ('Total',                               10500.0,        10500.0,        0.0),
                ('',                                    '',             '',             ''),
                ('Details per month',                   '',             '',             ''),
                ('Jan 2016',                            500.0,          500.0,          0.0),
                ('Feb 2016',                            1000.0,         1000.0,         0.0),
                ('Mar 2016',                            1500.0,         1500.0,         0.0),
                ('Apr 2016',                            2000.0,         2000.0,         0.0),
                ('May 2016',                            2500.0,         2500.0,         0.0),
                ('Jun 2016',                            3000.0,         3000.0,         0.0),
            ],
        )

    def test_consolidated_journals_unfold_2_folded_line(self):
        line_id = 'journal_%s' % self.journals[0].id
        report = self.env['account.consolidated.journal']
        options = self._init_options(report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-12-31'))
        report = report.with_context(report._set_context(options))
        options['unfolded_lines'] = [line_id]

        self.assertLinesValues(
            report._get_lines(options, line_id=line_id),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      1,              2,              3],
            [
                ('journal sale (0)',                    2100.0,         2100.0,         0.0),
                ('0_1 account_0_1',                     1050.0,         0.0,            1050.0),
                ('0_2 account_0_1',                     1050.0,         0.0,            1050.0),
                ('400000 Product Sales',                0.0,            2100.0,         -2100.0),
            ],
        )

    def test_consolidated_journals_filter_journal(self):
        report = self.env['account.consolidated.journal']
        options = self._init_options(report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-12-31'))
        options = self._update_multi_selector_filter(options, 'journals', self.journals[0].ids)
        report = report.with_context(report._set_context(options))

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      1,              2,              3],
            [
                ('journal sale (0)',                    2100.0,         2100.0,         0.0),
                ('Total',                               2100.0,         2100.0,         0.0),
                ('',                                    '',             '',             ''),
                ('Details per month',                   '',             '',             ''),
                ('Jan 2016',                            100.0,          100.0,          0.0),
                ('Feb 2016',                            200.0,          200.0,          0.0),
                ('Mar 2016',                            300.0,          300.0,          0.0),
                ('Apr 2016',                            400.0,          400.0,          0.0),
                ('May 2016',                            500.0,          500.0,          0.0),
                ('Jun 2016',                            600.0,          600.0,          0.0),
            ],
        )

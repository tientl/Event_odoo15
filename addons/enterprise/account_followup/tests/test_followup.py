# -*- coding: utf-8 -*-
from freezegun import freeze_time

from odoo.tests import tagged
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@tagged('post_install', '-at_install')
class TestAccountFollowupReports(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.partner_a.email = 'partner_a@mypartners.xyz'

        cls.env['account_followup.followup.line'].search([]).unlink()

        cls.first_followup_level = cls.env['account_followup.followup.line'].create({
            'name': 'first_followup_level',
            'delay': 10,
            'description': 'First Followup Level',
            'send_email': True,
            'print_letter': False,
            'join_invoices': True,
        })
        cls.second_followup_level = cls.env['account_followup.followup.line'].create({
            'name': 'second_followup_level',
            'delay': 15,
            'description': 'Second Followup Level',
        })

    def assertPartnerFollowup(self, partner, status, level):
        partner.invalidate_cache(['followup_status', 'followup_level'])
        res = partner._query_followup_level()
        self.assertEqual(res.get(partner.id, {}).get('followup_status'), status or None)
        self.assertEqual(res.get(partner.id, {}).get('followup_level'), level.id if level else None)

    def test_followup_report(self):
        ''' Test folded/unfolded lines. '''
        # Init options.
        report = self.env['account.followup.report']
        options = {
            **report._get_options(None),
            'partner_id': self.partner_a.id,
        }
        report = report.with_context(report._set_context(options))

        with freeze_time('2016-01-01'):
            self.assertPartnerFollowup(self.partner_a, None, None)

        # 2016-01-01: First invoice, partially paid.

        invoice_1 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [(0, 0, {'quantity': 1, 'price_unit': 500})]
        })
        invoice_1.action_post()

        payment_1 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 0.0,       'credit': 200.0,    'account_id': self.company_data['default_account_receivable'].id}),
                (0, 0, {'debit': 200.0,     'credit': 0.0,      'account_id': self.company_data['default_journal_bank'].default_account_id.id}),
            ],
        })
        payment_1.action_post()

        (payment_1 + invoice_1).line_ids\
            .filtered(lambda line: line.account_id == self.company_data['default_account_receivable'])\
            .reconcile()

        with freeze_time('2016-01-01'):
            self.assertLinesValues(
                # pylint: disable=C0326
                report._get_lines(options),
                #   Name                                    Date,           Due Date,       Doc.    Exp. Date   Blocked             Total Due
                [   0,                                      1,              2,              3,      5,          6,                  7],
                [
                    ('INV/2016/00001',                      '01/01/2016',   '01/01/2016',   '',     '',         '',                 300.0),
                    ('',                                    '',             '',             '',     '',         'Total Due',        300.0),
                ],
            )
            self.assertPartnerFollowup(self.partner_a, 'with_overdue_invoices', None)

        # 2016-01-05: Credit note due at 2016-01-10.

        invoice_2 = self.env['account.move'].create({
            'move_type': 'out_refund',
            'invoice_date': '2016-01-05',
            'invoice_date_due': '2016-01-10',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [(0, 0, {'quantity': 1, 'price_unit': 200})]
        })
        invoice_2.action_post()

        with freeze_time('2016-01-05'):
            self.assertLinesValues(
                # pylint: disable=C0326
                report._get_lines(options),
                #   Name                                    Date,           Due Date,       Doc.    Exp. Date   Blocked             Total Due
                [   0,                                      1,              2,              3,      5,          6,                  7],
                [
                    ('RINV/2016/00001',                     '01/05/2016',   '01/10/2016',   '',     '',         '',                 -200.0),
                    ('INV/2016/00001',                      '01/01/2016',   '01/01/2016',   '',     '',         '',                 300.0),
                    ('',                                    '',             '',             '',     '',         'Total Due',        100.0),
                    ('',                                    '',             '',             '',     '',         'Total Overdue',    300.0),
                ],
            )
            self.assertPartnerFollowup(self.partner_a, 'with_overdue_invoices', None)

        # 2016-01-15: Draft invoice + previous credit note reached the date_maturity + first invoice reached the delay
        # of the first followup level.

        invoice_3 = self.env['account.move'].create({
            'move_type': 'out_refund',
            'invoice_date': '2016-01-15',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [(0, 0, {'quantity': 1, 'price_unit': 1000})]
        })

        with freeze_time('2016-01-15'):
            self.assertLinesValues(
                # pylint: disable=C0326
                report._get_lines(options),
                #   Name                                    Date,           Due Date,       Doc.    Exp. Date   Blocked             Total Due
                [   0,                                      1,              2,              3,      5,          6,                  7],
                [
                    ('RINV/2016/00001',                     '01/05/2016',   '01/10/2016',   '',     '',         '',                 -200.0),
                    ('INV/2016/00001',                      '01/01/2016',   '01/01/2016',   '',     '',         '',                 300.0),
                    ('',                                    '',             '',             '',     '',         'Total Due',        100.0),
                    ('',                                    '',             '',             '',     '',         'Total Overdue',    100.0),
                ],
            )
            self.assertPartnerFollowup(self.partner_a, 'in_need_of_action', self.first_followup_level)

        # 2016-01-20: Invoice in foreign currency.

        invoice_4 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-20',
            'partner_id': self.partner_a.id,
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {'quantity': 1, 'price_unit': 300})]
        })
        invoice_4.action_post()

        with freeze_time('2016-01-20'):
            lines = report._get_lines(options)
            self.assertLinesValues(
                # pylint: disable=C0326
                lines[:3],
                #   Name                                    Date,           Due Date,       Doc.    Exp. Date   Blocked             Total Due
                [   0,                                      1,              2,              3,      5,          6,                  7],
                [
                    ('INV/2016/00002',                      '01/20/2016',   '01/20/2016',   '',     '',         '',                 300.0),
                    ('',                                    '',             '',             '',     '',         'Total Due',        300.0),
                    ('',                                    '',             '',             '',     '',         '',                 ''),
                ],
                currency_map={7: {'currency': self.currency_data['currency']}},
            )
            self.assertLinesValues(
                # pylint: disable=C0326
                lines[3:],
                #   Name                                    Date,           Due Date,       Doc.    Exp. Date   Blocked             Total Due
                [   0,                                      1,              2,              3,      5,          6,                  7],
                [
                    ('RINV/2016/00001',                     '01/05/2016',   '01/10/2016',   '',     '',         '',                 -200.0),
                    ('INV/2016/00001',                      '01/01/2016',   '01/01/2016',   '',     '',         '',                 300.0),
                    ('',                                    '',             '',             '',     '',         'Total Due',        100.0),
                    ('',                                    '',             '',             '',     '',         'Total Overdue',    100.0),
                ],
            )
            self.assertPartnerFollowup(self.partner_a, 'in_need_of_action', self.first_followup_level)

        # Trigger the followup report notice.

        invoice_attachments = self.env['ir.attachment']
        for invoice in invoice_1 + invoice_2 + invoice_4:
            invoice_attachment = self.env['ir.attachment'].create({
                'name': 'some_attachment.pdf',
                'res_id': invoice.id,
                'res_model': 'account.move',
                'datas': 'test',
                'type': 'binary',
            })
            invoice_attachments += invoice_attachment
            invoice._message_set_main_attachment_id([(4, invoice_attachment.id)])

        self.partner_a._compute_unpaid_invoices()
        self.env['account.followup.report'].send_email(options)
        sent_attachments = self.env['mail.message'].search([('partner_ids', '=', self.partner_a.id)]).attachment_ids

        self.assertEqual(invoice_attachments, sent_attachments)

        # Execute followup.

        self.partner_a._execute_followup_partner()

        with freeze_time('2016-01-20'):
            self.assertPartnerFollowup(self.partner_a, 'with_overdue_invoices', self.second_followup_level)

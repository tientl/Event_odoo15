# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon

import logging
import requests

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestTourReconciliationWidget(AccountTestInvoicingHttpCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.out_invoice_1 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'name': 'line1', 'price_unit': 100.0}),
            ],
        })

        cls.out_invoice_2 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'name': 'line1', 'price_unit': 250.0}),
            ],
        })

        cls.in_invoice_1 = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': cls.partner_b.id,
            'invoice_date': '2019-04-01',
            'date': '2019-04-01',
            'invoice_line_ids': [
                (0, 0, {'name': 'line1', 'price_unit': 1175.0}),
            ],
        })

        cls.in_invoice_2 = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': cls.partner_b.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'name': 'line1', 'price_unit': 180.0}),
            ],
        })
        (cls.out_invoice_1 + cls.out_invoice_2 + cls.in_invoice_1 + cls.in_invoice_2).action_post()

        cls.bank_statement = cls.env['account.bank.statement'].create({
            'journal_id': cls.company_data['default_journal_bank'].id,
            'date': '2019-06-30',
            'balance_start': 0.0,
            'balance_end_real': 570.0,
            'line_ids': [
                # Match out_invoice_1 & out_invoice_2.
                (0, 0, {
                    'date': '2019-06-01', 'amount': 350.0, 'partner_id': cls.partner_a.id,
                    'payment_ref': 'line1: Payment of %s and %s' % (cls.out_invoice_1.name, cls.out_invoice_2.name),
                }),
                # To be reconciled manually with in_invoice_1 (partial).
                (0, 0, {
                    'date': '2019-06-02', 'amount': -500.0, 'partner_id': cls.partner_b.id,
                    'payment_ref': 'line2',
                }),
                # Line without partner to match with in_invoice_2.
                (0, 0, {
                    'date': '2019-06-03', 'amount': -180.0, 'partner_id': False,
                    'payment_ref': 'line3',
                }),
                # Line to reconcile with a custom write-off line.
                (0, 0, {
                    'date': '2019-06-04', 'amount': 900.0, 'partner_id': False,
                    'payment_ref': 'line4',
                }),
            ],
        })
        cls.bank_statement.button_post()

    def test_bank_statement_reconciliation_tour(self):
        payload = {
            'action': 'bank_statement_reconciliation_view',
            'statement_line_ids[]': self.bank_statement.line_ids.ids,
        }
        prep = requests.models.PreparedRequest()
        prep.prepare_url(url="http://localhost/web#", params=payload)

        account_reconcile_model = self.env['account.reconcile.model'].search([('company_id', '=', self.company_data['company'].id)])
        account_reconcile_model.past_months_limit = None

        self.start_tour(
            prep.url.replace('http://localhost', '').replace('?', '#'),
            'bank_statement_reconciliation', login=self.env.user.login,
        )

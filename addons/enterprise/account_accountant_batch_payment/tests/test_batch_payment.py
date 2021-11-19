# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestBatchPayment(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # Get some records
        cls.customers = cls.env['res.partner'].create([
            {'name': 'alpha'},
            {'name': 'beta'},
            {'name': 'gamma'},
        ])

        # Create a bank journal
        cls.journal = cls.company_data['default_journal_bank']
        cls.batch_deposit_method = cls.env.ref('account_batch_payment.account_payment_method_batch_deposit')
        cls.batch_deposit = cls.journal.inbound_payment_method_line_ids.filtered(lambda l: l.code == 'batch_payment')

        # Create some payments
        cls.payments = [
            cls.createPayment(cls.customers[0], 100),
            cls.createPayment(cls.customers[1], 200),
            cls.createPayment(cls.customers[2], 500),
        ]

    @classmethod
    def createPayment(cls, partner, amount):
        """ Create a batch deposit payment """
        payment = cls.env['account.payment'].create({
            'journal_id': cls.journal.id,
            'payment_method_line_id': cls.batch_deposit.id,
            'payment_type': 'inbound',
            'date': time.strftime('%Y') + '-07-15',
            'amount': amount,
            'partner_id': partner.id,
            'partner_type': 'customer',
        })
        payment.action_post()
        return payment

    def test_BatchLifeCycle(self):
        # Create and "print" a batch payment
        batch = self.env['account.batch.payment'].create({
            'journal_id': self.journal.id,
            'payment_ids': [(4, payment.id, None) for payment in self.payments],
            'payment_method_id': self.batch_deposit_method.id,
        })
        batch.validate_batch()
        error_action = batch.print_batch_payment()
        self.assertTrue(all(payment.is_move_sent for payment in self.payments))
        self.assertTrue(batch.state == 'sent')
        # Create a bank statement
        bank_statement = self.env['account.bank.statement'].create({
            'name': 'test deposit life cycle',
            'balance_start': 0.0,
            'balance_end_real': 800.0,
            'date': time.strftime('%Y') + '-08-01',
            'journal_id': self.journal.id,
            'company_id': self.env.user.company_id.id,
        })
        bank_statement_line = self.env['account.bank.statement.line'].create({
            'amount': 800,
            'date': time.strftime('%Y') + '-07-18',
            'payment_ref': 'DEPOSIT',
            'statement_id': bank_statement.id,
        })
        bank_statement.button_post()
        # Simulate the process of reconciling the statement line using the batch deposit
        deposits_reconciliation_data = self.env['account.reconciliation.widget'].get_batch_payments_data(bank_statement.ids)
        self.assertTrue(len(deposits_reconciliation_data), 1)
        self.assertTrue(deposits_reconciliation_data[0]['id'], batch.id)
        deposit_reconciliation_lines = self.env['account.reconciliation.widget'].get_move_lines_by_batch_payment(bank_statement_line.id, batch.id)
        self.assertTrue(len(deposit_reconciliation_lines), 3)
        lines_vals_list = [{'id': line['id']} for line in deposit_reconciliation_lines]
        self.env['account.reconciliation.widget'].process_bank_statement_line(bank_statement_line.ids, [{'lines_vals_list': lines_vals_list}])
        self.assertTrue(all(payment.state == 'posted' for payment in self.payments))
        self.assertTrue(batch.state == 'reconciled')

    def test_zero_amount_payment(self):
        zero_payment = self.createPayment(self.customers[0], 0)
        batch_vals = {
            'journal_id': self.journal.id,
            'payment_ids': [(4, zero_payment.id, None)],
            'payment_method_id': self.batch_deposit_method.id,
        }
        self.assertRaises(ValidationError, self.env['account.batch.payment'].create, batch_vals)

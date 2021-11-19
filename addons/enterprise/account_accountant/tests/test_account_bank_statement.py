
# -*- coding: utf-8 -*-
from odoo.addons.account.tests.test_account_bank_statement import TestAccountBankStatementCommon
from odoo.tests import tagged
from odoo import fields


@tagged('post_install', '-at_install')
class TestAccountBankStatement(TestAccountBankStatementCommon):

    def test_reconciliation_payment_state(self):
        ''' Test the 'in_payment' state on invoices & 'reconciled' state in payments:
        - The invoice could be reconciled with account.payments.
        - The invoice could be reconciled directly with an account.bank.statement.line.
        - The invoice could be reconciled with both.
        '''
        # Two invoices, both having 3000.0 in foreign currency to reconcile.
        test_invoice_1 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.from_string('2019-01-01'),
            'partner_id': self.partner_a.id,
            'currency_id': self.currency_2.id,
            'invoice_line_ids': [(0, 0, {
                'quantity': 1,
                'price_unit': 3000.0,
                'account_id': self.company_data['default_account_revenue'].id,
            })]
        })
        test_invoice_2 = test_invoice_1.copy()

        # Two statement lines having respectively 2000.0 & 4000.0 in foreign currency to reconcile.
        self.statement = self.env['account.bank.statement'].create({
            'name': 'test_statement',
            'date': '2019-01-01',
            'journal_id': self.bank_journal_1.id,
            'balance_end_real': 7250.0,
            'line_ids': [
                (0, 0, {
                    'date': '2019-01-01',
                    'payment_ref': 'line_1',
                    'partner_id': self.partner_a.id,
                    'foreign_currency_id': self.currency_2.id,
                    'amount': 1250.0,
                    'amount_currency': 2500.0,
                }),
                (0, 0, {
                    'date': '2019-01-01',
                    'payment_ref': 'line_2',
                    'partner_id': self.partner_a.id,
                    'amount': 2000.0,
                }),
                (0, 0, {
                    'date': '2019-01-01',
                    'payment_ref': 'line_3',
                    'partner_id': self.partner_a.id,
                    'amount': 4000.0,
                }),
            ],
        })

        # Two payments, both having 2000.0 in foreign currency to reconcile.
        test_payment_1 = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'amount': 2000.0,
            'date': fields.Date.from_string('2019-01-01'),
            'currency_id': self.currency_2.id,
            'partner_id': self.partner_a.id,
            'journal_id': self.statement.line_ids.journal_id.id,
            'payment_method_line_id': self.inbound_payment_method_line.id,
        })
        test_payment_2 = test_payment_1.copy()

        test_st_line_1 = self.statement.line_ids.filtered(lambda line: line.payment_ref == 'line_2')
        test_st_line_2 = self.statement.line_ids.filtered(lambda line: line.payment_ref == 'line_3')

        # Post everything.
        (test_invoice_1 + test_invoice_2).action_post()
        (test_payment_1 + test_payment_2).action_post()
        self.statement.button_post()

        # Initial setup: nothing is reconciled.
        self.assertRecordValues(test_invoice_1 + test_invoice_2, [
            {
                'payment_state': 'not_paid',
                'amount_total': 3000.0,
                'amount_residual': 3000.0,
            },
            {
                'payment_state': 'not_paid',
                'amount_total': 3000.0,
                'amount_residual': 3000.0,
            },
        ])
        self.assertRecordValues(test_payment_1 + test_payment_2, [
            {
                'state': 'posted',
                'amount': 2000.0,
            },
            {
                'state': 'posted',
                'amount': 2000.0,
            },
        ])

        # ===== Reconcile entries together =====

        # Reconciliation between test_invoice_1 & test_payment_1.
        # The payment state shouldn't change.
        (test_invoice_1.line_ids + test_payment_1.line_ids)\
            .filtered(lambda line: line.account_id.user_type_id.type == 'receivable')\
            .reconcile()

        self.assertRecordValues(test_invoice_1, [
            {
                'payment_state': 'partial',
                'amount_total': 3000.0,
                'amount_residual': 1000.0,
            },
        ])

        # Reconciliation between test_invoice_1 & test_payment_2.
        # test_invoice_1 must be paid but in the 'in_payment' state.
        (test_invoice_1.line_ids + test_payment_2.line_ids)\
            .filtered(lambda line: line.account_id.user_type_id.type == 'receivable')\
            .reconcile()

        self.assertRecordValues(test_invoice_1, [
            {
                'payment_state': 'in_payment',
                'amount_total': 3000.0,
                'amount_residual': 0.0,
            },
        ])

        # Reconciliation between test_st_line_1 & test_payment_1.
        # test_invoice_1 should remain in 'in_payment' state since test_payment_2 is not yet reconciled with a statement
        # line.
        # However, test_payment_1 should now be in 'reconciled' state.
        counterpart_line = test_payment_1.line_ids.filtered(lambda line: line.account_id.user_type_id.type != 'receivable')
        test_st_line_1.reconcile([{'id': counterpart_line.id}])

        self.assertRecordValues(test_st_line_1, [{'is_reconciled': True}])
        self.assertRecordValues(test_invoice_1, [
            {
                'payment_state': 'in_payment',
                'amount_total': 3000.0,
                'amount_residual': 0.0,
            },
        ])
        self.assertRecordValues(test_payment_1, [{'is_matched': True}])

        # Reconciliation between test_st_line_2 & test_payment_2.
        # An open balance of 2000.0 will be created.
        # test_invoice_1 should get the 'paid' state.
        # test_payment_2 should be now in 'reconciled' state.
        counterpart_line = test_payment_2.line_ids.filtered(lambda line: line.account_id.user_type_id.type != 'receivable')
        test_st_line_2.reconcile([{'id': counterpart_line.id}])

        self.assertRecordValues(test_st_line_2, [{'is_reconciled': True}])
        self.assertRecordValues(test_invoice_1, [
            {
                'payment_state': 'paid',
                'amount_total': 3000.0,
                'amount_residual': 0.0,
            },
        ])
        self.assertRecordValues(test_payment_2, [{'is_matched': True}])

        # Reconciliation between test_invoice_2 & test_payment_2.
        # The payment state shouldn't change since test_payment_2 is already partially reconciled.
        (test_invoice_2.line_ids + test_payment_2.line_ids)\
            .filtered(lambda line: line.account_id.user_type_id.type == 'receivable')\
            .reconcile()

        self.assertRecordValues(test_invoice_2, [
            {
                'payment_state': 'partial',
                'amount_total': 3000.0,
                'amount_residual': 2000.0,
            },
        ])

        # Reconciliation of the test_st_line_2's open balance with the test_invoice_2's remaining balance.
        # test_invoice_2 should get the 'paid' state.
        (test_invoice_2.line_ids + test_st_line_2.line_ids)\
            .filtered(lambda line: line.account_id.user_type_id.type == 'receivable')\
            .reconcile()

        self.assertRecordValues(test_invoice_2, [
            {
                'payment_state': 'paid',
                'amount_total': 3000.0,
                'amount_residual': 0.0,
            },
        ])

        # ===== Undo the reconciliation =====

        (test_st_line_1 + test_st_line_2).button_undo_reconciliation()

        self.assertRecordValues(test_st_line_1, [{'is_reconciled': False}])
        self.assertRecordValues(test_st_line_2, [{'is_reconciled': False}])
        self.assertRecordValues(test_invoice_1, [{'payment_state': 'in_payment'}])
        self.assertRecordValues(test_invoice_2, [{'payment_state': 'partial'}])
        self.assertRecordValues(test_payment_1, [{'state': 'posted'}])
        self.assertRecordValues(test_payment_2, [{'state': 'posted'}])

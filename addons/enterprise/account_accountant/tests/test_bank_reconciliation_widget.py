# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestBankStatementReconciliation(AccountTestInvoicingCommon):

    def test_reconciliation_proposition(self):
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [(0, 0, {
                'quantity': 1,
                'price_unit': 100,
                'name': 'test invoice',
            })],
        })
        move.action_post()
        rcv_mv_line = move.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))

        st_line = self.env['account.bank.statement'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'line_ids': [(0, 0, {
                'payment_ref': '_',
                'partner_id': self.partner_a.id,
                'amount': 100,
            })],
        }).line_ids

        # exact amount match
        rec_prop = self.env['account.reconciliation.widget'].get_bank_statement_line_data(st_line.ids)['lines']
        prop = rec_prop[0]['reconciliation_proposition']

        self.assertEqual(len(prop), 1)
        self.assertEqual(prop[0]['id'], rcv_mv_line.id)

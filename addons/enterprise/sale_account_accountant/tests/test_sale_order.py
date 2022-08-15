# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestSaleOrder(TestSaleCommon):

    def test_reconciliation_with_so(self):
        # create SO
        so = self.env['sale.order'].create({
            'name': 'SO/01/01',
            'reference': 'Petit suisse',
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
        })
        self.env['sale.order.line'].create({
            'name': self.company_data['product_order_no'].name,
            'product_id': self.company_data['product_order_no'].id,
            'product_uom_qty': 2,
            'product_uom': self.company_data['product_order_no'].uom_id.id,
            'price_unit': self.company_data['product_order_no'].list_price,
            'order_id': so.id,
            'tax_id': False,
        })
        # Mark SO as sent otherwise we won't find any match
        so.write({'state': 'sent'})
        # Create bank statement
        statement = self.env['account.bank.statement'].create({
            'name': 'Test',
            'journal_id': self.company_data['default_journal_bank'].id,
            'user_id': self.company_data['default_user_employee'].id,
        })
        st_line1 = self.env['account.bank.statement.line'].create({
            'payment_ref': 'should not find anything',
            'amount': 15,
            'statement_id': statement.id
        })
        st_line2 = self.env['account.bank.statement.line'].create({
            'payment_ref': 'Payment for SO/01/01',
            'amount': 15,
            'statement_id': statement.id
        })
        st_line3 = self.env['account.bank.statement.line'].create({
            'payment_ref': 'Payment for Petit suisse',
            'amount': 15,
            'statement_id': statement.id
        })
        # Call get_bank_statement_line_data for st_line_1, should not find any sale order
        res = self.env['account.reconciliation.widget'].get_bank_statement_line_data([st_line1.id])
        line = res.get('lines', [{}])[0]
        self.assertFalse(line.get('sale_order_ids', False))
        # Call again for st_line_2, it should find sale_order
        res = self.env['account.reconciliation.widget'].get_bank_statement_line_data([st_line2.id])
        line = res.get('lines', [{}])[0]
        self.assertEqual(line.get('sale_order_ids', []), [so.id])
        # Call again for st_line_3, it should find sale_order based on reference
        res = self.env['account.reconciliation.widget'].get_bank_statement_line_data([st_line3.id])
        line = res.get('lines', [{}])[0]
        self.assertEqual(line.get('sale_order_ids', []), [so.id])

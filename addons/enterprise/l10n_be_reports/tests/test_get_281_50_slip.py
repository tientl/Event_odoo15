# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo import fields, Command


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestResPartner(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_be.l10nbe_chart_template'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.invoice = cls.init_invoice('in_invoice')

        cls.product_line_vals_1 = {
            'name': cls.product_a.name,
            'product_id': cls.product_a.id,
            'account_id': cls.product_a.property_account_expense_id.id,
            'partner_id': cls.partner_a.id,
            'product_uom_id': cls.product_a.uom_id.id,
            'quantity': 1.0,
            'discount': 0.0,
            'price_unit': 1000.0,
            'price_subtotal': 1000.0,
            'price_total': 1150,
            'tax_ids': cls.product_a.supplier_taxes_id.ids,
            'tax_line_id': False,
            'currency_id': False,
            'amount_currency': 0.0,
            'debit': 1000.0,
            'credit': 0.0,
            'date_maturity': False,
        }
        cls.tax_line_vals_1 = {
            'name': cls.tax_purchase_a.name,
            'product_id': False,
            'account_id': cls.company_data['default_account_tax_purchase'].id,
            'partner_id': cls.partner_a.id,
            'product_uom_id': False,
            'quantity': 1.0,
            'discount': 0.0,
            'price_unit': 150,
            'price_subtotal': 150,
            'price_total': 150,
            'tax_ids': [],
            'tax_line_id': cls.tax_purchase_a.id,
            'currency_id': False,
            'amount_currency': 0.0,
            'debit': 150,
            'credit': 0.0,
            'date_maturity': False,
        }
        cls.term_line_vals_1 = {
            'name': '',
            'product_id': False,
            'account_id': cls.company_data['default_account_payable'].id,
            'partner_id': cls.partner_a.id,
            'product_uom_id': False,
            'quantity': 1.0,
            'discount': 0.0,
            'price_unit': -1150.0,
            'price_subtotal': -1150.0,
            'price_total': -1150.0,
            'tax_ids': [],
            'tax_line_id': False,
            'currency_id': False,
            'amount_currency': 0.0,
            'debit': 0.0,
            'credit': 1150.0,
            'date_maturity': fields.Date.from_string('2000-05-12'),
        }
        cls.partner_a.write({
            'street': 'Rue du Jacobet, 9',
            'zip': '7100',
            'city': 'La Louvière',
            'vat': 'BE0475646428',
            'is_company': True,
            'category_id': [(4, cls.env.ref('l10n_be_reports.res_partner_tag_281_50').id)]
        })
        cls.partner_a_information = {
            'name': 'partner_a',
            'address': 'Rue du Jacobet, 9',
            'zip': '7100',
            'city': 'La Louvière',
            'nature': '2',
            'vat': '0475646428',
            'remunerations': {'commissions': 1000.0},
            'paid_amount': 826.45,
            'total_amount': 1000.0,
            'job_position': False,
            'citizen_identification': False
        }
        cls.tag_281_50_commissions = cls.env.ref('l10n_be_reports.account_tag_281_50_commissions')
        cls.tag_281_50_fees = cls.env.ref('l10n_be_reports.account_tag_281_50_fees')
        cls.tag_281_50_atn = cls.env.ref('l10n_be_reports.account_tag_281_50_atn')
        cls.tag_281_50_exposed_expenses = cls.env.ref('l10n_be_reports.account_tag_281_50_exposed_expenses')

    def test_res_partner_get_paid_amount(self):
        '''Checking of the paid total value for a specific partner.'''
        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2000-05-12'),
            'currency_id': self.currency_data['currency'].id,
            'invoice_payment_term_id': self.pay_terms_a.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_line_vals_1['product_id'],
                    'product_uom_id': self.product_line_vals_1['product_uom_id'],
                    'price_unit': self.product_line_vals_1['price_unit'],
                    'tax_ids': [Command.set(self.product_line_vals_1['tax_ids'])],
                }),
            ],
        })
        move.invoice_line_ids.account_id.tag_ids |= self.tag_281_50_commissions
        move.action_post()

        payment_dicts = []
        for i in range(2):
            payment_dicts.append({
                'payment_type': 'outbound',
                'amount': 500,
                'currency_id': self.currency_data['currency'].id,
                'journal_id': self.company_data['default_journal_bank'].id,
                'date': fields.Date.from_string('200%s-05-12' % i),
                'partner_id': self.partner_a.id,
                'payment_method_line_id': self.outbound_payment_method_line.id,
                'partner_type': 'supplier'
            })

        payments = self.env['account.payment'].create(payment_dicts)
        payments.action_post()

        payable_move_lines = move.mapped('line_ids').filtered(lambda x: x.account_internal_type == 'payable')
        payable_move_lines += payments.line_ids.filtered(lambda x: x.account_internal_type == 'payable')
        payable_move_lines.reconcile()

        move.flush()
        payments.flush()

        self.assertEqual(move.amount_residual, 210.0)

        tags = self.env['account.account.tag'] + self.tag_281_50_commissions + self.tag_281_50_fees + self.tag_281_50_atn + self.tag_281_50_exposed_expenses
        paid_amount_per_partner = self.partner_a._get_paid_amount_per_partner('2000', tags)
        paid_amount_for_partner_a = paid_amount_per_partner.get(self.partner_a.id, 0.0)
        self.assertEqual(paid_amount_for_partner_a, self.partner_a.currency_id.round(413.22))

        paid_amount_per_partner = self.partner_a._get_paid_amount_per_partner('2001', tags)
        paid_amount_for_partner_a = paid_amount_per_partner.get(self.partner_a.id, 0.0)
        self.assertEqual(paid_amount_for_partner_a, self.partner_a.currency_id.round(413.22))

    def test_res_partner_get_partner_information(self):
        '''Checking of all information about a specific partner.'''
        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2000-05-12'),
            'currency_id': self.currency_data['currency'].id,
            'invoice_payment_term_id': self.pay_terms_a.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_line_vals_1['product_id'],
                    'product_uom_id': self.product_line_vals_1['product_uom_id'],
                    'price_unit': self.product_line_vals_1['price_unit'],
                    'tax_ids': [Command.set(self.product_line_vals_1['tax_ids'])],
                }),
            ],
        })
        move.invoice_line_ids.account_id.tag_ids |= self.tag_281_50_commissions
        move.action_post()

        payment = self.env['account.payment'].create({
            'payment_type': 'outbound',
            'amount': 1000,
            'currency_id': self.currency_data['currency'].id,
            'journal_id': self.company_data['default_journal_bank'].id,
            'date': fields.Date.from_string('2000-05-12'),
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.outbound_payment_method_line.id,
            'partner_type': 'supplier'
        })
        payment.action_post()

        payable_move_lines = move.mapped('line_ids').filtered(lambda x: x.account_internal_type == 'payable')
        payable_move_lines += payment.line_ids.filtered(lambda x: x.account_internal_type == 'payable')
        payable_move_lines.reconcile()

        move.flush()
        payment.flush()

        tags = self.env['account.account.tag'] + self.tag_281_50_commissions + self.tag_281_50_fees + self.tag_281_50_atn + self.tag_281_50_exposed_expenses
        paid_amount_per_partner = self.partner_a._get_paid_amount_per_partner('2000', tags)
        paid_amount_for_partner_a = paid_amount_per_partner.get(self.partner_a.id, 0.0)

        commissions_amounts = self.partner_a._get_balance_per_partner(self.tag_281_50_commissions, '2000')
        commissions_balance_for_partner_a = commissions_amounts.get(self.partner_a.id, 0.0)

        partner_information = self.partner_a._get_partner_information({'commissions': commissions_balance_for_partner_a}, paid_amount_for_partner_a)
        self.assertEqual(self.partner_a_information, partner_information)

# -*- coding: utf-8 -*-

from odoo import fields
from odoo.tests import tagged
from odoo.tools.misc import formatLang

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon

import datetime
from contextlib import contextmanager
from unittest.mock import patch
from freezegun import freeze_time


@tagged('post_install', '-at_install')
class POSTestTaxReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        test_country = cls.env['res.country'].create({
            'name': "Hassaleh",
            'code': 'HH',
        })

        cls.company_data['company'].country_id = test_country
        cls.company_data['company'].chart_template_id.country_id = test_country # So that we can easily instantiate test tax templates within this country

        # Create some tax report
        tax_report = cls.env['account.tax.report'].create({
            'name': 'Test',
            'country_id': test_country.id,
        })

        cls.pos_tax_report_line_invoice_base = cls._create_tax_report_line("Invoice Base", tax_report, tag_name='pos_invoice_base', sequence=0)
        cls.pos_tax_report_line_invoice_tax = cls._create_tax_report_line("Invoice Tax", tax_report, tag_name='pos_invoice_tax', sequence=1)
        cls.pos_tax_report_line_refund_base = cls._create_tax_report_line("Refund Base", tax_report, tag_name='pos_refund_base', sequence=2)
        cls.pos_tax_report_line_refund_tax = cls._create_tax_report_line("Refund Tax", tax_report, tag_name='pos_refund_tax', sequence=3)

        # Create a tax using the created report
        tax_template = cls.env['account.tax.template'].create({
            'name': 'Impôt recto',
            'amount': '10',
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'chart_template_id': cls.company_data['company'].chart_template_id.id,
            'invoice_repartition_line_ids': [
                (0,0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                    'plus_report_line_ids': [cls.pos_tax_report_line_invoice_base.id],
                }),

                (0,0, {
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'plus_report_line_ids': [cls.pos_tax_report_line_invoice_tax.id],
                }),
            ],
            'refund_repartition_line_ids': [
                (0,0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                    'plus_report_line_ids': [cls.pos_tax_report_line_refund_base.id],
                }),

                (0,0, {
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'plus_report_line_ids': [cls.pos_tax_report_line_refund_tax.id],
                }),
            ],
        })
        # Needed in order to be able to instantiate the template
        cls.env['ir.model.data'].create({
            'name': 'pos_account_reports.test_tax',
            'module': 'account_reports',
            'res_id': tax_template.id,
            'model': 'account.tax.template',
        })
        cls.pos_tax = tax_template._generate_tax(cls.company_data['company'])['tax_template_to_tax'][tax_template]

        pos_tax_account = cls.env['account.account'].create({
            'name': 'POS tax account',
            'code': 'POS tax test',
            'user_type_id': cls.env.ref('account.data_account_type_current_assets').id,
            'company_id': cls.company_data['company'].id,
        })

        rep_ln_tax = cls.pos_tax.invoice_repartition_line_ids + cls.pos_tax.refund_repartition_line_ids
        rep_ln_tax.filtered(lambda x: x.repartition_type == 'tax').write({'account_id': pos_tax_account.id})

        # Create POS objects
        pos_journal = cls.env['account.journal'].create({
            'name': 'POS journal',
            'type': 'sale',
            'code': 'POS',
            'company_id': cls.company_data['company'].id,
        })

        cls.pos_config = cls.env['pos.config'].create({
            'name': 'Crab Shop',
            'company_id': cls.company_data['company'].id,
            'journal_id': pos_journal.id,
        })

        cls.pos_product = cls.env['product.product'].create({
            'name': 'Crab',
            'type': 'consu',
        })

        cls.pos_payment_method = cls.env['pos.payment.method'].create({
            'name': 'POS test payment method',
            'receivable_account_id': cls.company_data['default_account_receivable'].id,
            'journal_id': cls.company_data['default_journal_cash'].id,
        })

        # Add the payment method to the pos_config
        cls.pos_config.write({'payment_method_ids': [(4, cls.pos_payment_method.id, 0)]})

    def _create_and_pay_pos_order(self, qty, price_unit):
        tax_amount = (self.pos_tax.amount / 100) * qty * price_unit # Only possible because the tax is 'percent' and price excluded. Don't do this at home !
        rounded_total = self.company_data['company'].currency_id.round(tax_amount + price_unit * qty)

        order = self.env['pos.order'].create({
            'company_id': self.company_data['company'].id,
            'partner_id': self.partner_a.id,
            'session_id': self.pos_config.current_session_id.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.pos_product.id,
                'price_unit': price_unit,
                'qty': qty,
                'tax_ids': [(6, 0, self.pos_tax.ids)],
                'price_subtotal': qty * price_unit,
                'price_subtotal_incl': rounded_total,
            })],
            'amount_total': rounded_total,
            'amount_tax': self.company_data['company'].currency_id.round(tax_amount),
            'amount_paid': 0,
            'amount_return': 0,
        })

        # Pay the order
        context_payment = {
            "active_ids": [order.id],
            "active_id": order.id
        }
        pos_make_payment = self.env['pos.make.payment'].with_context(context_payment).create({
            'amount': rounded_total,
            'payment_method_id': self.pos_payment_method.id,
        })
        pos_make_payment.with_context(context_payment).check()

    def test_pos_tax_report(self):
        self.pos_config.module_account = False
        self._check_tax_report_content()

    def test_pos_tax_report_invoice(self):
        self.pos_config.module_account = True
        self._check_tax_report_content()

    @freeze_time("2020-01-01")
    def _check_tax_report_content(self):
        today = fields.Date.today()
        self.pos_config.open_session_cb()
        self._create_and_pay_pos_order(1, 30)
        self._create_and_pay_pos_order(-1, 40)
        self.pos_config.current_session_id.action_pos_session_closing_control()

        report = self.env['account.generic.tax.report']
        report.flush()
        report_opt = report._get_options({'date': {'period_type': 'custom', 'filter': 'custom', 'date_to': today, 'mode': 'range', 'date_from': today}})
        new_context = report._set_context(report_opt)
        inv_report_lines = report.with_context(new_context)._get_lines(report_opt)
        self.assertLinesValues(
            inv_report_lines,
            #   Name                                                Balance
            [   0,                                                  1],
            [
                (self.pos_tax_report_line_invoice_base.name,        30),
                (self.pos_tax_report_line_invoice_tax.name,         3),
                (self.pos_tax_report_line_refund_base.name,         40),
                (self.pos_tax_report_line_refund_tax.name,          4),
            ],
        )

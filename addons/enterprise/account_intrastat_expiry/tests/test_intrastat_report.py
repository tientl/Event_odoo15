# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged
from odoo import fields
from freezegun import freeze_time


@tagged('post_install', '-at_install')
class IntrastatExpiryReportTest(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        values = [
            {
                'type': type,
                'name': '%s-%s' % (type, date[0]),
                'start_date': date[1],
                'expiry_date': date[2],
            } for type in (
                'commodity',
                'transaction',
            ) for date in (
                ('no_date', False, False),
                ('expired', False, '2000-01-01'),
                ('premature', '2030-01-01', False),
            )
        ]
        cls.intrastat_codes = {}
        for i, vals in enumerate(values, 100):
            vals['code'] = str(i)
            cls.intrastat_codes[vals['name']] = cls.env['account.intrastat.code'].sudo().create(vals)

        cls.company_data['company'].country_id = cls.env.ref('base.be')

        cls.product_c = cls.env['product.product'].create({
            'name': 'product_c',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'lst_price': 1000.0,
            'standard_price': 800.0,
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
            'property_account_expense_id': cls.company_data['default_account_expense'].id,
            'taxes_id': [(6, 0, cls.tax_sale_a.ids)],
            'supplier_taxes_id': [(6, 0, cls.tax_purchase_a.ids)],
        })

    @classmethod
    def _create_invoices(cls, code_type=None):
        moves = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a,
            'invoice_date': fields.Date.from_string('2022-02-01'),
            'intrastat_country_id': cls.env.ref('base.de'),
            'invoice_line_ids': [
                (0, 0, {
                    'name': 'line_1',
                    'product_id': cls.product_a.id,
                    'price_unit': 5.0,
                    'intrastat_transaction_id': cls.intrastat_codes['%s-no_date' % code_type].id if code_type else None,
                    'quantity': 1.0,
                    'account_id': cls.company_data['default_account_revenue'].id,
                }),
                (0, 0, {
                    'name': 'line_2',
                    'product_id': cls.product_b.id,
                    'price_unit': 5.0,
                    'intrastat_transaction_id': cls.intrastat_codes['%s-expired' % code_type].id if code_type else None,
                    'quantity': 1.0,
                    'account_id': cls.company_data['default_account_revenue'].id,
                }),
                (0, 0, {
                    'name': 'line_3',
                    'product_id': cls.product_c.id,
                    'price_unit': 5.0,
                    'intrastat_transaction_id': cls.intrastat_codes['%s-premature' % code_type].id if code_type else None,
                    'quantity': 1.0,
                    'account_id': cls.company_data['default_account_revenue'].id,
                }),
            ],
        })
        moves.action_post()
        cls.cr.flush()  # must flush else SQL request in report is not accurate
        return moves

    @freeze_time('2022-02-01')
    def test_intrastat_report_transaction(self):
        invoice = self._create_invoices('transaction')
        report = self.env['account.intrastat.report']
        options = report._get_options(None)
        options['date']['date_from'] = '1900-01-01'
        options['date']['date_to'] = '2022-12-01'
        options.update({'country_format': 'code'})
        lines = report._get_lines(options)
        self.assertLinesValues(
            # pylint: disable=C0326
            lines,
            #    country code,  transaction code,  origin country
            [    2,             3,                 7   ],
            [
                ('DE',          '103',             'QU'),
                ('DE',          '104',             'QU'),
                ('DE',          '105',             'QU'),
            ],
        )
        self.assertEqual(options['warnings'], {
            'expired_trans': [invoice.id],
            'premature_trans': [invoice.id],
        })

    @freeze_time('2022-02-01')
    def test_intrastat_report_commodity_on_products(self):
        self.product_a.intrastat_id = self.intrastat_codes['commodity-no_date']
        self.product_b.intrastat_id = self.intrastat_codes['commodity-expired']
        self.product_c.intrastat_id = self.intrastat_codes['commodity-premature']
        self._create_invoices()
        report = self.env['account.intrastat.report']
        options = report._get_options(None)
        options['date']['date_from'] = '1900-01-01'
        options['date']['date_to'] = '2022-12-01'
        options.update({'country_format': 'code'})
        lines = report._get_lines(options)
        self.assertLinesValues(
            # pylint: disable=C0326
            lines,
            #    country code,  transaction code,  commodity code,  origin country
            [    2,             3,                 5,               7  ],
            [
                ('DE',          11,                '100',          'QU'),
                ('DE',          11,                '101',          'QU'),
                ('DE',          11,                '102',          'QU'),
            ],
        )
        self.assertEqual(options['warnings'], {
            'expired_comm': [self.product_b.id],
            'premature_comm': [self.product_c.id],
        })

    @freeze_time('2022-02-01')
    def test_intrastat_report_commodity_on_product_categories(self):
        self.product_a.categ_id = self.env['product.category'].create({
            'name': 'categ_a',
            'intrastat_id': self.intrastat_codes['commodity-no_date'].id,
        })
        self.product_b.categ_id = self.env['product.category'].create({
            'name': 'categ_b',
            'intrastat_id': self.intrastat_codes['commodity-expired'].id,
        })
        self.product_c.categ_id = self.env['product.category'].create({
            'name': 'categ_c',
            'intrastat_id': self.intrastat_codes['commodity-premature'].id,
        })
        self._create_invoices()
        report = self.env['account.intrastat.report']
        options = report._get_options(None)
        options['date']['date_from'] = '1900-01-01'
        options['date']['date_to'] = '2022-12-01'
        options.update({'country_format': 'code'})
        lines = report._get_lines(options)
        self.assertLinesValues(
            # pylint: disable=C0326
            lines,
            #    country code,  transaction code,  commodity code,  origin country
            [    2,             3,                 5,               7  ],
            [
                ('DE',          11,                '100',          'QU'),
                ('DE',          11,                '101',          'QU'),
                ('DE',          11,                '102',          'QU'),
            ],
        )
        self.assertEqual(options['warnings'], {
            'expired_categ_comm': [self.product_b.categ_id.id],
            'premature_categ_comm': [self.product_c.categ_id.id],
        })

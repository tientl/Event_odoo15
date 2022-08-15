# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account_reports.tests.account_sales_report_common import AccountSalesReportCommon
from odoo.tests import tagged
from odoo.tools.misc import NON_BREAKING_SPACE
from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class SwedishSalesReportTest(AccountSalesReportCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_se.l10nse_chart_template'):
        super().setUpClass(chart_template_ref)

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        res = super().setup_company_data(company_name, chart_template=chart_template, **kwargs)
        res['company'].update({
            'country_id': cls.env.ref('base.se').id,
            'vat': 'SE123456789701',
        })
        res['company'].partner_id.update({
            'email': 'jsmith@mail.com',
            'phone': '+32475123456',
        })
        return res

    @freeze_time('2019-12-31')
    def test_ec_sales_report(self):
        goods_tax = self.env['account.tax'].search([('name', '=', 'Momsfri Försäljning av varor EU'), ('company_id', '=', self.company_data['company'].id)])[0]
        triangular_tax = self.env['account.tax'].search([('name', '=like', 'Trepartshandel%'), ('company_id', '=', self.company_data['company'].id)])[0]
        services_tax = self.env['account.tax'].search([('name', '=', 'Momsfri försäljning av tjänst EU'), ('company_id', '=', self.company_data['company'].id)])[0]
        self._create_invoices([
            (self.partner_a, goods_tax, 3000),
            (self.partner_a, goods_tax, 3000),
            (self.partner_a, services_tax, 7000),
            (self.partner_b, services_tax, 4000),
            (self.partner_b, triangular_tax, 2000),
        ])
        report = self.env['account.sales.report']
        options = report._get_options(None)
        self.assertEqual(report._get_report_country_code(options), 'SE', "The country chosen for EC Sales list should be Sweden")
        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            # Partner, VAT Number, Goods_Amount, Triangular_Amount, Service_Amount
            [0, 1, 2, 3, 4],
            [
                (self.partner_a.name, self.partner_a.vat, f'6,000.00{NON_BREAKING_SPACE}kr', '', f'7,000.00{NON_BREAKING_SPACE}kr'),
                (self.partner_b.name, self.partner_b.vat, '', f'2,000.00{NON_BREAKING_SPACE}kr', f'4,000.00{NON_BREAKING_SPACE}kr'),
            ],
        )
        self.assertTrue(report._get_kvr(options), "Error creating KVR")

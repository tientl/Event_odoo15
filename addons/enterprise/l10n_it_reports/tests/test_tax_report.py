# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItalianTaxReport(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_it.l10n_it_chart_template_generic'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company_data['company'].country_id = cls.env.ref('base.it')

        cls.tax_4v = cls.env['account.tax'].search([('company_id', '=', cls.company_data['company'].id),
                                                    ('name', '=', 'Iva al 4% (debito)')])
        cls.tax_4a = cls.env['account.tax'].search([('company_id', '=', cls.company_data['company'].id),
                                                    ('name', '=', 'Iva al 4% (credito)')])

        cls.tax_4v.tax_group_id.property_tax_payable_account_id = cls.company_data['default_account_payable']

    def test_tax_report_carryover_vp14_credit_period(self):
        """
        Test to have a value in line vp14 credit at a period inside the year.
        In this case, we should put that value in line vp8.
        """
        report = self.env['account.generic.tax.report']
        self._test_line_report_carryover(
            '2015-03-10',
            1000,
            self.tax_4a,
            self._init_options(
                report,
                fields.Date.from_string('2015-03-01'),
                fields.Date.from_string('2015-03-31')),
            self._init_options(
                report,
                fields.Date.from_string('2015-04-01'),
                fields.Date.from_string('2015-04-30')),
            'VP8',
            40.0)

    def test_tax_report_carryover_vp14_credit_year(self):
        """
        Test to have a value in line vp14 credit at the last period of the year.
        In this case, we should put that value in line vp9.
        """
        report = self.env['account.generic.tax.report']
        self._test_line_report_carryover(
            '2015-12-10',
            1000,
            self.tax_4a,
            self._init_options(
                report,
                fields.Date.from_string('2015-12-01'),
                fields.Date.from_string('2015-12-31')),
            self._init_options(
                report,
                fields.Date.from_string('2016-01-01'),
                fields.Date.from_string('2016-01-30')),
            'VP9',
            40.0)

    def test_tax_report_carryover_vp14_debit_valid(self):
        """
        Test to have a value in line vp14 debit between 0 and 25.82.
        In this case, we should put that value in line vp7.
        """
        report = self.env['account.generic.tax.report']
        self._test_line_report_carryover(
            '2015-05-10',
            500,
            self.tax_4v,
            self._init_options(
                report,
                fields.Date.from_string('2015-05-01'),
                fields.Date.from_string('2015-05-31')),
            self._init_options(
                report,
                fields.Date.from_string('2015-06-01'),
                fields.Date.from_string('2015-06-30')),
            'VP7',
            20.0)

    def test_tax_report_carryover_vp14_debit_invalid(self):
        """
        Test to have a value in line vp14 debit > 25.82.
        In this case, we should never put that value in line vp7.
        """
        report = self.env['account.generic.tax.report']
        self._test_line_report_carryover(
            '2015-05-10',
            1000,
            self.tax_4v,
            self._init_options(
                report,
                fields.Date.from_string('2015-05-01'),
                fields.Date.from_string('2015-05-31')),
            self._init_options(
                report,
                fields.Date.from_string('2015-06-01'),
                fields.Date.from_string('2015-06-30')),
            'VP7',
            0.0)

    def _test_line_report_carryover(self, invoice_date, invoice_amount, tax_line,
                                    first_month_options, second_month_options,
                                    target_line_code, target_line_value):
        def _get_attachment(*args, **kwargs):
            return []
        report = self.env['account.generic.tax.report']

        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.ref("base.res_partner_12"),
            'date': invoice_date,
            'invoice_date': invoice_date,
            'invoice_line_ids': [
                (0, 0, {
                    'name': 'Product A',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': invoice_amount,
                    'quantity': 1,
                    'tax_ids': tax_line,
                }),
            ],
        })
        invoice._post()

        with patch.object(type(report), '_get_vat_report_attachments', autospec=True, side_effect=_get_attachment):
            vat_closing_move = report._generate_tax_closing_entries(first_month_options)
            vat_closing_move._post()

            # Get to the next month
            report_lines = report._get_lines(second_month_options)
            line = [line for line in report_lines if line['line_code'] == target_line_code][0]

            self.assertEqual(line['columns'][0]['balance'], target_line_value)

    def _init_options(self, report, date_from, date_to):
        return report._get_options({'date': {
            'date_from': date_from.strftime(DEFAULT_SERVER_DATE_FORMAT),
            'date_to': date_to.strftime(DEFAULT_SERVER_DATE_FORMAT),
            'filter': 'custom',
            'mode': report.filter_date.get('mode', 'range'),
        }})

# -*- coding: utf-8 -*-
from unittest.mock import patch

from .common import TestAccountReportsCommon
from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import Form


@tagged('post_install', '-at_install')
class TestTaxReportCarryover(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        company = cls.company_data['company']
        company2 = cls.company_data_2['company']

        fiscal_country = cls.env['res.country'].create({
            'name': "L'Île de la Mouche",
            'code': 'YY',
        })
        company.country_id = company2.country_id = fiscal_country.id
        company.account_tax_periodicity = company2.account_tax_periodicity = 'trimester'
        company2.currency_id = company.currency_id

        company.chart_template_id.country_id = fiscal_country.id

        cls.tax_report = cls.env['account.tax.report'].create({
            'name': 'Test',
            'country_id': company.account_fiscal_country_id.id,
        })

        cls.tax_42_line = cls._create_tax_report_line('Base 42%', cls.tax_report, sequence=1, tag_name='base_42',
                                                      carry_over_condition='no_negative_amount_carry_over_condition')
        cls.tax_11_line = cls._create_tax_report_line('Base 11%', cls.tax_report, sequence=2, tag_name='base_11')

        cls.tax_22_line = cls._create_tax_report_line('Base 22%', cls.tax_report, sequence=3, tag_name='base_22',
                                                      is_carryover_used_in_balance=True)
        cls.tax_27_line = cls._create_tax_report_line('Base 27%', cls.tax_report, sequence=4, tag_name='base_27',
                                                      carry_over_condition='always_carry_over_and_set_to_0',
                                                      carry_over_destination_line_id=cls.tax_22_line.id,
                                                      is_carryover_persistent=False)

    def _trigger_carryover_line_creation(self, company_data, tax_lines, with_reversal=True):
        taxes = self._configure_tax_for_company(company_data, tax_lines)

        # Trigger the creation of a carryover line for the selected company
        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'journal_id': company_data['default_journal_purchase'].id,
            'invoice_date': '2020-03-31',
            'invoice_line_ids': [
                (0, 0, {
                    'name': 'Turlututu',
                    'price_unit': 100.0,
                    'quantity': 1,
                    'account_id': company_data['default_account_expense'].id,
                    'tax_ids': [(6, 0, tax.ids)]}) for tax in taxes
            ],
        })
        invoice.action_post()

        # Generate the report and check the results
        report = self.env['account.generic.tax.report'].with_company(company_data['company'])
        options = self._init_options(report, invoice.date, invoice.date)
        options['tax_report'] = self.tax_report.id
        report = report.with_context(report._set_context(options))

        # Invalidate the cache to ensure the lines will be fetched in the right order.
        report.invalidate_cache()

        if with_reversal:
            # We refund the invoice
            refund_wizard = self.env['account.move.reversal'].with_context(active_model="account.move",
                                                                           active_ids=invoice.ids).create(
                {
                    'reason': 'Test refund tax repartition',
                    'refund_method': 'refund',
                    'date': '2020-03-31',
                    'journal_id': invoice.journal_id.id,
                })
            res = refund_wizard.reverse_moves()
            refund = self.env['account.move'].browse(res['res_id'])

            # Change the value of the line with tax 42 to get a negative value on the report
            move_form = Form(refund)
            with move_form.invoice_line_ids.edit(1) as line_form:
                line_form.price_unit = 200
            move_form.save()

            refund.action_post()

        # return the information needed to do further tests if needed
        return report, taxes, invoice

    def _configure_tax_for_company(self, company_data, tax_lines):
        company = company_data['company']

        tax_group_purchase = self.env['account.tax.group'].with_company(company).sudo().create({
            'name': 'tax_group_purchase',
            'property_tax_receivable_account_id': company_data['default_account_receivable'].copy().id,
            'property_tax_payable_account_id': company_data['default_account_payable'].copy().id,
        })

        taxes = []

        for line in tax_lines:
            amount = line.tag_name.split('_')[1]
            template = self.env['account.tax.template'].create({
                'name': 'Test tax template',
                'tax_group_id': tax_group_purchase.id,
                'amount': amount,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'chart_template_id': company.chart_template_id.id,
                'invoice_repartition_line_ids': [
                    (0, 0, {
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'use_in_tax_closing': True
                    }),
                    (0, 0, {
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'plus_report_line_ids': [line.id],
                        'use_in_tax_closing': True
                    }),
                ],
                'refund_repartition_line_ids': [
                    (0, 0, {
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'use_in_tax_closing': True
                    }),
                    (0, 0, {
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'minus_report_line_ids': [line.id],
                        'use_in_tax_closing': True
                    }),
                ],
            })

            # The templates needs an xmlid in order so that we can call _generate_tax
            self.env['ir.model.data'].create({
                'name': 'account_reports.test_tax_report_tax_'+amount+'_'+company.name,
                'module': 'account_reports',
                'res_id': template.id,
                'model': 'account.tax.template',
            })
            tax = template._generate_tax(company)['tax_template_to_tax'][template]
            taxes.append(tax)

        return taxes

    def _check_carryover_test_result(self, invoice, report, company_data, expected_value, tax_line):
        options = self._init_options(report, invoice.date, invoice.date)
        # Due to warning in runbot when printing wkhtmltopdf in the test, patch the method that fetch the pdf in order
        # to return an empty attachment.
        with patch.object(type(report), '_get_vat_report_attachments', autospec=True,
                          side_effect=lambda *args, **kwargs: []):
            # Generate and post the vat closing move. This should trigger the carry over
            # And create a carry over line for the tax line 42
            vat_closing_move = report._generate_tax_closing_entries(options)
            vat_closing_move.action_post()

            # The negative amount on the line 42 (which is using carry over) was -42.
            # This amount will be carried over to the future in the tax line
            # The with company is necessary to ensure that it is the same as the one of the report
            domain = tax_line.with_company(company_data['company'])._get_carryover_lines_domain(options)
            carryover_lines = self.env['account.tax.carryover.line'].search(domain)
            carried_over_sum = sum([line.amount for line in carryover_lines])
            self.assertEqual(carried_over_sum, expected_value)

    def test_tax_report_carry_over(self):
        report, taxes, invoice = self._trigger_carryover_line_creation(self.company_data, [self.tax_11_line,
                                                                                           self.tax_42_line])

        # ====== Test the current value, based on the invoice created earlier ======

        self._check_carryover_test_result(invoice, report, self.company_data, -42.0, self.tax_42_line)

        # ====== Add a new invoice later than this period, reducing slightly the carried over amount ======

        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'journal_id': self.company_data['default_journal_purchase'].id,
            'invoice_date': '2020-06-30',
            'invoice_line_ids': [(0, 0, {
                'name': 'Turlututu',
                'price_unit': 50.0,
                'quantity': 1,
                'account_id': self.company_data['default_account_expense'].id,
                'tax_ids': [(6, 0, taxes[1].ids)],
                })],
        })
        invoice.action_post()
        self._check_carryover_test_result(invoice, report, self.company_data, -21.0, self.tax_42_line)

        # ====== Add another invoice to stop the carry over ======

        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'journal_id': self.company_data['default_journal_purchase'].id,
            'invoice_date': '2020-09-30',
            'invoice_line_ids': [(0, 0, {
                'name': 'Turlututu',
                'price_unit': 500.0,
                'quantity': 1,
                'account_id': self.company_data['default_account_expense'].id,
                'tax_ids': [(6, 0, taxes[1].ids)],
            })],
        })
        invoice.action_post()
        self._check_carryover_test_result(invoice, report, self.company_data, 0.0, self.tax_42_line)

    def test_tax_report_carry_over_multi_company(self):
        """
        Setup the creation of a carryover line in both companies.
        If the multi-company is working properly, the second one should not get the line from the first one.
        """
        report, _, invoice = self._trigger_carryover_line_creation(self.company_data_2, [self.tax_11_line,
                                                                                         self.tax_42_line])
        self._check_carryover_test_result(invoice, report, self.company_data_2, -42.0, self.tax_42_line)
        report, _, invoice = self._trigger_carryover_line_creation(self.company_data, [self.tax_11_line,
                                                                                       self.tax_42_line])
        self._check_carryover_test_result(invoice, report, self.company_data, -42.0, self.tax_42_line)

    def test_tax_report_carry_over_non_persistent_and_used_in_balance(self):
        # Create a move with 100$ 21% tax
        report, taxes, invoice = self._trigger_carryover_line_creation(self.company_data, [self.tax_27_line], False)

        # Then close the period to trigger the carryover line creation
        # Line 27 carry over to line 22, so we check this one and make sure it has a carryover balance of 27
        self._check_carryover_test_result(invoice, report, self.company_data, 27.0, self.tax_22_line)

        # Get the report for the next period to test that the carryover is used in the balance
        options = self._init_options(report, fields.Date.from_string('2020-04-30'),
                                     fields.Date.from_string('2020-04-30'))
        lines = report._get_lines(options)
        line_id = report._get_generic_line_id('account.tax.report.line', self.tax_22_line.id)
        line_22 = [line for line in lines if line['id'] == line_id][0]

        # The balance of the line 22 for the next period is the balance of its carryover from last period.
        self.assertEqual(line_22['columns'][0]['balance'], 27.0)

        # Close the current period again. It should trigger a carryover from line 27 to line 22.
        # even if it is empty, to reset the balance since it is not persistent and should be at 0 if there
        # as been nothing in a period.
        with patch.object(type(report), '_get_vat_report_attachments', autospec=True,
                          side_effect=lambda *args, **kwargs: []):
            vat_closing_move = report._generate_tax_closing_entries(options)
            vat_closing_move.action_post()

            # Directly check the carryover lines. Because no move has been made during the last period,
            # it should have been balanced to go back to 0
            domain = self.tax_22_line.with_company(self.company_data['company'])._get_carryover_lines_domain(options)
            carryover_lines = self.env['account.tax.carryover.line'].search(domain)
            carried_over_sum = sum([line.amount for line in carryover_lines])
            self.assertEqual(carried_over_sum, 0)

    def test_tax_report_carry_over_non_persistent_and_used_in_balance_with_empty_period(self):
        tax_25_line = self._create_tax_report_line('Base 25%', self.tax_report, sequence=5, tag_name='base_25',
                                                   code='t25', is_carryover_used_in_balance=True)
        tax_32_line = self._create_tax_report_line('Total line', self.tax_report, sequence=6,
                                                   carry_over_condition='always_carry_over_and_set_to_0',
                                                   formula='t25',
                                                   carry_over_destination_line_id=tax_25_line.id,
                                                   is_carryover_persistent=False)
        # Create a move with 100$ 25% tax
        report, taxes, invoice = self._trigger_carryover_line_creation(self.company_data, [tax_25_line], False)

        # Then close the period to trigger the carryover line creation
        # Line 32 is using line 25 in its formula, and will carry over to line 25 of next period
        # So we check this one and make sure it has a carryover balance of 25
        self._check_carryover_test_result(invoice, report, self.company_data, 25.0, tax_25_line)

        # Get the report for the next period to test that the carryover is used in the balance
        options = self._init_options(report, fields.Date.from_string('2020-04-30'), fields.Date.from_string('2020-04-30'))
        lines = report._get_lines(options)
        line_id = report._get_generic_line_id('account.tax.report.line', tax_25_line.id)
        line_25 = [line for line in lines if line['id'] == line_id][0]

        # The balance of the line 25 for the next period is the balance of its carryover from last period.
        self.assertEqual(line_25['columns'][0]['balance'], 25.0)

        # Close the current period again. As no changes were done and 32 is using 25 in the formula, the amount should
        # Be the same. Thus, there should be no new carryover line.
        with patch.object(type(report), '_get_vat_report_attachments', autospec=True, side_effect=lambda *args, **kwargs: []):
            vat_closing_move = report._generate_tax_closing_entries(options)
            vat_closing_move.action_post()

            # Directly check the carryover lines. As the carried over balance is the same as the last period, no
            # new move has been added
            domain = tax_25_line.with_company(self.company_data['company'])._get_carryover_lines_domain(options)
            carryover_lines = self.env['account.tax.carryover.line'].search(domain)
            self.assertEqual(len(carryover_lines), 1)
            # Get the report for the next period again
            options = self._init_options(report, fields.Date.from_string('2020-05-30'), fields.Date.from_string('2020-05-30'))
            lines = report._get_lines(options)
            line_id = report._get_generic_line_id('account.tax.report.line', tax_25_line.id)
            line_25 = [line for line in lines if line['id'] == line_id][0]

            # The balance of the line 25 for the next period is the same as the last period as no changes occurred.
            self.assertEqual(line_25['columns'][0]['balance'], 25.0)

# -*- coding: utf-8 -*-

from odoo import models, _


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        for move in self.filtered(lambda m: not m.posted_before and m.tax_closing_end_date):
            # Make sure to use the company of the move for the carryover operations
            AccountGenericTaxReport = self.env['account.generic.tax.report'].with_company(move.journal_id.company_id)
            # When working with carried over lines, update the tax line with the changes when posting the period move
            options = move._get_report_options_from_tax_closing_entry()
            new_context = AccountGenericTaxReport._set_context(options)
            report_lines = AccountGenericTaxReport.with_context(new_context)._get_lines(options)

            for line in [line for line in report_lines if line['columns'][0].get('carryover_bounds', False)]:
                line_balance = line['columns'][0]['balance']
                carryover_bounds = line['columns'][0].get('carryover_bounds')
                tax_line_id = AccountGenericTaxReport._parse_line_id(line['id'])[-1][2]

                tax_line = self.env['account.tax.report.line'].browse(tax_line_id)
                carry_to_line = tax_line._get_carryover_destination_line(options)

                country_id = self.env['account.tax.report'].browse(options['tax_report']).country_id
                reports = self.env['account.tax.report'].search([('country_id', '=', country_id.id)])

                for report in reports:
                    options['tax_report_option'] = report.id

                    # We get the old carryover balance balance at the time of this period.
                    old_carryover_balance = AccountGenericTaxReport.get_carried_over_balance_before_date(
                        carry_to_line, options)
                    # We also get the new carryover balance we are expecting after the end of this period.
                    dummy, carryover_balance = AccountGenericTaxReport.get_amounts_after_carryover(
                        carry_to_line, line_balance, carryover_bounds, options, 0, tax_line.is_carryover_persistent)

                    carryover_delta = carryover_balance - old_carryover_balance

                    if options['fiscal_position'] == 'domestic':
                        fiscal_position_id = False
                    else:
                        fiscal_position_id = options['fiscal_position']

                    amount = 0
                    if not move.currency_id.is_zero(carryover_delta):
                        amount = carryover_delta

                    if not move.currency_id.is_zero(amount):
                        self.env['account.tax.carryover.line'].create({
                            'name': _('Carryover for period %s to %s', new_context['date_from'], new_context['date_to']),
                            'amount': amount,
                            'date': new_context['date_to'],
                            'tax_report_line_id': carry_to_line.id,
                            'foreign_vat_fiscal_position_id': fiscal_position_id,
                            'company_id': move.company_id.id
                        })

        return super()._post(soft)

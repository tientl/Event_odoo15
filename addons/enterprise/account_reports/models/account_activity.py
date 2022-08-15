# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools import date_utils
from odoo.tools.misc import format_date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
import json
import base64

class AccountMove(models.Model):
    _inherit = "account.move"

    tax_closing_end_date = fields.Date(help="Technical field used for VAT closing, containig the end date of the period this entry closes.")
    tax_report_control_error = fields.Boolean(help="technical field used to know if there was a failed control check")

    def action_open_tax_report(self):
        action = self.env["ir.actions.actions"]._for_xml_id("account_reports.action_account_report_gt")
        options = self._get_report_options_from_tax_closing_entry()
        # Pass options in context and set ignore_session: read to prevent reading previous options
        action.update({'params': {'options': options, 'ignore_session': 'read'}})
        return action

    def refresh_tax_entry(self):
        for move in self.filtered(lambda m: m.tax_closing_end_date and m.state == 'draft'):
            options = move._get_report_options_from_tax_closing_entry()
            ctx = move.env['account.report']._set_context(options)
            ctx['strict_range'] = True
            move.env['account.generic.tax.report'].with_context(ctx)._generate_tax_closing_entries(options, closing_moves=move)

    def _get_report_options_from_tax_closing_entry(self):
        self.ensure_one()
        date_to = self.tax_closing_end_date
        # Take the periodicity of tax report from the company and compute the starting period date.
        delay = self.company_id._get_tax_periodicity_months_delay() - 1
        date_from = date_utils.start_of(date_to + relativedelta(months=-delay), 'month')

        # In case the company submits its report in different regions, a closing entry
        # is made for each fiscal position defining a foreign VAT.
        # We hence need to make sure to select a tax report in the right country when opening
        # the report (in case there are many, we pick the first one available; it doesn't impact the closing)
        if self.fiscal_position_id.foreign_vat:
            fpos_option = self.fiscal_position_id.id
            report_country = self.fiscal_position_id.country_id
        else:
            fpos_option = 'domestic'
            report_country = self.company_id.account_fiscal_country_id

        tax_report = self.env['account.tax.report'].search([('country_id', '=', report_country.id)], limit=1)
        tax_report_option = tax_report.id if tax_report else 'generic'

        options = {
            'date': {
                'date_from': fields.Date.to_string(date_from),
                'date_to': fields.Date.to_string(date_to),
                'filter': 'custom',
                'mode': 'range',
            },
            'fiscal_position': fpos_option,
            'tax_report': tax_report_option,
            'tax_unit': 'company_only',
        }

        return self.env['account.generic.tax.report']._get_options(options)

    def _close_tax_entry(self):
        """ Closes tax closing entries. The tax closing activities on them will be marked done, and the next tax closing entry
        will be generated or updated (if already existing). Also, a pdf of the tax report at the time of closing
        will be posted in the chatter of each move.

        The tax lock date of each  move's company will be set to the move's date in case no other draft tax closing
        move exists for that company (whatever their foreign VAT fiscal position) before or at that date, meaning that
        all the tax closings have been performed so far.
        """
        if not self.user_has_groups('account.group_account_manager'):
                raise UserError(_('Only Billing Administrators are allowed to change lock dates!'))

        tax_closing_activity_type = self.env.ref('account_reports.tax_closing_activity_type')

        for move in self:
            # Change lock date to end date of the period, if all other tax closing moves before this one have been treated
            open_previous_closing = self.env['account.move'].search([
                ('activity_ids.activity_type_id', '=', tax_closing_activity_type.id),
                ('company_id', '=', move.company_id.id),
                ('date', '<=', move.date),
                ('state', '=', 'draft'),
                ('id', '!=', move.id),
            ], limit=1)

            if not open_previous_closing:
                move.company_id.sudo().tax_lock_date = move.tax_closing_end_date

            # Add pdf report as attachment to move
            options = move._get_report_options_from_tax_closing_entry()
            ctx = self.env['account.report']._set_context(options)
            ctx['strict_range'] = True
            attachments = self.env['account.generic.tax.report'].with_context(ctx)._get_vat_report_attachments(options)

            # End activity
            activity = move.activity_ids.filtered(lambda m: m.activity_type_id.id == tax_closing_activity_type.id)
            if activity:
                activity.action_done()

            # Post the message with the PDF
            subject = _('Vat closing from %s to %s') % (format_date(self.env, options.get('date').get('date_from')), format_date(self.env, options.get('date').get('date_to')))
            move.with_context(no_new_invoice=True).message_post(body=move.ref, subject=subject, attachments=attachments)

            # Create the recurring entry (new draft move and new activity)
            if move.fiscal_position_id.foreign_vat:
                next_closing_params = {'fiscal_positions': move.fiscal_position_id}
            else:
                next_closing_params = {'include_domestic': True}
            move.company_id._get_and_update_tax_closing_moves(move.tax_closing_end_date + relativedelta(days=1), **next_closing_params)

    def _post(self, soft=True):
        # When posting entry, generate the pdf and next activity for the tax moves.
        tax_return_moves = self.filtered(lambda m: m.tax_closing_end_date)
        if tax_return_moves:
            tax_return_moves._close_tax_entry()
        return super()._post(soft)


class AccountTaxReportActivityType(models.Model):
    _inherit = "mail.activity.type"

    category = fields.Selection(selection_add=[('tax_report', 'Tax report')])

class AccountTaxReportActivity(models.Model):
    _inherit = "mail.activity"

    def action_open_tax_report(self):
        self.ensure_one()
        move = self.env['account.move'].browse(self.res_id)
        return move.action_open_tax_report()

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.osv import expression


class AccountMove(models.Model):
    _inherit = "account.move"

    attachment_ids = fields.One2many('ir.attachment', 'res_id', domain=[('res_model', '=', 'account.move')], string='Attachments')
    payment_state_before_switch = fields.Char(string="Payment State Before Switch", copy=False,
                                              help="Technical field to keep the value of payment_state when switching from invoicing to accounting "\
                                                   "(using invoicing_switch_threshold setting field). It allows keeping the former payment state, so that "\
                                                   "we can restore it if the user misconfigured the switch date and wants to change it.")

    def action_open_matching_suspense_moves(self):
        self.ensure_one()
        domain = self._get_domain_matching_suspense_moves()
        ids = self.env['account.move.line'].search(domain).mapped('statement_line_id').ids
        action_context = {'show_mode_selector': False, 'company_ids': self.mapped('company_id').ids}
        action_context.update({'suspense_moves_mode': True})
        action_context.update({'statement_line_ids': ids})
        action_context.update({'partner_id': self.partner_id.id})
        action_context.update({'partner_name': self.partner_id.name})
        return {
            'type': 'ir.actions.client',
            'tag': 'bank_statement_reconciliation_view',
            'context': action_context,
        }

    @api.model
    def _get_invoice_in_payment_state(self):
        # OVERRIDE to enable the 'in_payment' state on invoices.
        return 'in_payment'


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = "account.move.line"

    move_attachment_ids = fields.One2many('ir.attachment', compute='_compute_attachment')

    def _compute_attachment(self):
        for record in self:
            record.move_attachment_ids = self.env['ir.attachment'].search(expression.OR(record._get_attachment_domains()))

    def action_reconcile(self):
        """ This function is called by the 'Reconcile' action of account.move.line's
        tree view. It performs reconciliation between the selected lines, or, if they
        only consist of payable and receivable lines for the same partner, it opens
        the transfer wizard, pre-filled with the necessary data to transfer
        the payable/receivable open balance into the receivable/payable's one.
        This way, we can simulate reconciliation between receivable and payable
        accounts, using an intermediate account.move doing the transfer.
        """
        all_accounts = self.mapped('account_id')
        account_types = all_accounts.mapped('user_type_id.type')
        all_partners = self.mapped('partner_id')

        if len(all_accounts) == 2 and 'payable' in account_types and 'receivable' in account_types:

            if len(all_partners) != 1:
                raise UserError(_("You cannot reconcile the payable and receivable accounts of multiple partners together at the same time."))

            # In case we have only lines for one (or no) partner and they all
            # are located on a single receivable or payable account,
            # we can simulate reconciliation between them with a transfer entry.
            # So, we open the wizard allowing to do that, pre-filling the values.

            max_total = 0
            max_account = None
            for account in all_accounts:
                account_total = abs(sum(line.balance for line in self.filtered(lambda x: x.account_id == account)))
                if not max_account or max_total < account_total:
                    max_account = account
                    max_total = account_total

            wizard = self.env['account.automatic.entry.wizard'].create({
                'move_line_ids': [(6, 0, self.ids)],
                'destination_account_id': max_account.id,
                'action': 'change_account',
            })

            return {
                'name': _("Transfer Accounts"),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.automatic.entry.wizard',
                'res_id': wizard.id,
                'target': 'new',
                'context': {'active_ids': self.ids, 'active_model': 'account.move.line'},
            }

        return {
            'type': 'ir.actions.client',
            'name': _('Reconcile'),
            'tag': 'manual_reconciliation_view',
            'binding_model_id': self.env['ir.model.data']._xmlid_to_res_id('account.model_account_move_line'),
            'binding_type': 'action',
            'binding_view_types': 'list',
            'context': {'active_ids': self.ids, 'active_model': 'account.move.line'},
        }

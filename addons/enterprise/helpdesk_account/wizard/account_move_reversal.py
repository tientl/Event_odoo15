# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from ast import literal_eval

from odoo import models, fields, api, _


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    @api.model
    def default_get(self, fields):
        result = super(AccountMoveReversal, self).default_get(fields)
        ticket_id = result.get('helpdesk_ticket_id')
        if ticket_id and 'reason' in fields:
            result['reason'] = _('Helpdesk Ticket #%s', ticket_id)
        return result

    helpdesk_ticket_id = fields.Many2one('helpdesk.ticket')
    helpdesk_sale_order_id = fields.Many2one('sale.order', related="helpdesk_ticket_id.sale_order_id", string='Sales Order')
    suitable_move_ids = fields.Many2many('account.move', compute='_compute_suitable_moves')

    @api.depends('helpdesk_ticket_id.sale_order_id.invoice_ids', 'helpdesk_ticket_id.partner_id.commercial_partner_id')
    def _compute_suitable_moves(self):
        for r in self:
            domain = [('state', '=', 'posted'), ('move_type', '=', 'out_invoice')]
            if r.helpdesk_ticket_id.sale_order_id:
                domain.append(('id', 'in', r.helpdesk_ticket_id.sale_order_id.invoice_ids.ids))
            elif r.helpdesk_ticket_id.partner_id:
                domain.append(('partner_id', 'child_of', r.helpdesk_ticket_id.partner_id.commercial_partner_id.id))

            r.suitable_move_ids = self.env['account.move'].search(domain)._origin

    def reverse_moves(self):
        # OVERRIDE
        res = super(AccountMoveReversal, self).reverse_moves()

        if self.helpdesk_ticket_id:
            self.helpdesk_ticket_id.invoice_ids |= self.new_move_ids
            for move_id in self.new_move_ids:
                move_id.message_post_with_view('helpdesk.ticket_creation', values={'self': move_id, 'ticket': self.helpdesk_ticket_id}, subtype_id=self.env.ref('mail.mt_note').id)

        return res

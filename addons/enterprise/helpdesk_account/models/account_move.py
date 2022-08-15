# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class AccountMove(models.Model):
    _inherit = 'account.move'

    def write(self, vals):
        previous_states = None
        if 'state' in vals:
            previous_states = {move: move.state for move in self}
        res = super().write(vals)
        if 'state' in vals and vals['state'] == 'posted':
            tracked_moves = self.filtered(lambda m: m.state != previous_states[m])
            ticket_ids = self.env['helpdesk.ticket'].sudo().search([
                ('use_credit_notes', '=', True), ('invoice_ids', 'in', tracked_moves.ids)])
            if ticket_ids:
                mapped_data = dict()
                for ticket in ticket_ids:
                    mapped_data[ticket] = (ticket.invoice_ids & self)
                subtype_id = self.env.ref('helpdesk.mt_ticket_refund_posted')
                for ticket, invoices in mapped_data.items():
                    if not invoices:
                        continue
                    body = '</br>'.join(('<a href="#" data-oe-model="account.move" data-oe-id="%s">%s</a>' % (invoice.id, invoice.display_name))\
                        for invoice in invoices)
                    ticket.message_post(subtype_id=subtype_id.id, body=body)
        return res

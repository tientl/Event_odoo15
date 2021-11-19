# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _compute_state(self):
        # Since `state` is a computed field, it does not go through the `write` function we usually use to track
        # those changes.
        previous_states = {picking: picking.state for picking in self}
        res = super()._compute_state()
        tracked_pickings = self.filtered(lambda m: m.state == 'done' and\
            m.state != previous_states[m])
        ticket_ids = self.env['helpdesk.ticket'].sudo().search([
            ('use_product_returns', '=', True), ('picking_ids', 'in', tracked_pickings.ids)])
        if ticket_ids:
            mapped_data = dict()
            for ticket in ticket_ids:
                mapped_data[ticket] = (ticket.picking_ids & self)
            subtype_id = self.env.ref('helpdesk.mt_ticket_return_done')
            for ticket, pickings in mapped_data.items():
                if not pickings:
                    continue
                body = '</br>'.join(('<a href="#" data-oe-model="stock.picking" data-oe-id="%s">%s</a>' % (picking.id, picking.display_name))\
                    for picking in pickings)
                ticket.message_post(subtype_id=subtype_id.id, body=body)
        return res

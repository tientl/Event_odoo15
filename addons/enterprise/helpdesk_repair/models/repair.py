# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Repair(models.Model):
    _inherit = 'repair.order'

    ticket_id = fields.Many2one('helpdesk.ticket', string="Ticket", help="Related Helpdesk Ticket")

    def write(self, vals):
        previous_states = None
        if 'state' in vals:
            previous_states = {repair: repair.state for repair in self}
        res = super().write(vals)
        if 'state' in vals:
            tracked_repairs = self.filtered(
                lambda r: r.ticket_id.use_product_repairs and r.state == 'done' and previous_states[r] != r.state)
            subtype_id = self.env.ref('helpdesk.mt_ticket_repair_done')
            for repair in tracked_repairs:
                body = '<a href="#" data-oe-model="repair.order" data-oe-id="%s">%s</a>' % (repair.id, repair.display_name)
                repair.ticket_id.sudo().message_post(subtype_id=subtype_id.id, body=body)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders.filtered('ticket_id'):
            order.message_post_with_view('helpdesk.ticket_creation', values={'self': order, 'ticket': order.ticket_id}, subtype_id=self.env.ref('mail.mt_note').id)
        return orders

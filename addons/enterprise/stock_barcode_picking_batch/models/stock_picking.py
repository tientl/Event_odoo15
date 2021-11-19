
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class StockPicking(models.Model):
    _inherit = "stock.picking"
    display_batch_button = fields.Boolean(compute='_compute_display_batch_button')

    @api.depends('batch_id')
    def _compute_display_batch_button(self):
        for picking in self:
            picking.display_batch_button = picking.batch_id and picking.batch_id.state == 'in_progress'

    def action_open_batch_picking(self):
        self.ensure_one()
        return self.batch_id.action_client_action()

    def action_open_picking_client_action(self):
        self.ensure_one()
        # If this picking isn't a part of a batch, search for other pickings for
        # same partner and ask if the user wants to process them as a batch.
        if not self.env.context.get('pickings_to_batch_ids') and not self.batch_id and self.state == 'assigned' and self.partner_id:
            late_pickings = self.env['stock.picking'].search([
                ('partner_id', '=', self.partner_id.id),
                ('picking_type_id', '=', self.picking_type_id.id),
                ('state', '=', 'assigned'),
            ])
            if len(late_pickings) > 1:
                view = self.env.ref('stock_barcode_picking_batch.view_batch_picking_confirmation')
                return {
                    'name': _('Create New Batch Picking ?'),
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'stock_barcode_picking_batch.group.pickings',
                    'views': [(view.id, 'form')],
                    'view_id': view.id,
                    'target': 'new',
                    'context': dict(
                        self.env.context,
                        default_picking_id=self.id,
                        pickings_to_batch_ids=late_pickings.ids,
                    ),
                }
        return super().action_open_picking_client_action()

    def action_unbatch(self):
        self.ensure_one()
        if self.batch_id:
            self.batch_id = False

    def _get_without_quantities_error_message(self):
        if self.env.context.get('barcode_view'):
            return _(
                'You cannot validate a transfer if no quantities are reserved nor done. '
                'You can use the info button on the top right corner of your screen '
                'to remove the transfer in question from the batch.'
            )
        else:
            return super()._get_without_quantities_error_message()

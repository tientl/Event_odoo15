from odoo import fields, models


class StockBarcodePickingBatchGroupPickings(models.TransientModel):
    _name = 'stock_barcode_picking_batch.group.pickings'
    _description = "Group Pickings into a New Batch"

    partner_id = fields.Many2one(
        'res.partner', 'Contact', related='picking_id.partner_id')
    picking_id = fields.Many2one('stock.picking', required=True, readonly=True)
    picking_type_name = fields.Char(related='picking_id.picking_type_id.name')

    def action_generate_new_batch_picking(self):
        """ Create a new batch picking, then confirm and open it."""
        new_batch = self.env['stock.picking.batch'].create({
            'picking_ids': [(4, p) for p in self.env.context.get('pickings_to_batch_ids', [])],
        })
        new_batch.action_confirm()
        return new_batch.action_client_action()

    def action_open_picking(self):
        return self.picking_id.action_open_picking_client_action()

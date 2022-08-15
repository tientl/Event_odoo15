# -*- coding: utf-8 -*-

from odoo import api, fields, models


class StockMoveLine(models.Model):
    _name = 'stock.move.line'
    _inherit = ['stock.move.line', 'barcodes.barcode_events_mixin']

    product_barcode = fields.Char(related='product_id.barcode')
    location_processed = fields.Boolean()
    dummy_id = fields.Char(compute='_compute_dummy_id', inverse='_inverse_dummy_id')
    picking_location_id = fields.Many2one(related='picking_id.location_id')
    picking_location_dest_id = fields.Many2one(related='picking_id.location_dest_id')
    product_stock_quant_ids = fields.One2many('stock.quant', compute='_compute_product_stock_quant_ids')

    @api.depends('product_id', 'product_id.stock_quant_ids')
    def _compute_product_stock_quant_ids(self):
        for line in self:
            line.product_stock_quant_ids = line.product_id.stock_quant_ids.filtered(lambda q: q.company_id in self.env.companies and q.location_id.usage == 'internal')

    def _compute_dummy_id(self):
        self.dummy_id = ''

    def _inverse_dummy_id(self):
        pass

    def _get_fields_stock_barcode(self):
        return [
            'product_id',
            'location_id',
            'location_dest_id',
            'qty_done',
            'display_name',
            'product_uom_qty',
            'product_uom_id',
            'product_barcode',
            'owner_id',
            'lot_id',
            'lot_name',
            'package_id',
            'result_package_id',
            'dummy_id',
        ]

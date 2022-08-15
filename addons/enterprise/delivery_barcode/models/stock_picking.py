# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class StockPicking(models.Model):
    _name = 'stock.picking'
    _description = 'Transfer'
    _inherit = ['stock.picking', 'barcodes.barcode_events_mixin']

    delivery_package_type_ids = fields.One2many('stock.package.type', compute='_compute_delivery_package_type', store=False)

    @api.depends('carrier_id')
    def _compute_delivery_package_type(self):
        for picking in self:
            picking.delivery_package_type_ids = self.env['stock.package.type'].search(
                [('package_carrier_type', '=', picking.carrier_id.delivery_type)]
            )

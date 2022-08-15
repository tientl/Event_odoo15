# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class QuantPackage(models.Model):
    _inherit = 'stock.quant.package'
    _barcode_field = 'name'

    @api.model
    def action_create_from_barcode(self, vals_list):
        """ Creates a new package then returns its data to be added in the client side cache.
        """
        res = self.create(vals_list)
        return {
            'stock.quant.package': res.read(self._get_fields_stock_barcode(), False)
        }

    @api.model
    def _get_fields_stock_barcode(self):
        return ['name', 'location_id', 'package_type_id', 'quant_ids']

    @api.model
    def _get_usable_packages(self):
        usable_packages_domain = [
            '|',
            ('package_use', '=', 'reusable'),
            ('location_id', '=', False),
        ]
        return self.env['stock.quant.package'].search(usable_packages_domain)

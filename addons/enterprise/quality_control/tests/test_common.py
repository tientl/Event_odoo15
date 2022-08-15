# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestQualityCommon(common.TransactionCase):

    def setUp(self):
        super(TestQualityCommon, self).setUp()

        self.product_category_base = self.env.ref('product.product_category_1')
        self.product_category_1 = self.env['product.category'].create({
            'name': 'Office furnitures',
            'parent_id': self.product_category_base.id
        })
        self.product = self.env['product.product'].create({
            'name': 'Office Chair',
            'categ_id': self.product_category_1.id
        })
        self.product_2 = self.env['product.product'].create({
            'name': 'Test Product',
            'categ_id': self.product_category_base.parent_id.id
        })
        self.product_3 = self.env['product.product'].create({
            'name': 'Another Test Product',
            'categ_id': self.product_category_base.parent_id.id
        })
        self.product_4 = self.env['product.product'].create({
            'name': 'Saleable Product',
            'categ_id': self.product_category_base.id
        })
        self.product_tmpl_id = self.product.product_tmpl_id.id
        self.partner_id = self.env['res.partner'].create({'name': 'A Test Partner'}).id
        self.picking_type_id = self.ref('stock.picking_type_in')
        self.location_id = self.ref('stock.stock_location_suppliers')
        self.location_dest_id = self.ref('stock.stock_location_stock')

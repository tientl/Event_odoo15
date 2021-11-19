# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestQualityMrpCommon(common.TransactionCase):

    def setUp(self):
        super(TestQualityMrpCommon, self).setUp()

        self.product_uom_id = self.ref('uom.product_uom_unit')
        self.product = self.env['product.product'].create({
            'name': 'Drawer',
            'type': 'product',
            'uom_id': self.product_uom_id,
            'uom_po_id': self.product_uom_id,
            'tracking': 'lot',
        })
        self.product_id = self.product.id
        self.product_tmpl_id = self.product.product_tmpl_id.id
        self.picking_type_id = self.env.ref('stock.warehouse0').manu_type_id.id

        product_product_drawer_drawer = self.env['product.product'].create({
            'name': 'Drawer Black',
            'tracking': 'lot'
        })
        product_product_drawer_case = self.env['product.product'].create({
            'name': 'Drawer Case Black',
            'tracking': 'lot'
        })
        self.bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_tmpl_id,
            'product_uom_id': self.product_uom_id,
            'bom_line_ids': [
                (0, 0, {
                    'product_id': product_product_drawer_drawer.id,
                    'product_qty': 1,
                    'product_uom_id': self.product_uom_id,
                    'sequence': 1,
                }), (0, 0, {
                    'product_id': product_product_drawer_case.id,
                    'product_qty': 1,
                    'product_uom_id': self.product_uom_id,
                    'sequence': 1,
                })
            ]
        })
        self.bom_id = self.bom.id

        self.lot_product_27_0 = self.env['stock.production.lot'].create({
            'name': '0000000000030',
            'product_id': self.product_id,
            'company_id': self.env.company.id,
        })
        lot_product_product_drawer_drawer_0 = self.env['stock.production.lot'].create({
            'name': '0000000010001',
            'product_id': product_product_drawer_drawer.id,
            'company_id': self.env.company.id,
        })
        lot_product_product_drawer_case_0 = self.env['stock.production.lot'].create({
            'name': '0000000020045',
            'product_id': product_product_drawer_case.id,
            'company_id': self.env.company.id,
        })

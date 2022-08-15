# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.addons.mrp.tests.common import TestMrpCommon


class TestQualityCheckWorkorder(TestMrpCommon):

    def test_01_quality_check_with_component_consumed_in_operation(self):
        """ Test quality check on a production with a component consumed in one operation
        """

        picking_type_id = self.env.ref('stock.warehouse0').manu_type_id.id
        component = self.env['product.product'].create({
            'name': 'consumable component',
            'type': 'consu',
        })
        bom = self.bom_2.copy()
        bom.bom_line_ids[0].product_id = component

        # Registering the first component in the operation of the BoM
        bom.bom_line_ids[0].operation_id = bom.operation_ids[0]

        # Create Quality Point for the product consumed in the operation of the BoM
        self.env['quality.point'].create({
            'product_ids': [bom.bom_line_ids[0].product_id.id],
            'picking_type_ids': [picking_type_id],
            'measure_on': 'product',
        })
        # Create Quality Point for all products (that should not apply on components)
        self.env['quality.point'].create({
            'product_ids': [],
            'picking_type_ids': [picking_type_id],
            'measure_on': 'product',
        })

        # Create Production of Painted Boat to produce 5.0 Unit.
        production_form = Form(self.env['mrp.production'])
        production_form.product_id = bom.product_id
        production_form.bom_id = bom
        production_form.product_qty = 5.0
        production = production_form.save()
        production.action_confirm()
        production.qty_producing = 3.0

        # Check that the Quality Check were created and has correct values
        self.assertEqual(len(production.move_raw_ids[0].move_line_ids.check_ids), 2)
        self.assertEqual(len(production.move_raw_ids[1].move_line_ids.check_ids), 0)
        self.assertEqual(len(production.move_finished_ids[0].move_line_ids.check_ids), 1)
        self.assertEqual(len(production.check_ids), 2)

        # Registering consumption in tablet view
        wo = production.workorder_ids[0]
        wo.open_tablet_view()
        wo.qty_done = 10.0
        wo.action_next()
        self.assertEqual(len(production.move_raw_ids[0].move_line_ids.check_ids), 2)

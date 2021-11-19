# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo.tests import Form, common
from odoo.addons.industry_fsm_sale.tests.test_industry_fsm_sale_flow import TestFsmFlowSale


@common.tagged('post_install', '-at_install')
class TestFsmFlowStock(TestFsmFlowSale):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        (cls.product_ordered + cls.product_delivered).write({'type': 'product'})
        cls.product_lot = cls.env['product.product'].create({
            'name': 'Acoustic Magic Bloc',
            'list_price': 2950.0,
            'type': 'product',
            'invoice_policy': 'delivery',
            'taxes_id': False,
            'tracking': 'lot',
        })

        cls.lot_id1 = cls.env['stock.production.lot'].create({
            'product_id': cls.product_lot.id,
            'name': "Lot_1",
            'company_id': cls.env.company.id,
        })

        cls.lot_id2 = cls.env['stock.production.lot'].create({
            'product_id': cls.product_lot.id,
            'name': "Lot_2",
            'company_id': cls.env.company.id,
        })

        cls.lot_id3 = cls.env['stock.production.lot'].create({
            'product_id': cls.product_lot.id,
            'name': "Lot_3",
            'company_id': cls.env.company.id,
        })

        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)
        quants = cls.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': cls.product_lot.id,
            'inventory_quantity': 4,
            'lot_id': cls.lot_id1.id,
            'location_id': cls.warehouse.lot_stock_id.id,
        })
        quants |= cls.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': cls.product_lot.id,
            'inventory_quantity': 2,
            'lot_id': cls.lot_id2.id,
            'location_id': cls.warehouse.lot_stock_id.id,
        })
        quants |= cls.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': cls.product_lot.id,
            'inventory_quantity': 2,
            'lot_id': cls.lot_id3.id,
            'location_id': cls.warehouse.lot_stock_id.id,
        })
        quants.action_apply_inventory()

    def test_fsm_flow(self):
        '''
            3 delivery step
            1. Add product and lot on SO
            2. Check that default lot on picking are not the same as chosen on SO
            3. Validate fsm task
            4. Check that lot on validated picking are the same as chosen on SO
        '''
        self.warehouse.delivery_steps = 'pick_pack_ship'

        self.task.write({'partner_id': self.partner_1.id})
        self.task.with_user(self.project_user)._fsm_ensure_sale_order()
        self.task.sale_order_id.write({
            'order_line': [
                (0, 0, {
                    'product_id': self.product_lot.id,
                    'product_uom_qty': 3,
                    'fsm_lot_id': self.lot_id2.id,
                })
            ]
        })
        self.task.sale_order_id.action_confirm()

        move = self.task.sale_order_id.order_line.move_ids
        while move.move_orig_ids:
            move = move.move_orig_ids
        self.assertNotEqual(move.move_line_ids.lot_id, self.lot_id2, "Lot automatically added on move lines is not the same as asked. (By default, it's the first lot available)")
        self.task.with_user(self.project_user).action_fsm_validate()
        self.assertEqual(move.move_line_ids.lot_id, self.lot_id2, "Asked lots are added on move lines.")
        self.assertEqual(move.move_line_ids.qty_done, 3, "We deliver 3 (even they are only 2 in stock)")

        self.assertEqual(self.task.sale_order_id.picking_ids.mapped('state'), ['done', 'done', 'done'], "Pickings should be set as done")

    def test_fsm_mixed_pickings(self):
        '''
            1. Add normal product on SO
            2. Validate fsm task
            3. Check that pickings are not auto validated
        '''
        self.task.write({'partner_id': self.partner_1.id})
        self.task.with_user(self.project_user)._fsm_ensure_sale_order()
        self.task.sale_order_id.write({
            'order_line': [
                (0, 0, {
                    'product_id': self.product_a.id,
                    'product_uom_qty': 1,
                })
            ]
        })
        self.task.sale_order_id.action_confirm()
        self.task.with_user(self.project_user).action_fsm_validate()
        self.assertNotEqual(self.task.sale_order_id.picking_ids.mapped('state'), ['done'], "Pickings should be set as done")

    def test_fsm_flow_with_default_warehouses(self):
        '''
            When the multi warehouses feature is activated, a default warehouse can be set 
            on users. 
            The user set on a task should be propagated from the task to the sales order
            and his default warehouse set as the warehouse of the SO.
            If the customer has a salesperson assigned to him, the creation of a SO
            from a task overrides this to set the user assigned on the task.
        '''
        warehouse_A = self.env['stock.warehouse'].create({'name': 'WH A', 'code': 'WHA', 'company_id': self.env.company.id, 'partner_id': self.env.company.partner_id.id})
        self.partner_1.write({'user_id': self.uid})

        self.project_user.write({'property_warehouse_id': warehouse_A.id})

        self.task.write({'partner_id': self.partner_1.id})
        self.task.with_user(self.project_user)._fsm_ensure_sale_order()

        self.assertEqual(self.project_user.property_warehouse_id.id, self.task.sale_order_id.warehouse_id.id)
        self.assertEqual(self.project_user.id, self.task.sale_order_id.user_id.id)
        

    def test_fsm_stock_already_validated_picking(self):
        '''
            1 delivery step
            1. add product and lot on SO
            2. Validate picking with another lot
            3. Open wizard for lot, and ensure that the lot validated is the one chosen in picking
            4. Add a new lot and quantity in wizard
            5. Validate fsm task
            6. Ensure that lot and quantity are correct
        '''
        self.warehouse.delivery_steps = 'ship_only'

        self.task.write({'partner_id': self.partner_1.id})
        self.task.with_user(self.project_user)._fsm_ensure_sale_order()
        self.task.sale_order_id.write({
            'order_line': [
                (0, 0, {
                    'product_id': self.product_lot.id,
                    'product_uom_qty': 1,
                    'fsm_lot_id': self.lot_id2.id,
                    'task_id': self.task.id,
                })
            ]
        })
        self.task.sale_order_id.action_confirm()

        wizard = self.product_lot.with_context({'fsm_task_id': self.task.id}).action_assign_serial()
        wizard_id = self.env['fsm.stock.tracking'].browse(wizard['res_id'])
        self.assertFalse(wizard_id.tracking_validated_line_ids, "There aren't validated line")
        self.assertEqual(wizard_id.tracking_line_ids.product_id, self.product_lot, "There are one line with the right product")
        self.assertEqual(wizard_id.tracking_line_ids.lot_id, self.lot_id2, "The line has lot_id2")

        move = self.task.sale_order_id.order_line.move_ids
        move.quantity_done = 1
        picking_ids = self.task.sale_order_id.picking_ids
        picking_ids.with_context(skip_sms=True, cancel_backorder=True).button_validate()
        self.assertEqual(picking_ids.mapped('state'), ['done'], "Pickings should be set as done")
        self.assertNotEqual(move.move_line_ids.lot_id, self.lot_id2, "Lot automatically added on move lines is not the same as asked. (By default, it's the first lot available)")

        wizard = self.product_lot.with_context({'fsm_task_id': self.task.id}).action_assign_serial()
        wizard_id = self.env['fsm.stock.tracking'].browse(wizard['res_id'])
        self.assertFalse(wizard_id.tracking_line_ids, "There aren't line to validate")
        self.assertEqual(wizard_id.tracking_validated_line_ids.product_id, self.product_lot, "There are one line with the right product")
        self.assertEqual(wizard_id.tracking_validated_line_ids.lot_id, self.lot_id1, "The line has lot_id1, (not the lot choosed at the beginning, but the lot put in picking)")

        wizard_id.write({
            'tracking_line_ids': [
                (0, 0, {
                    'product_id': self.product_lot.id,
                    'quantity': 3,
                    'lot_id': self.lot_id3.id,
                })
            ]
        })
        wizard_id.generate_lot()

        self.task.with_user(self.project_user).action_fsm_validate()
        order_line_ids = self.task.sale_order_id.order_line.filtered(lambda l: l.product_id == self.product_lot)
        move = order_line_ids.move_ids
        self.assertEqual(len(order_line_ids), 2, "There are 2 order lines.")
        self.assertEqual(move.move_line_ids.lot_id, self.lot_id1 + self.lot_id3, "Lot stay the same.")
        self.assertEqual(sum(move.move_line_ids.mapped('qty_done')), 4, "We deliver 4 (1+3)")

        self.assertEqual(self.task.sale_order_id.picking_ids.mapped('state'), ['done', 'done'], "The 2 pickings should be set as done")

    def test_fsm_stock_validate_half_SOL_manually(self):
        '''
            1 delivery step
            1. add product and lot with wizard
            2. Validate SO
            3. In picking, deliver the half of the quantity of the SOL
            4. Open wizard for lot, and ensure that:
                a. the lot validated is the one chosen in picking
                b. the not yet validated line has the half of the quantity
            5. In wizard, add quantity in the non validated line
            6. Validate fsm task
            7. Ensure that lot and quantity are correct
        '''
        self.warehouse.delivery_steps = 'ship_only'

        self.task.write({'partner_id': self.partner_1.id})
        self.task.with_user(self.project_user)._fsm_ensure_sale_order()

        wizard = self.product_lot.with_context({'fsm_task_id': self.task.id}).action_assign_serial()
        wizard_id = self.env['fsm.stock.tracking'].browse(wizard['res_id'])

        wizard_id.write({
            'tracking_line_ids': [
                (0, 0, {
                    'product_id': self.product_lot.id,
                    'quantity': 5,
                    'lot_id': self.lot_id3.id,
                })
            ]
        })
        wizard_id.generate_lot()

        self.task.sale_order_id.action_confirm()

        order_line_ids = self.task.sale_order_id.order_line.filtered(lambda l: l.product_id == self.product_lot)
        ml_vals = order_line_ids[0].move_ids[0]._prepare_move_line_vals(quantity=0)
        # We chose the quantity to deliver manually
        ml_vals['qty_done'] = 3
        # And we chose the lot
        ml_vals['lot_id'] = self.lot_id2.id
        self.env['stock.move.line'].create(ml_vals)

        # When we validate the picking manually, we create a backorder.
        backorder_wizard_dict = self.task.sale_order_id.picking_ids.button_validate()
        backorder_wizard = Form(self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context'])).save()
        backorder_wizard.process()

        wizard = self.product_lot.with_context({'fsm_task_id': self.task.id}).action_assign_serial()
        wizard_id = self.env['fsm.stock.tracking'].browse(wizard['res_id'])
        self.assertEqual(wizard_id.tracking_line_ids.product_id, self.product_lot, "There are one (non validated) line with the right product")
        self.assertEqual(wizard_id.tracking_line_ids.lot_id, self.lot_id3, "The line has lot_id3, (the lot choosed at the beginning in the wizard)")
        self.assertEqual(wizard_id.tracking_line_ids.quantity, 2, "Quantity is 2 (5 from the beginning in the wizard - 3 already delivered)")
        self.assertEqual(wizard_id.tracking_validated_line_ids.product_id, self.product_lot, "There are one validated line with the right product")
        self.assertEqual(wizard_id.tracking_validated_line_ids.lot_id, self.lot_id2, "The line has lot_id2, (not the lot choosed at the beginning, but the lot put in picking)")
        self.assertEqual(wizard_id.tracking_validated_line_ids.quantity, 3, "Quantity is 3, chosen in the picking")

        # We add 2 to already present quantity on non validated line (2+2=4)
        wizard_id.tracking_line_ids.quantity = 4
        wizard_id.generate_lot()

        self.assertEqual(order_line_ids.product_uom_qty, 7, "Quantity on SOL is 7 (3 already delivered and 4 set in wizard)")
        self.assertEqual(order_line_ids.qty_delivered, 3, "Quantity already delivered is 3, chosen in the picking")

        self.task.with_user(self.project_user).action_fsm_validate()
        order_line_ids = self.task.sale_order_id.order_line.filtered(lambda l: l.product_id == self.product_lot)
        move = order_line_ids.move_ids
        self.assertEqual(len(order_line_ids), 1, "There are 1 order lines, delivered in 2 times (first manually, second with fsm task validation).")
        self.assertEqual(move.move_line_ids.lot_id, self.lot_id2 + self.lot_id3, "Lot stay the same.")
        self.assertEqual(sum(move.move_line_ids.mapped('qty_done')), 7, "We deliver 7 (4+3)")

        self.assertEqual(self.task.sale_order_id.picking_ids.mapped('state'), ['done', 'done'], "The 2 pickings should be set as done")

    def test_action_quantity_set(self):
        self.task.partner_id = self.partner_1
        product = self.product_lot.with_context(fsm_task_id=self.task.id)
        action = product.fsm_add_quantity()
        self.assertEqual(product.fsm_quantity, 0)
        self.assertEqual(action.get('type'), 'ir.actions.act_window', "It should redirect to the tracking wizard")
        self.assertEqual(action.get('res_model'), 'fsm.stock.tracking', "It should redirect to the tracking wizard")

    def test_set_quantity_with_done_so(self):
        self.task.write({'partner_id': self.partner_1.id})
        product = self.product_ordered.with_context({'fsm_task_id': self.task.id})
        product.type = 'consu'
        product.set_fsm_quantity(1)

        so = self.task.sale_order_id
        line01 = so.order_line[-1]
        self.assertEqual(line01.product_uom_qty, 1)
        so.action_confirm()
        so.picking_ids.button_validate()
        validate_form_data = so.picking_ids.button_validate()
        validate_form = Form(self.env[validate_form_data['res_model']].with_context(validate_form_data['context'])).save()
        validate_form.process()

        product.set_fsm_quantity(3)
        self.assertEqual(line01.product_uom_qty, 3)

    def test_validate_task_before_delivery(self):
        """ Suppose a 3-steps delivery. After confirming the two first steps, the user directly validates the task
        The three pickings should be done with a correct value"""
        product = self.product_a
        task = self.task

        # 3 steps
        self.warehouse.delivery_steps = 'pick_pack_ship'

        product.type = 'product'
        self.env['stock.quant']._update_available_quantity(product, self.warehouse.lot_stock_id, 5)

        task.write({'partner_id': self.partner_1.id})
        task.with_user(self.project_user)._fsm_ensure_sale_order()
        so = task.sale_order_id
        so.write({
            'order_line': [
                (0, 0, {
                    'product_id': product.id,
                    'product_uom_qty': 1,
                    'task_id': task.id,
                })
            ]
        })
        so.action_confirm()

        # Confirm two first pickings
        for picking in so.picking_ids.sorted(lambda p: p.id)[:2]:
            picking.move_line_ids_without_package.qty_done = 1
            picking.button_validate()

        task.with_user(self.project_user).action_fsm_validate()

        for picking in so.picking_ids:
            self.assertEqual(picking.state, 'done')
            self.assertEqual(len(picking.move_line_ids_without_package), 1)
            self.assertEqual(picking.move_line_ids_without_package.qty_done, 1)

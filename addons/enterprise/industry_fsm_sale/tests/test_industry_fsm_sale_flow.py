# Part of Odoo. See LICENSE file for full copyright and licensing details

from datetime import datetime
from odoo.addons.industry_fsm_sale.tests.common import TestFsmFlowSaleCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestFsmFlowSale(TestFsmFlowSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.product_delivered = cls.env['product.product'].create({
            'name': 'Acoustic Bloc Screens',
            'list_price': 2950.0,
            'type': 'service',
            'invoice_policy': 'delivery',
            'taxes_id': False,
        })


    # Overriden in industry_fsm_stock, to add another test, create another class
    def test_fsm_flow(self):

        # material
        self.assertFalse(self.task.material_line_product_count, "No product should be linked to a new task")
        with self.assertRaises(UserError, msg='Should not be able to get to material without customer set'):
            self.task.action_fsm_view_material()
        self.task.write({'partner_id': self.partner_1.id})
        self.assertFalse(self.task.task_to_invoice, "Nothing should be invoiceable on task")
        self.task.with_user(self.project_user).action_fsm_view_material()
        self.product_ordered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).fsm_add_quantity()
        self.assertEqual(self.task.material_line_product_count, 1, "1 product should be linked to the task")
        self.product_ordered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).fsm_add_quantity()
        self.assertEqual(self.task.material_line_product_count, 2, "2 product should be linked to the task")
        self.product_delivered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).fsm_add_quantity()
        self.assertEqual(self.task.material_line_product_count, 3, "3 products should be linked to the task")
        self.product_delivered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).fsm_remove_quantity()

        self.assertEqual(self.task.material_line_product_count, 2, "2 product should be linked to the task")

        self.product_delivered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).fsm_add_quantity()

        self.assertEqual(self.task.material_line_product_count, 3, "3 product should be linked to the task")

        # timesheet
        values = {
            'task_id': self.task.id,
            'project_id': self.task.project_id.id,
            'date': datetime.now(),
            'name': 'test timesheet',
            'user_id': self.env.uid,
            'unit_amount': 0.25,
        }
        self.env['account.analytic.line'].create(values)
        self.assertEqual(self.task.material_line_product_count, 3, "Timesheet should not appear in material")

        # validation and SO
        self.assertFalse(self.task.fsm_done, "Task should not be validated")
        self.assertEqual(self.task.sale_order_id.state, 'draft', "Sale order should not be confirmed")
        self.task.with_user(self.project_user).action_fsm_validate()
        self.assertTrue(self.task.fsm_done, "Task should be validated")
        self.assertEqual(self.task.sale_order_id.state, 'sale', "Sale order should be confirmed")

        # invoice
        self.assertTrue(self.task.task_to_invoice, "Task should be invoiceable")
        invoice_ctx = self.task.action_create_invoice()['context']
        invoice_wizard = self.env['sale.advance.payment.inv'].with_context(invoice_ctx).create({})
        invoice_wizard.create_invoices()
        self.assertFalse(self.task.task_to_invoice, "Task should not be invoiceable")

        # quotation
        self.assertEqual(self.task.quotation_count, 1, "1 quotation should be linked to the task")
        quotation = self.env['sale.order'].search([('state', '!=', 'cancel'), ('task_id', '=', self.task.id)])
        self.assertEqual(self.task.action_fsm_view_quotations()['res_id'], quotation.id, "Created quotation id should be in the action")

    def test_change_product_selection(self):
        self.task.write({'partner_id': self.partner_1.id})
        product = self.product_ordered.with_context({'fsm_task_id': self.task.id})
        product.set_fsm_quantity(5)

        so = self.task.sale_order_id
        sol01 = so.order_line[-1]
        self.assertEqual(sol01.product_uom_qty, 5)

        # Manually add a line for the same product
        sol02 = self.env['sale.order.line'].create({
            'order_id': so.id,
            'product_id': product.id,
            'product_uom_qty': 3,
            'product_uom': product.uom_id.id,
            'task_id': self.task.id
        })
        product.sudo()._compute_fsm_quantity()
        self.assertEqual(sol02.product_uom_qty, 3)
        self.assertEqual(product.fsm_quantity, 8)

        product.set_fsm_quantity(2)
        product.sudo()._compute_fsm_quantity()
        self.assertEqual(product.fsm_quantity, 2)
        self.assertEqual(sol01.product_uom_qty, 0)
        self.assertEqual(sol02.product_uom_qty, 2)

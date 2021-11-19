# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details
from freezegun import freeze_time

from odoo.tests import Form, tagged

from odoo.addons.sale_planning.tests.test_sale_planning import TestSalePlanning

@tagged('post_install', '-at_install')
class TestSaleForecast(TestSalePlanning):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.plannable_forecast_product = cls.env['product.product'].create({
            'name': 'Junior Developer Service',
            'type': 'service',
            'planning_enabled': True,
            'planning_role_id': cls.planning_role_junior.id,
            'service_tracking': 'task_in_project',
        })
        cls.plannable_forecast_so = cls.env['sale.order'].create({
            'partner_id': cls.planning_partner.id,
        })
        cls.plannable_forecast_sol = cls.env['sale.order.line'].create({
            'order_id': cls.plannable_forecast_so.id,
            'product_id': cls.plannable_forecast_product.id,
            'product_uom_qty': 10,
        })

    @classmethod
    def setUpEmployees(cls):
        super().setUpEmployees()
        user_group_employee = cls.env.ref('base.group_user')
        user_group_project_user = cls.env.ref('project.group_project_user')
        cls.user_projectuser_wout = cls.env['res.users'].with_context({'no_reset_password': True}).create({
            'name': 'Wout',
            'login': 'Wout',
            'email': 'wout@test.com',
            'groups_id': [(6, 0, [user_group_employee.id, user_group_project_user.id])],
        })
        cls.employee_wout.write({'user_id': cls.user_projectuser_wout.id})

    def test_planning_plan_order_task_assignee(self):
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.planning_partner
        with so_form.order_line.new() as sol_form:
            sol_form.product_id = self.plannable_forecast_product
            sol_form.product_uom_qty = 50
        so = so_form.save()
        so.action_confirm()
        so.order_line.task_id.write({'user_ids': self.user_projectuser_wout})
        Slot = self.env['planning.slot'].with_context(start_date='2021-07-25 00:00:00', stop_date='2021-07-31 23:59:59', scale='week', focus_date='2021-07-31 00:00:00')
        with freeze_time('2021-07-26'):
            Slot.action_plan_sale_order(view_domain=[('start_datetime', '=', '2021-07-25 00:00:00'), ('end_datetime', '=', '2021-07-31 23:59:59')])
        slot = so.order_line.planning_slot_ids.filtered('start_datetime')
        self.assertEqual(slot.employee_id, self.employee_wout, 'Planning should be assigned to the employee with sol\'s product role as default role')

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class SaleOrder(models.Model):
    _inherit = ['sale.order']

    task_id = fields.Many2one('project.task', string="Task", help="Task from which quotation have been created")

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        if self.env.context.get('fsm_no_message_post'):
            return False
        return super().message_post(**kwargs)


class SaleOrderLine(models.Model):
    _inherit = ['sale.order.line']

    def _timesheet_create_task_prepare_values(self, project):
        res = super(SaleOrderLine, self)._timesheet_create_task_prepare_values(project)
        if project.is_fsm:
            res.update({'partner_id': self.order_id.partner_shipping_id.id})
        return res

    def _timesheet_create_project_prepare_values(self):
        """Generate project values"""
        values = super(SaleOrderLine, self)._timesheet_create_project_prepare_values()
        if self.product_id.project_template_id.is_fsm:
            values.pop('sale_line_id', False)
        return values

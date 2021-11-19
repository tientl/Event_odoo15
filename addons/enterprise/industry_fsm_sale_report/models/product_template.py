# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.tools.sql import column_exists, create_column


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _auto_init(self):
        if not column_exists(self.env.cr, "product_template", "worksheet_template_id"):
            create_column(self.env.cr, "product_template", "worksheet_template_id", "int4")

            # This module is auto-installated, so the only way to get non-empty
            # values in the new field is having demo data on installing module
            # dependencies. So, filter the products and call compute method on
            # them only to avoid iterating over all products
            templates = self.search([
                ('service_tracking', 'in', ['task_global_project', 'task_new_project']),
                ('project_id.is_fsm', '=', True),
            ])
            templates._compute_worksheet_template_id()

        return super()._auto_init()

    worksheet_template_id = fields.Many2one(
        'worksheet.template', string="Worksheet Template",
        compute='_compute_worksheet_template_id', store=True, readonly=False)

    @api.depends('service_tracking', 'project_id')
    def _compute_worksheet_template_id(self):
        for template in self:
            if template.service_tracking not in ['task_global_project', 'task_new_project']:
                template.worksheet_template_id = False

            if template.project_id.is_fsm:
                template.worksheet_template_id = template.project_id.worksheet_template_id
            else:
                template.worksheet_template_id = False

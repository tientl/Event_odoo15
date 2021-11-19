# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    schedule_count = fields.Integer('Schedules', compute='_compute_schedule_count')

    def _compute_schedule_count(self):
        for rec in self:
            rec.schedule_count = self.env["mrp.production.schedule"].search_count([('product_id.product_tmpl_id', "=", self.id)])

    def action_open_mps_view(self):
        action = self.env["ir.actions.actions"]._for_xml_id("mrp_mps.action_mrp_mps")
        action['context'] = {"search_default_product_id": self.product_variant_ids.ids}
        return action

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'
    _start_name = "date_planned_start"
    _stop_name = "date_planned_finished"

    check_ids = fields.One2many('quality.check', 'production_id', string="Checks")

    def _generate_backorder_productions(self, close_mo=True):
        backorders = super()._generate_backorder_productions(close_mo=close_mo)
        for wo in backorders.workorder_ids:
            if wo.component_id:
                wo._update_component_quantity()
        return backorders

    def _button_mark_done_sanity_checks(self):
        self.workorder_ids._check_remaining_quality_checks()
        return super()._button_mark_done_sanity_checks()

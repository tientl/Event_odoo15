# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_industry_fsm_report = fields.Boolean("Worksheets")
    module_industry_fsm_sale = fields.Boolean('Time and Material')
    group_industry_fsm_quotations = fields.Boolean(string="Extra Quotations", implied_group="industry_fsm.group_fsm_quotation_from_task")

    @api.model
    def _get_basic_project_domain(self):
        return expression.AND([super()._get_basic_project_domain(), [('is_fsm', '=', False)]])

    @api.onchange('group_industry_fsm_quotations')
    def _onchange_group_industry_fsm_quotations(self):
        if not self.module_industry_fsm_sale and self.group_industry_fsm_quotations:
            self.module_industry_fsm_sale = True

    @api.onchange('module_industry_fsm_sale')
    def _onchange_module_industry_fsm_sale(self):
        if self.group_industry_fsm_quotations and not self.module_industry_fsm_sale:
            self.group_industry_fsm_quotations = False

    def set_values(self):
        if self.group_industry_fsm_quotations and not self.module_industry_fsm_sale:
            self.module_industry_fsm_sale = True
        super().set_values()

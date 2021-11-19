# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    rule_type = fields.Selection(related='company_id.rule_type', readonly=False)
    intercompany_user_id = fields.Many2one(related='company_id.intercompany_user_id', readonly=False, required=True)
    rules_company_id = fields.Many2one(related='company_id', string='Select Company', readonly=True)
    intercompany_transaction_message = fields.Char(compute='_compute_intercompany_transaction_message')

    @api.depends('rule_type', 'company_id')
    def _compute_intercompany_transaction_message(self):
        for record in self:
            record.company_id.rule_type = record.rule_type
            record.intercompany_transaction_message = record.company_id.intercompany_transaction_message

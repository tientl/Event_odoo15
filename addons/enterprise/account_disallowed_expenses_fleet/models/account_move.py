# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.depends('account_id.disallowed_expenses_category_id')
    def _compute_need_vehicle(self):
        for record in self:
            record.need_vehicle = record.account_id.disallowed_expenses_category_id.car_category and record.move_id.move_type == 'in_invoice'

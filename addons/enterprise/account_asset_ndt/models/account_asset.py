# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import formatLang


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    non_deductible_tax_val = fields.Monetary(string="Non Deductible Tax Value", compute="_compute_non_deductible_tax_value", store=True, readonly=True)

    @api.depends('original_move_line_ids')
    def _compute_non_deductible_tax_value(self):
        for record in self:
            record.non_deductible_tax_val = 0.0
            move_lines = record.original_move_line_ids
            non_deductible_tax_value = sum(move_lines.mapped('non_deductible_tax_value'))
            if non_deductible_tax_value:
                account = move_lines.account_id
                auto_create_multi = account.create_asset != 'no' and account.multiple_assets_per_line
                quantity = move_lines.quantity if auto_create_multi else 1
                record.non_deductible_tax_val = record.currency_id.round(non_deductible_tax_value / quantity)

    @api.depends('original_move_line_ids', 'original_move_line_ids.account_id', 'asset_type', 'non_deductible_tax_val')
    def _compute_value(self):
        super()._compute_value()
        for record in self:
            if record.non_deductible_tax_val:
                record.original_value += record.non_deductible_tax_val

    def validate(self):
        super().validate()
        for record in self:
            if record.account_asset_id.create_asset == 'no':
                record._post_non_deductible_tax_value()

    def _post_non_deductible_tax_value(self):
        # If the asset has a non-deductible tax, the value is posted in the chatter to explain why
        # the original value does not match the related purchase(s).
        if self.non_deductible_tax_val:
            currency = self.env.company.currency_id
            msg = _('A non deductible tax value of %s was added to %s\'s initial value of %s',
                    formatLang(self.env, self.non_deductible_tax_val, currency_obj=currency),
                    self.name,
                    formatLang(self.env, self._get_related_purchase_value(self), currency_obj=currency))
            self.message_post(body=msg)

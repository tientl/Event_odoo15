# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_invoice_intrastat_country_id(self):
        # OVERRIDE
        self.ensure_one()
        if self.is_sale_document():
            return self.partner_shipping_id.country_id.id
        else:
            return super(AccountMove, self)._get_invoice_intrastat_country_id()

    @api.onchange('partner_shipping_id')
    def _onchange_partner_shipping_id(self):
        res = super(AccountMove, self)._onchange_partner_shipping_id()
        self.intrastat_country_id = self._get_invoice_intrastat_country_id()
        return res

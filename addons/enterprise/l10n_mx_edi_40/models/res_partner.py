# -*- coding: utf-8 -*-

from odoo import models, fields
from odoo.addons.l10n_mx_edi.models.res_company import FISCAL_REGIMES_SELECTION

class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_mx_edi_fiscal_regime = fields.Selection(
        selection=FISCAL_REGIMES_SELECTION,
        string="Fiscal Regime",
        help="Fiscal Regime is required for all partners (used in CFDI)")
    l10n_mx_edi_no_tax_breakdown = fields.Boolean(
        string="No Tax Breakdown",
        help="Includes taxes in the price and does not add tax information to the CFDI. Particularly in handy for IEPS. ")
    country_code = fields.Char(related='country_id.code', string='Country Code')

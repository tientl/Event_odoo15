# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_lu_is_representative = fields.Boolean(compute='_compute_l10n_lu_is_representative')
    l10n_lu_agent_matr_number = fields.Char(
        string="Matr Number",
        help="National ID number of the accounting firm (agent company) acting as the declarer in eCDF declarations")
    l10n_lu_agent_ecdf_prefix = fields.Char(
        string="ECDF Prefix",
        help="eCDF prefix (identifier) of the accounting firm (agent company) acting as the declarer in eCDF declarations")
    l10n_lu_agent_rcs_number = fields.Char(
        string="Company Registry",
        help="RCS (Régistre de Commerce et des Sociétés) of the accounting firm (agent company) acting as the declarer in eCDF declarations")

    @api.depends('account_represented_company_ids.account_fiscal_country_id.code')
    def _compute_l10n_lu_is_representative(self):
        for record in self:
            record.l10n_lu_is_representative = 'LU' in record.mapped(
                'account_represented_company_ids.account_fiscal_country_id.code')

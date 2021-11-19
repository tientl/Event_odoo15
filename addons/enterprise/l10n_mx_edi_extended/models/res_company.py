# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # == Address ==
    l10n_mx_edi_locality = fields.Char(
        compute='_compute_l10n_mx_edi_locality',
        inverse='_inverse_l10n_mx_edi_locality')
    l10n_mx_edi_locality_id = fields.Many2one(
        'l10n_mx_edi.res.locality', string='Locality',
        related='partner_id.l10n_mx_edi_locality_id', readonly=False,
        help='Municipality configured for this company')

    # == External Trade ==
    l10n_mx_edi_num_exporter = fields.Char(
        'Number of Reliable Exporter',
        help='Indicates the number of reliable exporter in accordance '
        'with Article 22 of Annex 1 of the Free Trade Agreement with the '
        'European Association and the Decision of the European Community. '
        'Used in External Trade in the attribute "NumeroExportadorConfiable".')

    def _compute_l10n_mx_edi_locality(self):
        for company in self:
            address_data = company.partner_id.sudo().address_get(adr_pref=['contact'])
            if address_data['contact']:
                partner = company.partner_id.sudo().browse(address_data['contact'])
                company.l10n_mx_edi_locality = partner.l10n_mx_edi_locality
            else:
                company.l10n_mx_edi_locality = None

    def _inverse_l10n_mx_edi_locality(self):
        for company in self:
            company.partner_id.l10n_mx_edi_locality = company.l10n_mx_edi_locality

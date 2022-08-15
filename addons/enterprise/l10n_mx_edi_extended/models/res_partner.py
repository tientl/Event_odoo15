# coding: utf-8

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # == Address ==
    l10n_mx_edi_locality = fields.Char(
        string="Locality Name",
        store=True, readonly=False,
        compute='_compute_l10n_mx_edi_locality')
    l10n_mx_edi_locality_id = fields.Many2one(
        comodel_name='l10n_mx_edi.res.locality',
        string="Locality",
        help="Optional attribute used in the XML that serves to define the locality where the domicile is located.")

    # == External Trade ==
    l10n_mx_edi_curp = fields.Char(
        string="CURP", size=18,
        help="In Mexico, the Single Code of Population Registration (CURP) is a unique alphanumeric code of 18 "
             "characters used to officially identify both residents and Mexican citizens throughout the country.")
    l10n_mx_edi_external_trade = fields.Boolean(
        'Need external trade?', help='check this box to add by default '
        'the external trade complement in invoices for this customer.')

    @api.depends('l10n_mx_edi_locality_id')
    def _compute_l10n_mx_edi_locality(self):
        for partner in self:
            partner.l10n_mx_edi_locality = partner.l10n_mx_edi_locality_id.name

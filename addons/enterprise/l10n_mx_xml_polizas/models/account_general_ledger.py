# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, models

_logger = logging.getLogger(__name__)

class AccountGeneralLedger(models.AbstractModel):
    _inherit = "account.general.ledger"

    def _get_reports_buttons(self, options):
        """ Add the Export (XML Polizas) Button to the General Ledger """
        buttons = super()._get_reports_buttons(options)
        if self.env.company.account_fiscal_country_id.code == 'MX':
            buttons.append({
                'name': _('XML (Polizas)'),
                'sequence': 3,
                'action': 'l10n_mx_open_xml_export_wizard',
                'file_export_type': _('XML')
            })
        return buttons

    def l10n_mx_open_xml_export_wizard(self, options):
        """ Action to open the XML Polizas Export Options from the General Ledger button """
        return {
            'type': 'ir.actions.act_window',
            'name': _('XML Polizas Export Options'),
            'res_model': 'l10n_mx_xml_polizas.xml_polizas_wizard',
            'views': [[False, 'form']],
            'target': 'new',
            'context': {
                **self.env.context,
                'l10n_mx_xml_polizas_generation_options': options,
                'default_export_type': 'AF'
            }
        }

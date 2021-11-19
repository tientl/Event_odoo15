# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import base64

from odoo import api, models, tools, _


class AccountGeneralLedger(models.AbstractModel):
    _inherit = 'account.general.ledger'

    def _get_reports_buttons(self, options):
        # OVERRIDE
        buttons = super()._get_reports_buttons(options)
        if self.env.company.account_fiscal_country_id.code == 'NO':
            buttons.append({'name': _('SAF-T'), 'sequence': 5, 'action': 'print_xml', 'file_export_type': _('XML')})
        return buttons

    @api.model
    def _prepare_saft_report_values(self, options):
        # OVERRIDE
        template_vals = super()._prepare_saft_report_values(options)

        if template_vals['company'].country_code != 'NO':
            return template_vals

        template_vals.update({
            'xmlns': 'urn:StandardAuditFile-Taxation-Financial:NO',
            'file_version': '1.10',
            'accounting_basis': 'A',
        })
        return template_vals

    @api.model
    def get_xml(self, options):
        # OVERRIDE
        content = super().get_xml(options)

        if self.env.company.account_fiscal_country_id.code != 'NO':
            return content

        xsd_attachment = self.env['ir.attachment'].search([('name', '=', 'xsd_cached_Norwegian_SAF-T_Financial_Schema_v_1_10_xsd')])
        if xsd_attachment:
            with io.BytesIO(base64.b64decode(xsd_attachment.with_context(bin_size=False).datas)) as xsd:
                tools.xml_utils._check_with_xsd(content, xsd)
        return content

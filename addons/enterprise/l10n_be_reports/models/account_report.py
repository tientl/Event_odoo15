# -*- coding: utf-8 -*-

import re
import markupsafe
import stdnum

from odoo import models, _
from odoo.exceptions import RedirectWarning


class AccountReport(models.AbstractModel):
    _inherit = 'account.report'

    def _get_belgian_xml_export_representative_node(self):
        """ The <Representative> node is common to XML exports made for VAT Listing, VAT Intra,
        and tax declaration. It is used in case the company isn't submitting its report directly,
        but through an external accountant.

        :return: The string containing the complete <Representative> node or an empty string,
                 in case no representative has been configured.
        """
        representative = self.env.company.account_representative_id
        if representative:
            vat_no, country_from_vat = self.env['account.generic.tax.report']._split_vat_number_and_country_code(representative.vat or "")
            country = self.env['res.country'].search([('code', '=', country_from_vat)], limit=1)
            phone = representative.phone or representative.mobile or ''
            node_values = {
                'vat': stdnum.get_cc_module('be', 'vat').compact(vat_no),   # Sanitize VAT number
                'name': representative.name,
                'street': "%s %s" % (representative.street or "", representative.street2 or ""),
                'zip': representative.zip,
                'city': representative.city,
                'country_code': (country or representative.country_id).code,
                'email': representative.email,
                'phone': self._raw_phonenumber(phone)
            }

            missing_fields = [k for k, v in node_values.items() if not v or v == ' ']
            if missing_fields:
                message = _('Some fields required for the export are missing. Please specify them.')
                action = {
                    'name': _("Company : %s", representative.name),
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'res.partner',
                    'views': [[False, 'form']],
                    'target': 'new',
                    'res_id': representative.id,
                    'context': {'create': False},
                }
                button_text = _('Specify')
                additional_context = {'required_fields': missing_fields}
                raise RedirectWarning(message, action, button_text, additional_context)

            return markupsafe.Markup("""<ns2:Representative>
        <RepresentativeID identificationType="NVAT" issuedBy="%(country_code)s">%(vat)s</RepresentativeID>
        <Name>%(name)s</Name>
        <Street>%(street)s</Street>
        <PostCode>%(zip)s</PostCode>
        <City>%(city)s</City>
        <CountryCode>%(country_code)s</CountryCode>
        <EmailAddress>%(email)s</EmailAddress>
        <Phone>%(phone)s</Phone>
    </ns2:Representative>""") % node_values

        return markupsafe.Markup()

    def _raw_phonenumber(self, phonenumber):
        return re.sub("[^+0-9]", "", phonenumber)[:20]

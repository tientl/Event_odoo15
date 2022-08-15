# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import re
from io import BytesIO
from datetime import datetime
from odoo import models, fields, tools, _
from odoo.exceptions import RedirectWarning


class L10nLuGenerateXML(models.TransientModel):
    """
    This wizard is used to generate xml reports for Luxembourg
    according to the xml 2.0 standard.
    """
    _name = 'l10n_lu.generate.xml'
    _description = 'Generate Xml 2.0'

    report_data = fields.Binary('Report file', readonly=True, attachment=False)
    filename = fields.Char(string='Filename', size=256, readonly=True)

    def _lu_validate_xml_content(self, content):
        attachment = self.env.ref('l10n_lu_reports.xsd_cached_eCDF_file_v2_0-XML_schema_xsd',
                                  raise_if_not_found=False)
        if attachment:
            xsd_datas = base64.b64decode(attachment.datas) if attachment else b''
            with BytesIO(xsd_datas) as xsd:
                tools.xml_utils._check_with_xsd(content, xsd)
        return True

    def get_xml(self):
        """
        Generates the XML report.
        """
        company = self.env.company
        agent = company.account_representative_id

        # Check for agent's required fields
        if agent:
            ecdf_not_ok = not agent.l10n_lu_agent_ecdf_prefix or not re.match('[0-9A-Z]{6}', agent.l10n_lu_agent_ecdf_prefix)
            matr_not_ok = not agent.l10n_lu_agent_matr_number or not re.match('[0-9]{11,13}', agent.l10n_lu_agent_matr_number)
            if ecdf_not_ok or matr_not_ok:
                raise RedirectWarning(
                    message=_("Some fields required for the export are missing or invalid. Please verify them."),
                    action={
                        'name': _("Company : %s", agent.name),
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'res_model': 'res.partner',
                        'views': [[False, 'form']],
                        'target': 'new',
                        'res_id': agent.id,
                        'context': {'create': False},
                    },
                    button_text=_('Verify'),
                    additional_context={'required_fields': [ecdf_not_ok and 'l10n_lu_agent_ecdf_prefix',
                                                            matr_not_ok and 'l10n_lu_agent_matr_number']}
                )

        options = self.env.context.get('tax_report_options')
        filename = self.env['account.report'].get_report_filename(options)
        vat = agent.vat if agent else self._get_export_vat()
        if vat and vat.startswith("LU"):  # Remove LU prefix in the XML
            vat = vat[2:]
        language = self.env.context.get('lang', '').split('_')[0].upper()
        language = language in ('EN', 'FR', 'DE') and language or 'EN'
        if self.env.context.get('report_generation_options'):
            self.env.context['report_generation_options']['language'] = language
        lu_template_values = {
            'filename': filename,
            'lang': language,
            'interface': 'MODL5',
            'agent_vat': vat or "NE",
            'agent_matr_number': agent.l10n_lu_agent_matr_number or company.matr_number or "NE",
            'agent_rcs_number': agent.l10n_lu_agent_rcs_number or company.company_registry or "NE",
            'declarations': []
        }
        vat = self._get_export_vat()
        if vat and vat.startswith("LU"):  # Remove LU prefix in the XML
            vat = vat[2:]
        # The Matr. Number is required
        if not company.matr_number:
            raise RedirectWarning(
                message=_(
                    "The company's Matr. Number hasn't been defined. Please configure it in the company's information."
                ),
                action={
                    'name': _("Company : %s", company.name),
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'res.company',
                    'views': [[False, 'form']],
                    'target': 'new',
                    'res_id': company.id,
                    'context': {'create': False},
                },
                button_text=_('Configure'),
                additional_context={'required_fields': ['matr_number']}
            )

        declaration_template_values = {
            'vat_number': vat or "NE",
            'matr_number': company.matr_number or "NE",
            'rcs_number': company.company_registry or "NE",
        }

        declarations_data = self._lu_get_declarations(declaration_template_values)
        self._save_xml_report(declarations_data, lu_template_values, filename)

        return {
            'name': 'XML Report',
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=" + self._name + "&id=" + str(self.id) + "&filename_field=filename&field=report_data&download=true&filename=" + self.filename,
            'target': 'self',
        }

    def _get_export_vat(self):
        # To be overridden for reports that need to allow foreign VAT fiscal positions
        return self.env.company.vat

    def _save_xml_report(self, declarations_data, lu_template_values, filename):
        lu_template_values['declarations'] = declarations_data['declarations']

        # Add function to format floats
        lu_template_values['format_float'] = lambda f: tools.float_utils.float_repr(f, 2).replace('.', ',')
        rendered_content = self.env.ref('l10n_lu_reports.l10n_lu_electronic_report_template_2_0')._render(lu_template_values)

        content = "\n".join(re.split(r'\n\s*\n', rendered_content))
        self._lu_validate_xml_content(content)
        self.env['account.report']._lu_validate_ecdf_prefix()

        self.write({
            'report_data': base64.b64encode(bytes(content, 'utf-8')),
            'filename': filename + '.xml',
        })

    def _lu_get_declarations(self, declaration_template_values):
        values = self.env[self.env.context['model']]._get_lu_xml_2_0_report_values(self.env.context['account_report_generation_options'])
        declarations = {'declaration_singles': {'forms': values['forms']}, 'declaration_groups': []}
        declarations.update(declaration_template_values)
        return {'declarations': [declarations]}

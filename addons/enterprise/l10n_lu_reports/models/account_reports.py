# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import base64
from io import BytesIO
from datetime import datetime
from odoo import models, tools, _
from odoo.exceptions import UserError


class AccountReport(models.AbstractModel):
    _inherit = 'account.report'

    def get_report_filename(self, options):
        if self._get_report_country_code(options) != 'LU':
            return super().get_report_filename(options)
        # we can't determine milliseconds using fields.Datetime, hence used python's `datetime`
        company = self.env.company
        agent = company.account_representative_id
        now_datetime = datetime.now()
        file_ref_data = {
            'ecdf_prefix': agent and agent.l10n_lu_agent_ecdf_prefix or company.ecdf_prefix,
            'datetime': now_datetime.strftime('%Y%m%dT%H%M%S%f')[:-4]
        }
        filename = '{ecdf_prefix}X{datetime}'.format(**file_ref_data)
        # `FileReference` element of exported XML must have same `filename` as above. So, we pass it from
        # here and get it from options in `_get_lu_electronic_report_values` and pass it further to template.
        if options:
            options['filename'] = filename
        return filename

    def _get_report_country_code(self, options):
        # Overridden in order to use the fiscal country of the current company
        if self.env.company.account_fiscal_country_id.code != 'LU':
            return super()._get_report_country_code(options)
        return self.env.company.account_fiscal_country_id.code or None

    def _get_lu_electronic_report_values(self, options):
        company = self.env.company
        vat = self.get_vat_for_export(options)
        if vat and vat.startswith("LU"): # Remove LU prefix in the XML
            vat = vat[2:]
        return {
            'filename': options.get('filename'),
            'lang': 'EN',
            'interface' : 'MODL5',
            'vat_number' : vat or "NE",
            'matr_number' : company.matr_number or "NE",
            'rcs_number' : company.company_registry or "NE",
        }

    def _lu_validate_ecdf_prefix(self):
        ecdf_prefix = self.env.company.ecdf_prefix
        if not ecdf_prefix:
            raise UserError(_('Please set valid eCDF Prefix for your company.'))
        re_valid_prefix = re.compile(r'[0-9|A-Z]{6}$')
        if not re_valid_prefix.match(ecdf_prefix):
            msg = _('eCDF Prefix `{0}` associated with `{1}` company is invalid.\nThe expected format is ABCD12 (Six digits of numbers or capital letters)')
            raise UserError(msg.format(ecdf_prefix, self.env.company.display_name))
        return True

    def _lu_validate_xml_content(self, content):
        attachment = self.env.ref('l10n_lu_reports.xsd_cached_eCDF_file_v1_1-XML_schema_xsd', raise_if_not_found=False)
        if attachment:
            xsd_datas = base64.b64decode(attachment.datas) if attachment else b''
            with BytesIO(xsd_datas) as xsd:
                tools.xml_utils._check_with_xsd(content, xsd)
        return True

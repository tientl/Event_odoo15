# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import zipfile
import math
import tempfile
from odoo import models, fields, api, _


class ECSalesReport(models.AbstractModel):
    _inherit = 'account.sales.report'

    def _get_non_generic_country_codes(self, options):
        codes = super(ECSalesReport, self)._get_non_generic_country_codes(options)
        codes.add('DE')
        return codes

    def _get_ec_sale_code_options_data(self, options):
        if self._get_report_country_code(options) != 'DE':
            return super(ECSalesReport, self)._get_ec_sale_code_options_data(options)

        return {
            'goods': {
                'name': 'L',
                'tax_report_line_ids': self.env.ref('l10n_de.tax_report_de_tag_41').ids,
            },
            'triangular': {
                'name': 'D',
                'tax_report_line_ids': self.env.ref('l10n_de.tax_report_de_tag_42').ids,
            },
            'services': {
                'name': 'S',
                'tax_report_line_ids': self.env.ref('l10n_de.tax_report_de_tag_68').ids,
            },
        }

    @api.model
    def _get_columns_name(self, options):
        if self._get_report_country_code(options) != 'DE':
            return super(ECSalesReport, self)._get_columns_name(options)

        return [
            {'name': ''},
            {'name': _('Länderkennzeichen')},
            {'name': _('Ust-IdNr.')},
            {'name': _('Art der Leistung')},
            {'name': _('Betrag'), 'class': 'number'},
        ]

    @api.model
    def _get_reports_buttons(self, options):
        if self._get_report_country_code(options) != 'DE':
            return super(ECSalesReport, self)._get_reports_buttons(options)

        return super(ECSalesReport, self)._get_reports_buttons(options) + [
            {'name': _('CSV'), 'sequence': 3, 'action': 'print_de_csvs_zip', 'file_export_type': _('ZIP')}
        ]

    def print_de_csvs_zip(self, options):
        return {
            'type': 'ir_actions_account_report_download',
            'data': {
                'model': self.env.context.get('model'),
                'options': json.dumps(options),
                'output_format': 'zip',
                'financial_id': self.env.context.get('id'),
            }
        }

    @api.model
    def _get_csvs(self, options):
        options['get_file_data'] = True
        lines = self.with_context(no_format=True)._get_lines(options)
        # each csv file may only contain up to 1000 lines
        line_chunks = []
        chunks = [lines[i * 1000:(i + 1) * 1000] for i in range(math.ceil(len(lines) / 1000))]
        for chunk in chunks:
            content = 'Länderkennzeichen,USt-IdNr.,Betrag (Euro),Art der Leistung\n'
            for l in chunk:
                content += ','.join([l[0], l[1], str(l[3]), l[2]]) + '\n'
            line_chunks.append(content)
        return line_chunks

    def _get_zip(self, options):
        csvs = self._get_csvs(options)
        with tempfile.NamedTemporaryFile() as buf:
            with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED, allowZip64=False) as zip_buffer:
                for i, csv in enumerate(csvs):
                    zip_buffer.writestr('EC_Sales_list%s.csv' % (len(csvs) > 1 and ("_" + str(i+1)) or ""), csv)
            buf.seek(0)
            res = buf.read()
        return res

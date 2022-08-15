# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _
from odoo.exceptions import UserError
from odoo.tools.misc import formatLang
from odoo.tools import pycompat

from time import strptime

import json
import io
import contextlib


class ECSalesReport(models.AbstractModel):
    _inherit = 'account.sales.report'

    def _get_non_generic_country_codes(self, options):
        codes = super(ECSalesReport, self)._get_non_generic_country_codes(options)
        codes.add('SE')
        return codes

    def _get_ec_sale_code_options_data(self, options):
        if self._get_report_country_code(options) != 'SE':
            return super(ECSalesReport, self)._get_ec_sale_code_options_data(options)

        return {
            'goods': {
                'name': 'L',
                'tax_report_line_ids': self.env.ref('l10n_se.tax_report_line_35').ids,
            },
            'triangular': {
                'name': 'D',
                'tax_report_line_ids': self.env.ref('l10n_se.tax_report_line_38').ids,
            },
            'services': {
                'name': 'S',
                'tax_report_line_ids': self.env.ref('l10n_se.tax_report_line_39').ids,
            },
        }

    @api.model
    def _get_columns_name(self, options):
        if self._get_report_country_code(options) != 'SE':
            return super(ECSalesReport, self)._get_columns_name(options)

        return [
            {'name': ''},
            {'name': _('VAT Number')},
            {'name': _('Value of Product'), 'class': 'number'},
            {'name': _('Value of Third Party'), 'class': 'number'},
            {'name': _('Value of Service'), 'class': 'number'},
        ]

    @api.model
    def _get_reports_buttons(self, options):
        if self._get_report_country_code(options) != 'SE':
            return super(ECSalesReport, self)._get_reports_buttons(options)

        return super(ECSalesReport, self)._get_reports_buttons(options) + [
            {'name': _('KVR'), 'sequence': 3, 'action': 'print_se_kvr', 'file_export_type': _('KVR')}
        ]

    @api.model
    def _process_query_result(self, options, query_result):
        if self._get_report_country_code(options) != 'SE':
            return super(ECSalesReport, self)._process_query_result(options, query_result)

        ec_country_to_check = self.get_ec_country_codes(options)

        data = {}
        for row in query_result:
            if not row['vat']:
                row['vat'] = ''

            amount = row['amount'] or 0.0
            if amount:
                if not row['vat']:
                    if options.get('get_file_data', False):
                        raise UserError(_('One or more partners has no VAT Number.'))
                    else:
                        options['missing_vat_warning'] = True

                if row['same_country'] or row['partner_country_code'] not in ec_country_to_check:
                    options['unexpected_intrastat_tax_warning'] = True

                row['vat'] = row['vat'].replace(' ', '').upper()
                if not row['vat'] in data:
                    data[row['vat']] = {
                        'goods_amount': '',
                        'triangular_amount': '',
                        'services_amount': '',
                    }
                    if 'partner_id' in row:
                        data[row['vat']]['partner_id'] = row['partner_id']
                        data[row['vat']]['partner_name'] = row['partner_name']

                for option_code in options['ec_sale_code']:
                    if option_code['id'] == row['tax_code']:
                        data[row['vat']]['%s_amount' % row['tax_code']] = amount

        lines = []
        for vat, row in data.items():
            columns = [
                vat,
                row['goods_amount'],
                row['triangular_amount'],
                row['services_amount'],
            ]
            if not self.env.context.get('no_format', False) and not options.get('get_file_data', False):
                currency_id = self.env.company.currency_id
                columns[1] = formatLang(self.env, columns[1], currency_obj=currency_id)
                columns[2] = formatLang(self.env, columns[2], currency_obj=currency_id)
                columns[3] = formatLang(self.env, columns[3], currency_obj=currency_id)

            if options.get('get_file_data', False):
                columns.append('')
                lines.append(columns)
            else:
                lines.append({
                    'id': row['partner_id'],
                    'caret_options': 'res.partner',
                    'model': 'res.partner',
                    'name': row['partner_name'],
                    'columns': [{'name': v} for v in columns],
                    'unfoldable': False,
                    'unfolded': False,
                })
        return lines

    def print_se_kvr(self, options):
        return {
            'type': 'ir_actions_account_report_download',
            'data': {
                'model': self.env.context.get('model'),
                'options': json.dumps(options),
                'output_format': 'kvr',
                'financial_id': self.env.context.get('id'),
            }
        }

    def get_report_filename(self, options):
        if self._get_report_country_code(options) != 'SE':
            return super(ECSalesReport, self).get_report_filename(options)
        return '%s_%s' % (self.env.company.vat, self._get_se_period(options))

    def _get_se_period(self, options):
        if options['date']['period_type'] == 'month':
            return '%s%02d' % (options['date']['string'][-2:], strptime(options['date']['string'][:3], '%b').tm_mon)
        elif options['date']['period_type'] == 'quarter':
            return '%s-%s' % (options['date']['string'][-2:], options['date']['string'][1:2])
        else:
            raise UserError(_('You can only export Monthly or Quarterly reports.'))

    def _get_kvr(self, options):
        options['get_file_data'] = True

        lines = [
            ['SKV574008'],
            [self.env.company.vat, self._get_se_period(options), self.env.user.name, self.env.user.phone or '', self.env.user.email or '', ''],
        ]
        lines += self.with_context(no_format=True)._get_lines(options)

        with contextlib.closing(io.BytesIO()) as buf:
            writer = pycompat.csv_writer(buf, delimiter=';')
            writer.writerows(lines)
            content = buf.getvalue()

        return content

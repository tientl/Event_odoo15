# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

EDI_FIELDS = ['l10n_mx_edi_cfdi_uuid', 'l10n_mx_edi_cfdi_customer_rfc']

class XmlPolizasExportWizard(models.TransientModel):
    _inherit = 'l10n_mx_xml_polizas.xml_polizas_wizard'

    def _get_move_export_data(self, accounts_results):
        # Retrieve extra data for CompNal node

        mx_move_vals = {}
        AccountMove = self.env['account.move']
        for results in accounts_results:
            lines_data = results[1][0].get('lines', [])
            for line_data in lines_data:
                # move line data is already grouped by account, we store the retrieved move info
                # to reduce db queries
                mx_data = mx_move_vals.get(line_data['move_id'])
                if not mx_data:
                    mx_data = AccountMove.browse(line_data['move_id']).read(EDI_FIELDS)[0]
                    mx_move_vals[mx_data.pop('id')] = mx_data
                if mx_data.get('l10n_mx_edi_cfdi_uuid'):
                    currency_name = line_data.pop('currency_name', False)
                    currency_conversion_rate = mx_data.get('currency_conversion_rate')
                    amount_total = line_data['amount_currency']
                    if line_data['currency_id'] != line_data['company_currency_id'] and not currency_conversion_rate:
                        # calculate conversion rate just once per move so we don't see
                        # rounding differences between lines
                        amount_total_signed = line_data['balance']
                        if amount_total:
                            currency_conversion_rate = abs(amount_total_signed) / abs(amount_total)
                        else:
                            currency_conversion_rate = 1
                        currency_conversion_rate = '%.*f' % (5, currency_conversion_rate)
                        mx_data['currency_name'] = currency_name
                        mx_data['currency_conversion_rate'] = currency_conversion_rate
                    line_data.update({
                        'amount_total': amount_total,
                        **mx_data
                    })
        return super()._get_move_export_data(accounts_results)

    def _get_move_line_export_data(self, line):
        data = super()._get_move_line_export_data(line)
        uuid = line.get('l10n_mx_edi_cfdi_uuid')
        if uuid:
            data.update({
                'uuid': uuid,
                'currency_name': line.get('currency_name'),
                'currency_conversion_rate': line.get('currency_conversion_rate'),
                'customer_vat': line['l10n_mx_edi_cfdi_customer_rfc'],
                'amount_total': line['amount_total'],
            })
        return data

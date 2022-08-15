# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _


class ECSalesReport(models.AbstractModel):
    _inherit = 'account.sales.report'

    @api.model
    def _get_columns_name(self, options):
        if self._get_report_country_code(options) in self._get_non_generic_country_codes(options):
            return super(ECSalesReport, self)._get_columns_name(options)

        return [
            {'name': ''},
            {'name': _('Country Code')},
            {'name': _('VAT')},
            {'name': _('Amount'), 'class': 'number'},
        ]

    @api.model
    def _process_query_result(self, options, query_result):
        if self._get_report_country_code(options) in self._get_non_generic_country_codes(options):
            return super(ECSalesReport, self)._process_query_result(options, query_result)

        total_value = query_result and query_result[0]['total_value'] or 0
        lines = []
        context = self.env.context
        for res in query_result:
            if not context.get('no_format', False):
                res['value'] = self.format_value(res['value'])
            lines.append({
                'id': res['partner_id'],
                'caret_options': 'res.partner',
                'model': 'res.partner',
                'name': res['partner_name'],
                'columns': [{'name': c} for c in [
                    res['country_code'], res['partner_vat'], res['value']]
                ],
                'level': 2,
            })

        # Create total line
        lines.append({
            'id': 0,
            'name': _('Total'),
            'class': 'total',
            'level': 2,
            'columns': [{'name': self.format_value(total_value), 'no_format': total_value}],
            'colspan': 3,
        })
        return lines

    @api.model
    def _prepare_query(self, options):
        if self._get_report_country_code(options) in self._get_non_generic_country_codes(options):
            return super(ECSalesReport, self)._prepare_query(options)

        tables, where_clause, where_params = self._query_get(options, [(
            'move_id.move_type', 'in', ('out_invoice', 'out_refund'))
        ])
        where_params.append(tuple(self.env['account.sales.report'].get_ec_country_codes(options)))
        query = '''
                SELECT partner.id AS partner_id,
                       partner.vat AS partner_vat,
                       partner.name AS partner_name,
                       country.code AS country_code,
                       sum(account_move_line.balance) AS value,
                       sum(sum(account_move_line.balance)) OVER () AS total_value
                  FROM ''' + tables + '''
             LEFT JOIN res_partner partner ON account_move_line.partner_id = partner.id
             LEFT JOIN res_country country ON partner.country_id = country.id
             LEFT JOIN account_account account on account_move_line.account_id = account.id
             LEFT JOIN res_company company ON account_move_line.company_id = company.id
            INNER JOIN res_partner company_partner ON company_partner.id = company.partner_id
                 WHERE ''' + where_clause + '''
                   AND country.code IN %s
                   AND account.internal_type = 'receivable'
                   AND company_partner.country_id != country.id
                   AND partner.vat IS NOT NULL
              GROUP BY partner.id, partner.vat, partner.name, country.code
        '''
        return query, where_params

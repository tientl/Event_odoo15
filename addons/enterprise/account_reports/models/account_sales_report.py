# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.misc import formatLang


class ECSalesReport(models.AbstractModel):
    """ This report is meant to be overridden.
    It is overridden by the current company country specific report (should be in l10n_XX_reports),
    or if no report exist for the current company country, by "account_sales_report_generic.py".
    The menuitem linking to this report is initialy set to active = False.
    The menuitem active field is set to True when installing account_intrastat or an country specific report.
    This means that, when creating a new country speficifc report, the following record must be added
    to the report module (l10n_XX_reports) data :
    <record model="ir.ui.menu" id="account_reports.menu_action_account_report_sales">
        <field name="active" eval="True"/>
    </record>
    """

    _name = 'account.sales.report'
    _description = 'EC Sales List'
    _inherit = 'account.report'
    filter_date = {'mode': 'range', 'filter': 'this_month'}
    filter_journals = True
    filter_multi_company = None
    filter_ec_sale_code = None

    @api.model
    def _get_templates(self):
        templates = super(ECSalesReport, self)._get_templates()
        templates['main_template'] = 'account_reports.account_reports_sales_report_main_template'
        return templates

    def _get_non_generic_country_codes(self, options):
        # to be overriden by country specific method
        return set()

    def _get_report_country_code(self, options):
        # Overridden in order to use the fiscal country of the current company
        return self.env.company.account_fiscal_country_id.code or None

    def _get_options(self, previous_options=None):
        options = super(ECSalesReport, self)._get_options(previous_options)
        if self._get_report_country_code(options):
            options.pop('journals', None)
            options['country_specific_report_label'] = self.env.company.country_id.display_name
        else:
            options.pop('ec_sale_code', None)
            options['country_specific_report_label'] = None

        options['date']['strict_range'] = True
        return options

    @api.model
    def _get_filter_journals(self):
        # only show sale journals
        return self.env['account.journal'].search([('company_id', '=', self.env.company.id), ('type', '=', 'sale')], order="company_id, name")

    @api.model
    def _get_columns_name(self, options):
        # this method must be overriden by country specific method
        return []

    def _get_ec_sale_code_options_data(self, options):
        # this method must be overriden by country specific method
        # it defines wich tax report line ids are linked to goods, triangular & services
        # and it defines country specific names
        return {
            'goods': {'name': _('Goods'), 'tax_report_line_ids': ()},
            'triangular': {'name': _('Triangular'), 'tax_report_line_ids': ()},
            'services': {'name': _('Services'), 'tax_report_line_ids': ()},
        }

    def _init_filter_ec_sale_code(self, options, previous_options=None):
        # If the country changes, previous_options['ec_sale_code'] might exist but with wrong names/data.
        # We must recreate the dict, and apply "selected" state if previous ones existing.
        ec_sale_code_options_data = self._get_ec_sale_code_options_data(options)
        options['ec_sale_code'] = []
        for id in ('goods', 'triangular', 'services'):
            ec_sale_code_options_data[id].update({'id': id, 'selected': False})
            options['ec_sale_code'].append(ec_sale_code_options_data[id])

        if previous_options and previous_options.get('ec_sale_code'):
            for i in range(0, 3):
                options['ec_sale_code'][i]['selected'] = previous_options['ec_sale_code'][i]['selected']

    @api.model
    def _prepare_query(self, options):
        tables, where_clause, where_params = self._query_get(options)
        query = ' '.join([
            'WITH', self._get_query_with(options),
            'SELECT', self._get_query_select(options),
            'FROM', tables, self._get_query_from(options),
            'WHERE', where_clause,
            'GROUP BY', self._get_query_group_by(options),
            'ORDER BY', self._get_query_order_by(options),
        ])
        return query, where_params

    @api.model
    def _get_query_with(self, options):
        params = []
        for tax_code, tax_report_line_ids in options['selected_tag_ids'].items():
            for tax_report_line_id in tax_report_line_ids:
                params += [tax_code, tax_report_line_id]
        values = ', '.join(['(%s, %s)'] * int(len(params) / 2))
        return self.env.cr.mogrify(
            'tax_report_lines_additional_info (code, id) AS (VALUES %s)' % values,
            params,
        ).decode(self.env.cr.connection.encoding)

    @api.model
    def _get_query_select(self, options):
        res = '''p.vat AS vat,
                 tax_report_lines_additional_info.code as tax_code,
                 SUM(-account_move_line.balance) AS amount,
                 (p.country_id = company_partner.country_id) AS same_country,
                 country.code AS partner_country_code'''
        if not options or not options.get('get_file_data', False):
            res += ''',
                 account_move_line.partner_id AS partner_id,
                 p.name As partner_name'''
        return res

    @api.model
    def _get_query_from(self, options):
        return '''
                  JOIN res_partner p ON account_move_line.partner_id = p.id
                  JOIN account_account_tag_account_move_line_rel aml_tag ON account_move_line.id = aml_tag.account_move_line_id
                  JOIN account_account_tag tag ON tag.id = aml_tag.account_account_tag_id
                  JOIN account_tax_report_line_tags_rel ON account_tax_report_line_tags_rel.account_account_tag_id = tag.id
                  JOIN tax_report_lines_additional_info ON tax_report_lines_additional_info.id = account_tax_report_line_tags_rel.account_tax_report_line_id
                  JOIN res_company company ON account_move_line.company_id = company.id
                  JOIN res_partner company_partner ON company_partner.id = company.partner_id
                  JOIN res_country country ON p.country_id = country.id'''

    @api.model
    def _get_query_group_by(self, options):
        res = 'p.vat, tax_report_lines_additional_info.code, p.country_id, company_partner.country_id, country.code'
        if not options.get('get_file_data'):
            res = 'p.name, account_move_line.partner_id, ' + res
        return res

    @api.model
    def _get_query_order_by(self, options):
        params = [tax_code for tax_code in options['selected_tag_ids']][::-1]
        order_items = ['tax_report_lines_additional_info.code= %s'] * len(params)
        order_items.append('vat' if options.get('get_file_data') else 'partner_name')
        return self.env.cr.mogrify(", ".join(order_items), params).decode(self.env.cr.connection.encoding)

    @api.model
    def _get_lines(self, options, line_id=None):
        options['selected_tag_ids'] = self._get_selected_tags(options)
        query, params = self._prepare_query(options)
        self._cr.execute(query, params)
        query_res = self._cr.dictfetchall()

        return self._process_query_result(options, query_res)

    @api.model
    def _get_selected_tags(self, options):
        selected_tags = {}
        if options.get('ec_sale_code', False):
            # if no codes are selected to filter on, show all codes
            show_all = not [x['id'] for x in options['ec_sale_code'] if x['selected']]
            for option_code in options['ec_sale_code']:
                if option_code['selected'] or show_all:
                    selected_tags[option_code['id']] = tuple(option_code['tax_report_line_ids'])
        return selected_tags

    @api.model
    def _process_query_result(self, options, query_result):
        ec_country_to_check = self.get_ec_country_codes(options)
        lines = []
        for row in query_result:
            if not row['vat']:
                row['vat'] = ''

            amt = row['amount'] or 0.0
            if amt:
                if not row['vat']:
                    if options.get('get_file_data', False):
                        raise UserError(_('One or more partners has no VAT Number.'))
                    else:
                        options['missing_vat_warning'] = True

                if row['same_country'] or row['partner_country_code'] not in ec_country_to_check:
                    options['unexpected_intrastat_tax_warning'] = True

                ec_sale_code = self._get_ec_sale_code_options_data(options)[row['tax_code']]['name']

                vat = row['vat'].replace(' ', '').upper()
                columns = [
                    vat[:2],
                    vat[2:],
                    ec_sale_code,
                    amt
                ]
                if not self.env.context.get('no_format', False) and not options.get('get_file_data', False):
                    currency_id = self.env.company.currency_id
                    columns[3] = formatLang(self.env, columns[3], currency_obj=currency_id)

                if options.get('get_file_data', False):
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

    @api.model
    def get_ec_country_codes(self, options):
        rslt = {'AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR', 'HU',
                'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE'}

        # GB left the EU on January 1st 2021. But before this date, it's still to be considered as a EC country
        if fields.Date.from_string(options['date']['date_from']) < fields.Date.from_string('2021-01-01'):
            rslt.add('GB')

        return rslt

    @api.model
    def _get_report_name(self):
        return _('EC Sales List')

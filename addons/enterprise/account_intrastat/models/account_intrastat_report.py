# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _, _lt
from .supplementary_unit_codes import SUPPLEMENTARY_UNITS_TO_COMMODITY_CODES as SUPP_TO_COMMODITY

_merchandise_export_code = {
    'BE': '29',
    'FR': '21',
    'NL': '7',
}

_merchandise_import_code = {
    'BE': '19',
    'FR': '11',
    'NL': '6',
}

_unknown_country_code = {
    'BE': 'QU',
    'NL': 'QV',
}

_qn_unknown_individual_vat_country_codes = ('FI', 'SE', 'SK', 'DE', 'AT')

class IntrastatReport(models.AbstractModel):
    _name = 'account.intrastat.report'
    _description = 'Intrastat Report'
    _inherit = 'account.report'

    filter_date = {'mode': 'range', 'filter': 'this_month'}
    filter_journals = True
    filter_multi_company = None
    filter_with_vat = False
    filter_intrastat_type = [
        {'name': _lt('Arrival'), 'selected': False, 'id': 'arrival'},
        {'name': _lt('Dispatch'), 'selected': False, 'id': 'dispatch'},
    ]
    filter_intrastat_extended = True

    def print_xlsx(self, options):
        return super().print_xlsx({**options, 'country_format': 'code'})

    def _get_filter_journals(self):
        #only show sale/purchase journals
        return self.env['account.journal'].search([('company_id', 'in', self.env.companies.ids or [self.env.company.id]), ('type', 'in', ('sale', 'purchase'))], order="company_id, name")

    def _show_region_code(self):
        """Return a bool indicating if the region code is to be displayed for the country concerned in this localisation."""
        # TO OVERRIDE
        return True

    def _get_columns_name(self, options):
        columns = [
            {'name': ''},
            {'name': _('System')},
            {'name': _('Country Code')},
            {'name': _('Transaction Code')},
        ]
        if self._show_region_code():
            columns += [
                {'name': _('Region Code')},
            ]
        columns += [
            {'name': _('Commodity Code')},
            {'name': _('Type')},
            {'name': _('Origin Country')},
            {'name': _('Partner VAT')},
        ]
        if options.get('intrastat_extended'):
            columns += [
                {'name': _('Transport Code')},
                {'name': _('Incoterm Code')},
            ]
        columns += [
            {'name': _('Weight')},
            {'name': _('Supplementary Units')},
            {'name': _('Value'), 'class': 'number'},
        ]
        return columns

    @api.model
    def _create_intrastat_report_line(self, options, vals):
        # This is so that full country names are displayed when in the UI, and the 2-digit iso codes are used when 'code' is in the options
        country_column = 'country_code' if options.get('country_format') == 'code' else 'country_name'
        origin_country_column = 'intrastat_product_origin_country' if options.get('country_format') == 'code' else 'intrastat_product_origin_country_name'

        columns = [{'name': c} for c in [
            vals['system'], vals[country_column], vals['transaction_code'],
        ]]
        if self._show_region_code():
            columns.append({'name': vals['region_code']})
        columns += [{'name': c} for c in [
            vals['commodity_code'], vals['type'], vals[origin_country_column], vals['partner_vat'],
        ]]
        if options.get('intrastat_extended'):
            columns += [{'name': c} for c in [
                vals['invoice_transport'] or vals['company_transport'] or '',
                vals['invoice_incoterm'] or vals['company_incoterm'] or '',
            ]]

        columns += [{'name': c} for c in [
            vals['weight'], vals['supplementary_units'], self.format_value(vals['value'])
        ]]

        return {
            'id': vals['id'],
            'caret_options': 'account.move',
            'model': 'account.move.line',
            'name': vals['invoice_number'],
            'columns': columns,
            'level': 2,
        }

    @api.model
    def _decode_options(self, options):
        journal_ids = self.env['account.journal'].search([('type', 'in', ('sale', 'purchase'))]).ids
        if options.get('journals'):
            journal_ids = [c['id'] for c in options['journals'] if c.get('selected')] or journal_ids

        if options.get('intrastat_type'):
            incl_arrivals = options['intrastat_type'][0]['selected']
            incl_dispatches = options['intrastat_type'][1]['selected']
            if not incl_arrivals and not incl_dispatches:
                incl_arrivals = incl_dispatches = True
        else:
            incl_arrivals = incl_dispatches = True

        return options['date']['date_from'], options['date']['date_to'], journal_ids, \
            incl_arrivals, incl_dispatches, options.get('intrastat_extended'), options.get('with_vat')

    @api.model
    def _prepare_query(self, date_from, date_to, journal_ids, invoice_types=None, with_vat=False):
        query_blocks, params = self._build_query(date_from, date_to, journal_ids, invoice_types=invoice_types, with_vat=with_vat)
        query = 'SELECT %(select)s FROM %(from)s WHERE %(where)s ORDER BY %(order)s' % query_blocks
        return query, params

    @api.model
    def _build_query(self, date_from, date_to, journal_ids, invoice_types=None, with_vat=False):
        # triangular use cases are handled by letting the intrastat_country_id editable on
        # invoices. Modifying or emptying it allow to alter the intrastat declaration
        # accordingly to specs (https://www.nbb.be/doc/dq/f_pdf_ex/intra2017fr.pdf (§ 4.x))
        select = '''
                row_number() over () AS sequence,
                CASE WHEN inv.move_type IN ('in_invoice', 'out_refund') THEN %(import_merchandise_code)s ELSE %(export_merchandise_code)s END AS system,
                country.code AS country_code,
                country.name AS country_name,
                company_country.code AS comp_country_code,
                transaction.code AS transaction_code,
                company_region.code AS region_code,
                code.code AS commodity_code,
                inv_line.id AS id,
                prodt.id AS template_id,
                prodt.categ_id AS category_id,
                inv_line.product_uom_id AS uom_id,
                inv_line_uom.category_id AS uom_category_id,
                inv.id AS invoice_id,
                inv.currency_id AS invoice_currency_id,
                inv.name AS invoice_number,
                coalesce(inv.date, inv.invoice_date) AS invoice_date,
                inv.move_type AS invoice_type,
                inv_incoterm.code AS invoice_incoterm,
                comp_incoterm.code AS company_incoterm,
                inv_transport.code AS invoice_transport,
                comp_transport.code AS company_transport,
                CASE WHEN inv.move_type IN ('in_invoice', 'out_refund') THEN 'Arrival' ELSE 'Dispatch' END AS type,
                ROUND(
                    prod.weight * inv_line.quantity / (
                        CASE WHEN inv_line_uom.category_id IS NULL OR inv_line_uom.category_id = prod_uom.category_id
                        THEN inv_line_uom.factor ELSE 1 END
                    ) * (
                        CASE WHEN prod_uom.uom_type <> 'reference'
                        THEN prod_uom.factor ELSE 1 END
                    ),
                    SCALE(ref_weight_uom.rounding)
                ) AS weight,
                inv_line.quantity / (
                    CASE WHEN inv_line_uom.category_id IS NULL OR inv_line_uom.category_id = prod_uom.category_id
                    THEN inv_line_uom.factor ELSE 1 END
                ) AS quantity,
                inv_line.quantity AS line_quantity,
                CASE WHEN inv_line.price_subtotal = 0 THEN inv_line.price_unit * inv_line.quantity ELSE inv_line.price_subtotal END AS value,
                COALESCE(product_country.code, %(unknown_country_code)s) AS intrastat_product_origin_country,
                product_country.name AS intrastat_product_origin_country_name,
                CASE WHEN partner.vat IS NOT NULL THEN partner.vat
                     WHEN partner.vat IS NULL AND partner.is_company IS FALSE THEN %(unknown_individual_vat)s
                     ELSE 'QV999999999999'
                END AS partner_vat
                '''
        from_ = '''
                account_move_line inv_line
                LEFT JOIN account_move inv ON inv_line.move_id = inv.id
                LEFT JOIN account_intrastat_code transaction ON inv_line.intrastat_transaction_id = transaction.id
                LEFT JOIN res_company company ON inv.company_id = company.id
                LEFT JOIN account_intrastat_code company_region ON company.intrastat_region_id = company_region.id
                LEFT JOIN res_partner partner ON inv_line.partner_id = partner.id
                LEFT JOIN res_partner comp_partner ON company.partner_id = comp_partner.id
                LEFT JOIN res_country country ON inv.intrastat_country_id = country.id
                LEFT JOIN res_country company_country ON comp_partner.country_id = company_country.id
                INNER JOIN product_product prod ON inv_line.product_id = prod.id
                LEFT JOIN product_template prodt ON prod.product_tmpl_id = prodt.id
                LEFT JOIN account_intrastat_code code ON code.id = COALESCE(prod.intrastat_variant_id, prodt.intrastat_id)
                LEFT JOIN uom_uom inv_line_uom ON inv_line.product_uom_id = inv_line_uom.id
                LEFT JOIN uom_uom prod_uom ON prodt.uom_id = prod_uom.id
                LEFT JOIN account_incoterms inv_incoterm ON inv.invoice_incoterm_id = inv_incoterm.id
                LEFT JOIN account_incoterms comp_incoterm ON company.incoterm_id = comp_incoterm.id
                LEFT JOIN account_intrastat_code inv_transport ON inv.intrastat_transport_mode_id = inv_transport.id
                LEFT JOIN account_intrastat_code comp_transport ON company.intrastat_transport_mode_id = comp_transport.id
                LEFT JOIN res_country product_country ON product_country.id = inv_line.intrastat_product_origin_country_id
                LEFT JOIN res_country partner_country ON partner.country_id = partner_country.id AND partner_country.intrastat IS TRUE
                LEFT JOIN uom_uom ref_weight_uom on ref_weight_uom.category_id = %(weight_category_id)s and ref_weight_uom.uom_type = 'reference'
                '''
        where = '''
                inv.state = 'posted'
                AND inv_line.display_type IS NULL
                AND (NOT inv_line.price_subtotal = 0 OR inv_line.price_unit * inv_line.quantity != 0)
                AND inv.company_id = %(company_id)s
                AND company_country.id != country.id
                AND country.intrastat = TRUE AND (country.code != 'GB' OR inv.date < '2021-01-01')
                AND coalesce(inv.date, inv.invoice_date) >= %(date_from)s
                AND coalesce(inv.date, inv.invoice_date) <= %(date_to)s
                AND prodt.type != 'service'
                AND inv.journal_id IN %(journal_ids)s
                AND inv.move_type IN %(invoice_types)s
                AND NOT inv_line.exclude_from_invoice_tab
                '''
        order = 'inv.invoice_date DESC, inv_line.id'
        params = {
            'company_id': self.env.company.id,
            'import_merchandise_code': _merchandise_import_code.get(self.env.company.country_id.code, '29'),
            'export_merchandise_code': _merchandise_export_code.get(self.env.company.country_id.code, '19'),
            'date_from': date_from,
            'date_to': date_to,
            'journal_ids': tuple(journal_ids),
            'weight_category_id': self.env['ir.model.data']._xmlid_to_res_id('uom.product_uom_categ_kgm'),
            'unknown_individual_vat': 'QN999999999999' if self.env.company.country_id.code in _qn_unknown_individual_vat_country_codes else 'QV999999999999',
            'unknown_country_code': _unknown_country_code.get(self.env.company.country_id.code, 'QV'),
        }
        if with_vat:
            where += ' AND partner.vat IS NOT NULL '
        if invoice_types:
            params['invoice_types'] = tuple(invoice_types)
        else:
            params['invoice_types'] = ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')
        query = {
            'select': select,
            'from': from_,
            'where': where,
            'order': order,
        }
        return query, params

    @api.model
    def _fill_missing_values(self, vals_list):
        ''' Some values are too complex to be retrieved in the SQL query.
        Then, this method is used to compute the missing values fetched from the database.

        :param vals:    A dictionary created by the dictfetchall method.
        '''

        # Prefetch data before looping
        category_ids = self.env['product.category'].browse({vals['category_id'] for vals in vals_list})
        self.env['product.category'].search([('id', 'parent_of', category_ids.ids)]).read(['intrastat_id', 'parent_id'])

        for vals in vals_list:
            # Check account.intrastat.code
            # If missing, retrieve the commodity code by looking in the product category recursively.
            if not vals['commodity_code']:
                category_id = self.env['product.category'].browse(vals['category_id'])
                vals['commodity_code'] = category_id.search_intrastat_code().code

            # set transaction_code default value if none (this is overridden in account_intrastat_expiry)
            if not vals['transaction_code']:
                vals['transaction_code'] = 1

            # Check the currency.
            currency_id = self.env['res.currency'].browse(vals['invoice_currency_id'])
            company_currency_id = self.env.company.currency_id
            if currency_id != company_currency_id:
                vals['value'] = currency_id._convert(vals['value'], company_currency_id, self.env.company, vals['invoice_date'])
        return vals_list

    @api.model
    def _get_lines(self, options, line_id=None):
        self.env['account.move.line'].check_access_rights('read')

        date_from, date_to, journal_ids, incl_arrivals, incl_dispatches, extended, with_vat = self._decode_options(options)

        if not journal_ids:
            return []

        invoice_types = []
        if incl_arrivals:
            invoice_types += ['in_invoice', 'out_refund']
        if incl_dispatches:
            invoice_types += ['out_invoice', 'in_refund']

        query, params = self._prepare_query(date_from, date_to, journal_ids, invoice_types=invoice_types, with_vat=with_vat)

        self._cr.execute(query, params)
        query_res = self._cr.dictfetchall()
        query_res = self._fill_supplementary_units(query_res)

        # Create lines
        lines = []
        total_value = 0
        for vals in self._fill_missing_values(query_res):
            line = self._create_intrastat_report_line(options, vals)
            lines.append(line)
            total_value += vals['value']

        # Create total line if only one type selected.
        if incl_arrivals != incl_dispatches:
            colspan = 12 if extended else 10
            lines.append({
                'id': 0,
                'name': _('Total'),
                'class': 'total',
                'level': 2,
                'columns': [{'name': v} for v in [self.format_value(total_value)]],
                'colspan': colspan,
            })
        return lines

    @api.model
    def _get_report_name(self):
        return _('Intrastat Report')

    def _get_report_country_code(self, options):
        return self.env.company.account_fiscal_country_id.code or None

    def _fill_supplementary_units(self, query_results):
        """ Although the default measurement provided is the weight in kg, some commodities require a supplementary unit
        in the report.

            e.g. Livestock are measured p/st, which is to say per animal.
                 Bags of plastic artificial teeth (code 90212110) are measured 100 p/st, which is
                 per hundred teeth.
                 Code 29372200 Halogenated derivatives of corticosteroidal hormones are measured in grams... obviously.

        Since there is not always 1-to-1 mapping between these supplementary units, this function tries to occupy the field
        with the most accurate / relevant value, based on the available odoo units of measure. When the customer does not have
        inventory installed, or has left the UoM otherwise undefined, the default 'unit' UoM is used. In this case the quantity
        is used as the supplementary unit.
        """

        supp_unit_dict = {
            'p/st': {'uom_id': self.env.ref('uom.product_uom_unit'), 'factor': 1},
            'pa': {'uom_id': self.env.ref('uom.product_uom_unit'), 'factor': 2},
            '100 p/st': {'uom_id': self.env.ref('uom.product_uom_unit'), 'factor': 100},
            '1000 p/st': {'uom_id': self.env.ref('uom.product_uom_unit'), 'factor': 1000},
            'g': {'uom_id': self.env.ref('uom.product_uom_gram'), 'factor': 1},
            'm': {'uom_id': self.env.ref('uom.product_uom_meter'), 'factor': 1},
            'l': {'uom_id': self.env.ref('uom.product_uom_litre'), 'factor': 1},
        }

        # Transform the dictionary to the form Commodity code -> Supplementary unit name
        commodity_to_supp_code = {}
        for key in SUPP_TO_COMMODITY:
            commodity_to_supp_code.update({v: key for v in SUPP_TO_COMMODITY[key]})

        for vals in query_results:
            commodity_code = vals['commodity_code']
            supp_code = commodity_to_supp_code.get(commodity_code)
            supp_unit = supp_unit_dict.get(supp_code)
            if not supp_code or not supp_unit:
                vals['supplementary_units'] = None
                continue

            # If the supplementary unit is undefined here, the best we can do is
            uom_id, uom_category_id = vals['uom_id'], vals['uom_category_id']

            if uom_id == supp_unit['uom_id'].id:
                vals['supplementary_units'] = vals['line_quantity'] / supp_unit['factor']
            else:
                if uom_category_id == supp_unit['uom_id'].category_id.id:
                    vals['supplementary_units'] = self.env['uom.uom'].browse(uom_id)._compute_quantity(vals['line_quantity'], supp_unit['uom_id']) / supp_unit['factor']
                else:
                    vals['supplementary_units'] = None

        return query_results

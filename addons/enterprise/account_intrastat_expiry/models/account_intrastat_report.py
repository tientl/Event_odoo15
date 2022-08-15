# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api, _

from datetime import datetime
from collections import defaultdict


class IntrastatExpiryReport(models.AbstractModel):
    _inherit = 'account.intrastat.report'

    @api.model
    def _build_query(self, date_from, date_to, journal_ids, invoice_types=None, with_vat=False):
        query, params = super()._build_query(date_from, date_to, journal_ids, invoice_types, with_vat)
        query['select'] = """
            transaction.expiry_date <= invoice_date AS expired_trans,
            transaction.start_date > invoice_date AS premature_trans,
            code.expiry_date <= invoice_date AS expired_comm,
            code.start_date > invoice_date AS premature_comm,
            prod.id AS product_id,
			prodt.categ_id AS template_categ,
        """ + query['select']
        return query, params

    @api.model
    def _create_intrastat_report_line(self, options, vals):
        for error, val_key in (
            ('expired_trans', 'invoice_id'),
            ('premature_trans', 'invoice_id'),
            ('expired_comm', 'product_id'),
            ('premature_comm', 'product_id'),
            ('expired_categ_comm', 'template_categ'),
            ('premature_categ_comm', 'template_categ'),
        ):
            if vals.get(error):
                options['warnings'][error].add(vals[val_key])

        return super()._create_intrastat_report_line(options, vals)

    @api.model
    def _get_lines(self, options, line_id=None):
        options['warnings'] = defaultdict(set)
        res = super()._get_lines(options, line_id)
        options['warnings'] = {k: list(v) for k, v in options['warnings'].items()}
        return res

    def action_invalid_code_moves(self, options, params):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invalid transaction intrastat code entries.'),
            'res_model': 'account.move',
            'views': [(False, 'tree'), (False, 'form')],
            'domain': [('id', 'in', options['warnings'][params['option_key']])],
            'context': {'create': False, 'delete': False},
        }

    def action_invalid_code_products(self, options, params):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invalid commodity intrastat code products.'),
            'res_model': 'product.product',
            'views': [(
                self.env.ref('account_intrastat_expiry.product_product_tree_view_account_intrastat_expiry').id,
                'list',
            ), (False, 'form')],
            'domain': [('id', 'in', options['warnings'][params['option_key']])],
            'context': {
                'create': False,
                'delete': False,
                'expand': True,
            },
        }

    def action_invalid_code_product_categories(self, options, params):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invalid commodity intrastat code product categories.'),
            'res_model': 'product.category',
            'views': [(
                self.env.ref('account_intrastat_expiry.product_category_tree_view_account_intrastat_expiry').id,
                # False,
                'list',
            ), (False, 'form')],
            'domain': [('id', 'in', options['warnings'][params['option_key']])],
            'context': {
                'create': False,
                'delete': False,
                'search_default_group_by_intrastat_id': True,
                'expand': True,
            },
        }

    @api.model
    def _fill_missing_values(self, vals_list):
        vals_with_no_commodity_code = []
        for vals in vals_list:
            # set transaction_code default value if none, code "1" is expired from 2022-01-01, replaced by code "11"
            if not vals['transaction_code']:
                vals['transaction_code'] = 1 if vals['invoice_date'] < datetime.strptime('2022-01-01', '%Y-%m-%d').date() else 11
            # Keep track of vals with no commodity code. If vals has code after super() call, we know the code comes from the product's category.
            if not vals['commodity_code']:
                vals_with_no_commodity_code.append(vals)

        res = super()._fill_missing_values(vals_list)

        codes_from_prod_categ = [x['commodity_code'] for x in vals_with_no_commodity_code if x['commodity_code']]
        commodity_code_by_code = {
            record.code: record
            for record in self.env['account.intrastat.code'].search([('code', 'in', codes_from_prod_categ)])
        }

        for vals in vals_with_no_commodity_code:
            if vals['commodity_code']:
                # if vals now has a commodity_code, it's from it's product category
                commodity_code = commodity_code_by_code[vals['commodity_code']]
                if commodity_code.expiry_date and commodity_code.expiry_date <= vals['invoice_date']:
                    vals['expired_categ_comm'] = True
                if commodity_code.start_date and commodity_code.start_date > vals['invoice_date']:
                    vals['premature_categ_comm'] = True

        return res

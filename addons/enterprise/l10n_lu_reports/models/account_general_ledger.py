# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from itertools import groupby
import base64
import io

from odoo import api, models, tools, _
from odoo.exceptions import UserError


class AccountGeneralLedger(models.AbstractModel):
    _inherit = 'account.general.ledger'

    def _get_reports_buttons(self, options):
        res = super()._get_reports_buttons(options)
        if self._get_report_country_code(options) == 'LU':
            res.append({'name': _('FAIA'), 'sequence': 3, 'action': 'print_xml', 'file_export_type': _('XML')})
        return res

    @api.model
    def _fill_l10n_lu_saft_report_invoices_values(self, options, values):
        res = {
            'total_invoices_debit': 0.0,
            'total_invoices_credit': 0.0,
            'invoice_vals_list': [],
            'uoms': [],
            'product_vals_list': [],
        }

        # Fill 'total_invoices_debit', 'total_invoices_credit', 'invoice_vals_list'.
        encountered_product_ids = set()
        encountered_product_uom_ids = set()
        for move_vals in values['move_vals_list']:
            if move_vals['type'] not in ('out_invoice', 'out_refund'):
                continue

            move_vals.update({
                'invoice_line_vals_list': [],
                'tax_detail_vals_list': [],
                'total_invoice_untaxed_balance': 0.0,
                'total_invoice_tax_balance': 0.0,
            })

            for line_vals in move_vals['line_vals_list']:
                if line_vals['tax_line_id']:
                    move_vals['tax_detail_vals_list'].append({
                        'currency_id': line_vals['currency_id'],
                        'tax_id': line_vals['tax_line_id'],
                        'tax_name': line_vals['tax_name'],
                        'tax_amount': line_vals['tax_amount'],
                        'tax_amount_type': line_vals['tax_amount_type'],
                        'amount': line_vals['balance'],
                        'amount_currency': line_vals['amount_currency'],
                        'rate': line_vals['rate'],
                    })
                    move_vals['total_invoice_tax_balance'] -= line_vals['balance']
                elif not line_vals['account_internal_type'] in ('receivable', 'payable') and not line_vals['exclude_from_invoice_tab']:
                    move_vals['total_invoice_untaxed_balance'] -= line_vals['balance']
                    if line_vals['balance'] > 0.0:
                        res['total_invoices_debit'] += line_vals['balance']
                    else:
                        res['total_invoices_credit'] -= line_vals['balance']
                    if line_vals['product_id']:
                        encountered_product_ids.add(line_vals['product_id'])
                    if line_vals['product_uom_id']:
                        encountered_product_uom_ids.add(line_vals['product_uom_id'])
                    move_vals['invoice_line_vals_list'].append(line_vals)

            res['invoice_vals_list'].append(move_vals)
            move_vals['total_invoice_balance'] = move_vals['total_invoice_untaxed_balance'] + move_vals['total_invoice_tax_balance']

        # Fill 'uoms'.
        uoms = self.env['uom.uom'].browse(list(encountered_product_uom_ids))
        non_ref_uoms = uoms.filtered(lambda uom: uom.uom_type != 'reference')
        if non_ref_uoms:
            # search base UoM for UoM master table
            uoms |= self.env['uom.uom'].search([('category_id', 'in', non_ref_uoms.category_id.ids), ('uom_type', '=', 'reference')])
        res['uoms'] = uoms

        # Fill 'product_vals_list'.
        self._cr.execute('''
            SELECT
                product.id,
                product.barcode,
                product_template.name,
                product.product_tmpl_id,
                product.default_code,
                product_category.name               AS product_category,
                uom.name                            AS standard_uom,
                uom.uom_type                        AS uom_type,
                TRUNC(uom.factor, 8)                AS uom_ratio,
                CASE
                    WHEN uom.factor != 0
                    THEN TRUNC((1.0 / uom.factor), 8)
                    ELSE 0
                END                                 AS ratio,
                base_uom.name                       AS base_uom
            FROM product_product product
                LEFT JOIN product_template          ON product_template.id = product.product_tmpl_id
                LEFT JOIN product_category          ON product_category.id = product_template.categ_id
                LEFT JOIN uom_uom uom               ON uom.id = product_template.uom_id
                LEFT JOIN uom_uom base_uom          ON base_uom.category_id = uom.category_id AND base_uom.uom_type='reference'
            WHERE product.id in %s
            ORDER BY default_code
        ''', [tuple(encountered_product_ids)])

        res['product_vals_list'] = self._cr.dictfetchall()
        duplicate_product_codes = set()
        empty_product_codes = set()
        for product_code, grouped_products in groupby(res['product_vals_list'], key=lambda product: product['default_code']):
            product_list = list(grouped_products)
            if not product_code:
                empty_product_codes.add(product_list[0]['name'])
            elif len(product_list) > 1:
                for product in product_list:
                    duplicate_product_codes.add(product['name'])
        if duplicate_product_codes:
            raise UserError(_(
                "Below products has duplicated `Internal Reference`, please make them unique:\n`%s`.",
                ', '.join(duplicate_product_codes),
            ))
        if empty_product_codes:
            raise UserError(_(
                "Please define `Internal Reference` for below products:\n`%s`.",
                ', '.join(empty_product_codes),
            ))

        values.update(res)

    @api.model
    def _prepare_saft_report_values(self, options):
        # OVERRIDE
        template_vals = super()._prepare_saft_report_values(options)

        if self.env.company.account_fiscal_country_id.code != 'LU':
            return template_vals

        template_vals.update({
            'xmlns': 'urn:OECD:StandardAuditFile-Taxation/2.00',
            'file_version': '2.01',
            'accounting_basis': 'Invoice Accounting',
        })
        self._fill_l10n_lu_saft_report_invoices_values(options, template_vals)
        return template_vals

    @api.model
    def get_xml(self, options):
        # OVERRIDE
        content = super().get_xml(options)

        if self.env.company.account_fiscal_country_id.code != 'LU':
            return content

        xsd_attachment = self.env['ir.attachment'].search([('name', '=', 'xsd_cached_FAIA_v_2_01_reduced_version_A_xsd')])
        if xsd_attachment:
            with io.BytesIO(base64.b64decode(xsd_attachment.with_context(bin_size=False).datas)) as xsd:
                tools.xml_utils._check_with_xsd(content, xsd)
        return content

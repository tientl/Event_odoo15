# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from copy import deepcopy
from collections import defaultdict
import xml.dom.minidom
import re

from odoo.tools import float_repr
from odoo import api, fields, models, release, _
from odoo.exceptions import UserError


class AccountGeneralLedger(models.AbstractModel):
    _inherit = "account.general.ledger"

    @api.model
    def _fill_saft_report_general_ledger_values(self, options, values):
        res = {
            'total_debit_in_period': 0.0,
            'total_credit_in_period': 0.0,
            'account_vals_list': [],
            'journal_vals_list': [],
            'move_vals_list': [],
            'tax_detail_per_line_map': {},
        }

        # Fill 'account_vals_list'.
        accounts_results, dummy = self._do_query([options])
        for account, periods_results in accounts_results:
            # Detail for each account.
            results = periods_results[0]
            account_init_bal = results.get('initial_balance', {})
            account_un_earn = results.get('unaffected_earnings', {})
            account_balance = results.get('sum', {})
            opening_balance = account_init_bal.get('debit', 0.0) \
                              + account_un_earn.get('debit', 0.0) \
                              - account_init_bal.get('credit', 0.0) \
                              - account_un_earn.get('credit', 0.0)
            closing_balance = account_balance.get('debit', 0.0) - account_balance.get('credit', 0.0)
            res['account_vals_list'].append({
                'account': account,
                'opening_balance': opening_balance,
                'closing_balance': closing_balance,
            })

        # Fill 'total_debit_in_period', 'total_credit_in_period', 'move_vals_list'.
        tables, where_clause, where_params = self._query_get(options)
        query = '''
            SELECT
                account_move_line.id,
                account_move_line.date,
                account_move_line.name,
                account_move_line.account_id,
                account_move_line.partner_id,
                account_move_line.currency_id,
                account_move_line.amount_currency,
                account_move_line.debit,
                account_move_line.credit,
                account_move_line.balance,
                account_move_line.exclude_from_invoice_tab,
                account_move_line.tax_line_id,
                account_move_line.quantity,
                account_move_line.price_unit,
                account_move_line.product_id,
                account_move_line.product_uom_id,
                account_move_line__move_id.id               AS move_id,
                account_move_line__move_id.name             AS move_name,
                account_move_line__move_id.move_type        AS move_type,
                account_move_line__move_id.create_date      AS move_create_date,
                account_move_line__move_id.invoice_date     AS move_invoice_date,
                account_move_line__move_id.invoice_origin   AS move_invoice_origin,
                tax.id                                      AS tax_id,
                tax.name                                    AS tax_name,
                tax.amount                                  AS tax_amount,
                tax.amount_type                             AS tax_amount_type,
                journal.id                                  AS journal_id,
                journal.code                                AS journal_code,
                journal.name                                AS journal_name,
                journal.type                                AS journal_type,
                account.internal_type                       AS account_internal_type,
                currency.name                               AS currency_code,
                product.default_code                        AS product_default_code,
                uom.name                                    AS product_uom_name
            FROM ''' + tables + '''
            JOIN account_journal journal ON journal.id = account_move_line.journal_id
            JOIN account_account account ON account.id = account_move_line.account_id
            JOIN res_currency currency ON currency.id = account_move_line.currency_id
            LEFT JOIN product_product product ON product.id = account_move_line.product_id
            LEFT JOIN uom_uom uom ON uom.id = account_move_line.product_uom_id
            LEFT JOIN account_tax tax ON tax.id = account_move_line.tax_line_id
            WHERE ''' + where_clause + '''
            ORDER BY account_move_line.date, account_move_line.id
        '''
        self._cr.execute(query, where_params)

        journal_vals_map = {}
        move_vals_map = {}
        inbound_types = self.env['account.move'].get_inbound_types(include_receipts=True)
        for line_vals in self._cr.dictfetchall():
            line_vals['rate'] = abs(line_vals['amount_currency']) / abs(line_vals['balance']) if line_vals['balance'] else 1.0
            line_vals['tax_detail_vals_list'] = []

            journal_vals_map.setdefault(line_vals['journal_id'], {
                'id': line_vals['journal_id'],
                'name': line_vals['journal_name'],
                'type': line_vals['journal_type'],
                'move_vals_map': {},
            })
            journal_vals = journal_vals_map[line_vals['journal_id']]

            move_vals = {
                'id': line_vals['move_id'],
                'name': line_vals['move_name'],
                'type': line_vals['move_type'],
                'sign': -1 if line_vals['move_type'] in inbound_types else 1,
                'invoice_date': line_vals['move_invoice_date'],
                'invoice_origin': line_vals['move_invoice_origin'],
                'date': line_vals['date'],
                'create_date': line_vals['move_create_date'],
                'partner_id': line_vals['partner_id'],
                'line_vals_list': [],
            }
            move_vals_map.setdefault(line_vals['move_id'], move_vals)
            journal_vals['move_vals_map'].setdefault(line_vals['move_id'], move_vals)

            move_vals = move_vals_map[line_vals['move_id']]
            move_vals['line_vals_list'].append(line_vals)

            # Track the total debit/period of the whole period.
            res['total_debit_in_period'] += line_vals['debit']
            res['total_credit_in_period'] += line_vals['credit']

            res['tax_detail_per_line_map'][line_vals['id']] = line_vals

        # Fill 'journal_vals_list'.
        for journal_vals in journal_vals_map.values():
            journal_vals['move_vals_list'] = list(journal_vals.pop('move_vals_map').values())
            res['journal_vals_list'].append(journal_vals)
            res['move_vals_list'] += journal_vals['move_vals_list']

        # Add newly computed values to the final template values.
        values.update(res)

    @api.model
    def _fill_saft_report_tax_details_values(self, options, values):
        tax_vals_map = {}

        tables, where_clause, where_params = self._query_get(options)
        tax_details_query, tax_details_params = self.env['account.move.line']._get_query_tax_details(tables, where_clause, where_params)
        self._cr.execute(f'''
            SELECT
                tax_detail.base_line_id,
                tax_line.currency_id,
                tax.id AS tax_id,
                tax.amount_type AS tax_amount_type,
                tax.name AS tax_name,
                tax.amount AS tax_amount,
                SUM(tax_detail.tax_amount) AS amount,
                SUM(tax_detail.tax_amount) AS amount_currency
            FROM ({tax_details_query}) AS tax_detail
            JOIN account_move_line tax_line ON tax_line.id = tax_detail.tax_line_id
            JOIN account_tax tax ON tax.id = tax_detail.tax_id
            GROUP BY tax_detail.base_line_id, tax_line.currency_id, tax.id
        ''', tax_details_params)
        for tax_vals in self._cr.dictfetchall():
            line_vals = values['tax_detail_per_line_map'][tax_vals['base_line_id']]
            line_vals['tax_detail_vals_list'].append({
                **tax_vals,
                'rate': line_vals['rate'],
            })
            tax_vals_map.setdefault(tax_vals['tax_id'], {
                'id': tax_vals['tax_id'],
                'name': tax_vals['tax_name'],
                'amount': tax_vals['tax_amount'],
                'amount_type': tax_vals['tax_amount_type'],
            })

        # Fill 'tax_vals_list'.
        values['tax_vals_list'] = list(tax_vals_map.values())

    @api.model
    def _fill_saft_report_partner_ledger_values(self, options, values):
        res = {
            'customer_vals_list': [],
            'supplier_vals_list': [],
            'partner_detail_map': defaultdict(lambda: {
                'type': False,
                'addresses': [],
                'contacts': [],
            }),
        }

        all_partners = self.env['res.partner']

        # Fill 'customer_vals_list' and 'supplier_vals_list'
        new_options = dict(options)
        new_options['account_type'] = [
            {'id': 'receivable', 'selected': True},
            {'id': 'payable', 'selected': True},
        ]
        partners_results = self.env['account.partner.ledger']._do_query(new_options)
        partner_vals_list = []
        for partner, results in partners_results:
            # Ignore Falsy partner.
            if not partner:
                continue

            all_partners |= partner

            partner_sum = results.get('sum', {})
            partner_init_bal = results.get('initial_balance', {})

            opening_balance = partner_init_bal.get('debit', 0.0) \
                              - partner_init_bal.get('credit', 0.0)
            closing_balance = partner_init_bal.get('debit', 0.0) \
                              + partner_sum.get('debit', 0.0) \
                              - partner_init_bal.get('credit', 0.0) \
                              - partner_sum.get('credit', 0.0)
            partner_vals_list.append({
                'partner': partner,
                'opening_balance': opening_balance,
                'closing_balance': closing_balance,
            })

        if all_partners:
            domain = [('partner_id', 'in', tuple(all_partners.ids))]
            tables, where_clause, where_params = self._query_get(new_options, domain=domain)
            self._cr.execute(f'''
                SELECT
                    account_move_line.partner_id,
                    SUM(account_move_line.balance)
                FROM {tables}
                JOIN account_account account ON account.id = account_move_line.account_id
                WHERE {where_clause}
                AND account.internal_type IN ('receivable', 'payable')
                GROUP BY account_move_line.partner_id
            ''', where_params)

            for partner_id, balance in self._cr.fetchall():
                res['partner_detail_map'][partner_id]['type'] = 'customer' if balance >= 0.0 else 'supplier'

        for partner_vals in partner_vals_list:
            partner_id = partner_vals['partner'].id
            if res['partner_detail_map'][partner_id]['type'] == 'customer':
                res['customer_vals_list'].append(partner_vals)
            elif res['partner_detail_map'][partner_id]['type'] == 'supplier':
                res['supplier_vals_list'].append(partner_vals)

        # Fill 'partner_detail_map'.
        all_partners |= values['company'].partner_id
        partner_addresses_map = defaultdict(dict)
        partner_contacts_map = defaultdict(lambda: self.env['res.partner'])

        def _track_address(current_partner, partner):
            if partner.zip and partner.city:
                address_key = (partner.zip, partner.city)
                partner_addresses_map[current_partner][address_key] = partner

        def _track_contact(current_partner, partner):
            phone = partner.phone or partner.mobile
            if phone:
                partner_contacts_map[current_partner] |= partner

        for partner in all_partners:
            _track_address(partner, partner)
            _track_contact(partner, partner)
            for child in partner.child_ids:
                _track_address(partner, child)
                _track_contact(partner, child)

        no_partner_address = self.env['res.partner']
        no_partner_contact = self.env['res.partner']
        for partner in all_partners:
            res['partner_detail_map'][partner.id].update({
                'partner': partner,
                'addresses': list(partner_addresses_map[partner].values()),
                'contacts': partner_contacts_map[partner],
            })
            if not res['partner_detail_map'][partner.id]['addresses']:
                no_partner_address |= partner
            if not res['partner_detail_map'][partner.id]['contacts']:
                no_partner_contact |= partner

        if no_partner_address:
            raise UserError(_(
                "Please define at least one address (Zip/City) for the following partners: %s.",
                ', '.join(no_partner_address.mapped('display_name')),
            ))
        if no_partner_contact:
            raise UserError(_(
                "Please define at least one contact (Phone or Mobile) for the following partners: %s.",
                ', '.join(no_partner_contact.mapped('display_name')),
            ))

        # Add newly computed values to the final template values.
        values.update(res)

    @api.model
    def _prepare_saft_report_values(self, options):
        def format_float(amount, digits=2):
            return float_repr(amount or 0.0, precision_digits=digits)

        def format_date(date_str, formatter):
            date_obj = fields.Date.to_date(date_str)
            return date_obj.strftime(formatter)

        company = self.env.company
        if not company.company_registry:
            raise UserError(_("Please define `Company Registry` for your company."))

        template_values = {
            'company': company,
            'xmlns': '',
            'file_version': 'undefined',
            'accounting_basis': 'undefined',
            'today_str': fields.Date.to_string(fields.Date.context_today(self)),
            'software_version': release.version,
            'date_from': options['date']['date_from'],
            'date_to': options['date']['date_to'],
            'format_float': format_float,
            'format_date': format_date,
        }
        self._fill_saft_report_general_ledger_values(options, template_values)
        self._fill_saft_report_tax_details_values(options, template_values)
        self._fill_saft_report_partner_ledger_values(options, template_values)
        return template_values

    def get_xml(self, options):
        options = deepcopy(options)
        options = self._force_strict_range(options)
        options.pop('multi_company', None)
        options['unfolded_lines'] = []
        options['unfold_all'] = False

        template_vals = self._prepare_saft_report_values(options)
        content = self.env.ref('account_saft.saft_template')._render(template_vals)

        # Indent the XML data and return as Pretty XML string and remove extra new lines.
        pretty_xml = xml.dom.minidom.parseString(content).toprettyxml()
        return "\n".join(re.split(r'\n\s*\n', pretty_xml)).encode()

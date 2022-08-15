# -*- coding: utf-8 -*-

import calendar
import json
from collections import namedtuple

from dateutil.rrule import rrule, MONTHLY

from odoo import models, fields, tools, release, _
from odoo.exceptions import UserError
from odoo.tools.xml_utils import _check_with_xsd


class ReportAccountGeneralLedger(models.AbstractModel):
    _inherit = 'account.general.ledger'

    def _get_reports_buttons(self, options):
        buttons = super(ReportAccountGeneralLedger, self)._get_reports_buttons(options)
        buttons.append({'name': _('XAF'), 'sequence': 3, 'action': 'l10n_nl_print_xaf', 'file_export_type': _('XAF')})
        return buttons

    def _get_opening_balance_vals(self, options):
        new_options = self.env['account.partner.ledger']._get_options_initial_balance(options)
        tables, where_clause, where_params = self._query_get(new_options)
        self.env.cr.execute(f"""
            SELECT acc.id AS account_id,
                   acc.code AS account_code,
                   COUNT(*) AS lines_count,
                   SUM(account_move_line.debit) AS sum_debit,
                   SUM(account_move_line.credit) AS sum_credit
            FROM {tables}
            JOIN account_account acc ON account_move_line.account_id = acc.id
            JOIN account_account_type acc_type ON acc_type.id = acc.user_type_id
            WHERE {where_clause}
            AND acc_type.include_initial_balance
            GROUP BY acc.id
        """, where_params)

        opening_lines = []
        lines_count = 0
        sum_debit = 0
        sum_credit = 0
        for query_res in self.env.cr.dictfetchall():
            lines_count += query_res['lines_count']
            sum_debit += query_res['sum_debit']
            sum_credit += query_res['sum_credit']

            opening_lines.append({
                'id': query_res['account_id'],
                'account_code': query_res['account_code'],
                'balance': query_res['sum_debit'] - query_res['sum_credit'],
            })

        return {
            'opening_lines_count': lines_count,
            'opening_debit': sum_debit,
            'opening_credit': sum_credit,
            'opening_lines': opening_lines,
        }

    def _compute_period_number(self, date_str):
        date = fields.Date.from_string(date_str)
        return date.strftime('%y%m')[1:]

    def get_xaf(self, options):

        company = self.env.company
        msgs = []

        if not company.vat:
            msgs.append(_('- VAT number'))
        if not company.country_id:
            msgs.append(_('- Country'))

        if msgs:
            msgs = [_('Some fields must be specified on the company:')] + msgs
            raise UserError('\n'.join(msgs))

        date_from = options['date']['date_from']
        date_to = options['date']['date_to']
        # Retrieve periods values
        periods = []
        Period = namedtuple('Period', 'number name date_from date_to')
        for period in rrule(freq=MONTHLY, bymonth=(), dtstart=fields.Date.from_string(date_from),
                            until=fields.Date.from_string(date_to)):
            period_from = fields.Date.to_string(period.date())
            period_to = period.replace(day=calendar.monthrange(period.year, period.month)[1])
            period_to = fields.Date.to_string(period_to.date())
            periods.append(Period(
                number=self._compute_period_number(period_from),
                name=period.strftime('%B') + ' ' + date_from[0:4],
                date_from=period_from,
                date_to=period_to
            ))

        # A new computation engine and a new template were created to solve a memory error in stable (13.0).
        if self.env.ref('l10n_nl_reports.xaf_audit_file_v2', raise_if_not_found=False):
            return self._l10n_nl_reports_get_xaf_v2(options, company, date_from, date_to, periods)

        def cust_sup_tp(partner_id):
            if partner_id.supplier_rank and partner_id.customer_rank:
                return 'B'
            if partner_id.supplier_rank:
                return 'C'
            if partner_id.customer_rank:
                return 'S'
            return 'O'

        def acc_tp(account_id):
            if account_id.user_type_id.type in ['income', 'expense']:
                return 'P'
            if account_id.user_type_id.type in ['asset', 'liability']:
                return 'B'
            return 'M'

        def jrn_tp(journal_id):
            if journal_id.type == 'bank':
                return 'B'
            if journal_id.type == 'cash':
                return 'C'
            if journal_id.type == 'situation':
                return 'O'
            if journal_id.type in ['sale', 'sale_refund']:
                return 'S'
            if journal_id.type in ['purchase', 'purchase_refund']:
                return 'P'
            return 'Z'

        def amnt_tp(move_line_id):
            return 'C' if move_line_id.credit else 'D'

        def change_date_time(record):
            return record.write_date.strftime('%Y-%m-%dT%H:%M:%S')

        # Retrieve move lines values
        total_query = """
            SELECT COUNT(*),
                   SUM(l.debit),
                   SUM(l.credit),
                   ARRAY_AGG(DISTINCT l.partner_id) FILTER (WHERE l.partner_id IS NOT NULL),
                   ARRAY_AGG(DISTINCT l.account_id),
                   ARRAY_AGG(DISTINCT l.journal_id),
                   ARRAY_AGG(DISTINCT l.tax_line_id) FILTER (WHERE l.tax_line_id IS NOT NULL)
            FROM account_move_line l, account_move m
            WHERE l.move_id = m.id
            AND l.date >= %s
            AND l.date <= %s
            AND l.company_id = %s
            AND l.display_type IS NULL
            AND m.state = 'posted'
        """
        self.env.cr.execute(total_query, (date_from, date_to, company.id,))
        moves_count, moves_debit, moves_credit, partner_ids, account_ids, journal_ids, tax_ids = self.env.cr.fetchall()[0]
        # Retrieve journal values
        journal_x_moves = {}
        if journal_ids:
            journal_query = """
                SELECT j.id,
                       ARRAY_AGG(DISTINCT m.id)
                FROM account_move m
                JOIN account_journal j ON m.journal_id = j.id
                WHERE j.id IN %s
                AND m.date >= %s
                AND m.date <= %s
                AND m.company_id = %s
                AND m.state = 'posted'
                GROUP BY j.id
            """
            self.env.cr.execute(journal_query, (tuple(journal_ids), date_from, date_to, company.id,))
            journal_x_moves = {
                self.env['account.journal'].browse(journal_id): self.env['account.move'].browse(move_ids)
                for journal_id, move_ids in self.env.cr.fetchall()
            }
        values = {
            **self._get_opening_balance_vals(options),
            'company_id': company,
            'partner_ids': self.env['res.partner'].browse(partner_ids),
            'account_ids': self.env['account.account'].browse(account_ids),
            'journal_ids': self.env['account.journal'].browse(journal_ids),
            'journal_x_moves': journal_x_moves,
            'compute_period_number': self._compute_period_number,
            'periods': periods,
            'tax_ids': self.env['account.tax'].browse(tax_ids),
            'cust_sup_tp': cust_sup_tp,
            'acc_tp': acc_tp,
            'jrn_tp': jrn_tp,
            'amnt_tp': amnt_tp,
            'change_date_time': change_date_time,
            'fiscal_year': date_from[0:4],
            'date_from': date_from,
            'date_to': date_to,
            'date_created': fields.Date.context_today(self),
            'software_version': release.version,
            'moves_count': moves_count,
            'moves_debit': moves_debit or 0.0,
            'moves_credit': moves_credit or 0.0,
        }
        audit_content = self.env['ir.qweb']._render('l10n_nl_reports.xaf_audit_file', values)
        with tools.file_open('l10n_nl_reports/data/xml_audit_file_3_2.xsd', 'rb') as xsd:
            _check_with_xsd(audit_content, xsd)

        return audit_content

    def _l10n_nl_reports_get_xaf_v2(self, options, company, date_from, date_to, periods):
        def cust_sup_tp(customer, supplier):
            if supplier and customer:
                return 'B'
            if supplier:
                return 'C'
            if customer:
                return 'S'
            return 'O'

        def acc_tp(account_type):
            if account_type in ['income', 'expense']:
                return 'P'
            if account_type in ['asset', 'liability']:
                return 'B'
            return 'M'

        def jrn_tp(journal_type):
            if journal_type == 'bank':
                return 'B'
            if journal_type == 'cash':
                return 'C'
            if journal_type == 'situation':
                return 'O'
            if journal_type in ['sale', 'sale_refund']:
                return 'S'
            if journal_type in ['purchase', 'purchase_refund']:
                return 'P'
            return 'Z'

        def amnt_tp(credit):
            return 'C' if credit else 'D'

        def change_date_time(date):
            return date.strftime('%Y-%m-%dT%H:%M:%S')

        def get_vals_dict():
            new_options = self.env['account.partner.ledger']._get_options_sum_balance(options)
            tables, where_clause, where_params = self._query_get(new_options)

            # Count the total number of lines to be used in the batching
            self.env.cr.execute(f"SELECT COUNT(*) FROM {tables} WHERE {where_clause}", where_params)
            count = self.env.cr.fetchone()[0]
            batch_size = 10**4
            # Create a list to store the query results during the batching
            res_list = []

            for offset in range(0, count, batch_size):
                self.env.cr.execute(f"""
                    SELECT journal.id AS journal_id,
                           journal.name AS journal_name,
                           journal.code AS journal_code,
                           journal.type AS journal_type,
                           account_move_line__move_id.id AS move_id,
                           account_move_line__move_id.name AS move_name,
                           account_move_line__move_id.date AS move_date,
                           account_move_line__move_id.amount_total AS move_amount,
                           account_move_line__move_id.move_type IN ('out_invoice', 'out_refund', 'in_refund', 'in_invoice', 'out_receipt', 'in_receipt') AS move_is_invoice,
                           account_move_line.id AS line_id,
                           account_move_line.name AS line_name,
                           account_move_line.display_type AS line_display_type,
                           account_move_line.ref AS line_ref,
                           account_move_line.date AS line_date,
                           account_move_line.credit AS line_credit,
                           account_move_line.debit AS line_debit,
                           account_move_line.balance AS line_balance,
                           account_move_line.full_reconcile_id AS line_reconcile_id,
                           account_move_line.partner_id AS line_partner_id,
                           account_move_line.move_id AS line_move_id,
                           account_move_line.move_name AS line_move_name,
                           account_move_line.amount_currency AS line_amount_currency,
                           account.id AS account_id,
                           account.name AS account_name,
                           account.code AS account_code,
                           account.write_uid AS account_write_uid,
                           account.write_date AS account_write_date,
                           account_type.type AS account_type,
                           reconcile.name AS line_reconcile_name,
                           currency.id AS line_currency_id,
                           currency2.id AS line_company_currency_id,
                           currency.name AS line_currency_name,
                           currency2.name AS line_company_currency_name,
                           partner.id AS partner_id,
                           partner.name AS partner_name,
                           partner.commercial_company_name AS partner_commercial_company_name,
                           partner.commercial_partner_id AS partner_commercial_partner_id,
                           partner.is_company AS partner_is_company,
                           (SELECT contact.name FROM res_partner contact WHERE contact.parent_id = partner.id limit 1) AS partner_contact_name,
                           partner.phone AS partner_phone,
                           partner.email AS partner_email,
                           partner.website AS partner_website,
                           partner.vat AS partner_vat,
                           partner.credit_limit AS partner_credit_limit,
                           partner.street_name AS partner_street_name,
                           partner.street_number AS partner_street_number,
                           partner.street_number2 AS partner_street_number2,
                           partner.city AS partner_city,
                           partner.zip AS partner_zip,
                           state.name AS partner_state_name,
                           partner.country_id AS partner_country_id,
                           partner_bank.id AS partner_bank_id,
                           partner_bank.sanitized_acc_number AS partner_sanitized_acc_number,
                           bank.bic AS partner_bic,
                           partner.write_uid AS partner_write_uid,
                           partner.write_date AS partner_write_date,
                           partner.customer_rank AS partner_customer_rank,
                           partner.supplier_rank AS partner_supplier_rank,
                           country.code AS partner_country_code,
                           tax.id AS tax_id,
                           tax.name AS tax_name
                      FROM {tables}
                      JOIN account_journal journal ON account_move_line.journal_id = journal.id
                      JOIN account_account account ON account_move_line.account_id = account.id
                      JOIN account_account_type account_type ON account.user_type_id = account_type.id
                      LEFT JOIN res_partner partner ON account_move_line.partner_id = partner.id
                      LEFT JOIN account_tax tax ON account_move_line.tax_line_id = tax.id
                      LEFT JOIN account_full_reconcile reconcile ON account_move_line.full_reconcile_id = reconcile.id
                      LEFT JOIN res_currency currency ON account_move_line.currency_id = currency.id
                      LEFT JOIN res_currency currency2 ON account_move_line.company_currency_id = currency2.id
                      LEFT JOIN res_country country ON partner.country_id = country.id
                      LEFT JOIN res_partner_bank partner_bank ON partner.id = partner_bank.partner_id and partner_bank.company_id = account_move_line.company_id
                      LEFT JOIN res_bank bank ON partner_bank.bank_id = bank.id
                      LEFT JOIN res_country_state state ON partner.state_id = state.id
                     WHERE {where_clause}
                     ORDER BY account_move_line.id
                     LIMIT {batch_size}
                    OFFSET {offset}
                """, where_params)
                res_list += self.env.cr.dictfetchall()

            vals_dict = {}
            for row in res_list:
                # Aggregate taxes' values
                if row['tax_id']:
                    vals_dict.setdefault('tax_data', {})
                    vals_dict['tax_data'].setdefault(row['tax_id'], {
                        'tax_id': row['tax_id'],
                        'tax_name': row['tax_name'],
                    })
                # Aggregate accounts' values
                vals_dict.setdefault('account_data', {})
                vals_dict['account_data'].setdefault(row['account_id'], {
                    'account_code': row['account_code'],
                    'account_name': row['account_name'],
                    'account_type': acc_tp(row['account_type']),
                    'account_write_date': change_date_time(row['account_write_date']),
                    'account_write_uid': row['account_write_uid'],
                    'account_xaf_userid': self.env['res.users'].browse(row['account_write_uid']).l10n_nl_report_xaf_userid,
                })
                # Aggregate partners' values
                if row['partner_id']:
                    vals_dict.setdefault('partner_data', {})
                    vals_dict['partner_data'].setdefault(row['partner_id'], {
                        'partner_id': row['partner_id'],
                        # XAF XSD has maximum 50 characters for customer/supplier name
                        'partner_name': (row['partner_name']
                                         or row['partner_commercial_company_name']
                                         or row['partner_commercial_partner_id']
                                         or ('id: ' + str(row['partner_id'])))[:50],
                        'partner_is_company': row['partner_is_company'],
                        'partner_phone': row['partner_phone'],
                        'partner_email': row['partner_email'],
                        'partner_website': row['partner_website'],
                        'partner_vat': row['partner_vat'],
                        'partner_credit_limit': row['partner_credit_limit'],
                        'partner_street_name': row['partner_street_name'],
                        'partner_street_number': row['partner_street_number'],
                        'partner_street_number2': row['partner_street_number2'],
                        'partner_city': row['partner_city'],
                        'partner_zip': row['partner_zip'],
                        'partner_state_name': row['partner_state_name'],
                        'partner_country_id': row['partner_country_id'],
                        'partner_country_code': row['partner_country_code'],
                        'partner_write_uid': row['partner_write_uid'],
                        'partner_xaf_userid': self.env['res.users'].browse(row['partner_write_uid']).l10n_nl_report_xaf_userid,
                        'partner_write_date': change_date_time(row['partner_write_date']),
                        'partner_customer_rank': row['partner_customer_rank'],
                        'partner_supplier_rank': row['partner_supplier_rank'],
                        'partner_type': cust_sup_tp(row['partner_customer_rank'], row['partner_supplier_rank']),
                        'partner_contact_name': row['partner_contact_name'] and row['partner_contact_name'][:50],
                        'partner_bank_data': {},
                    })
                    # Aggregate bank values for each partner
                    if row['partner_bank_id']:
                        vals_dict['partner_data'][row['partner_id']]['partner_bank_data'].setdefault(row['partner_bank_id'], {
                            'partner_sanitized_acc_number': row['partner_sanitized_acc_number'],
                            'partner_bic': row['partner_bic'],
                        })
                # Aggregate journals' values
                vals_dict.setdefault('journal_data', {})
                vals_dict['journal_data'].setdefault(row['journal_id'], {
                    'journal_name': row['journal_name'],
                    'journal_code': row['journal_code'],
                    'journal_type': jrn_tp(row['journal_type']),
                    'journal_move_data': {},
                })
                vals_dict.setdefault('moves_count', 0)
                vals_dict['moves_count'] += 1
                vals_dict.setdefault('moves_credit', 0.0)
                vals_dict['moves_credit'] += row['line_credit']
                vals_dict.setdefault('moves_debit', 0.0)
                vals_dict['moves_debit'] += row['line_debit']
                vals_dict['journal_data'][row['journal_id']]['journal_move_data'].setdefault(row['move_id'], {
                    'move_id': row['move_id'],
                    'move_name': row['move_name'],
                    'move_date': row['move_date'],
                    'move_amount': round(row['move_amount'], 2),
                    'move_period_number': self._compute_period_number(row['move_date']),
                    'move_line_data': {},
                })
                vals_dict['journal_data'][row['journal_id']]['journal_move_data'][row['move_id']]['move_line_data'].setdefault(row['line_id'], {
                        'line_id': row['line_id'],
                        'line_name': row['line_name'],
                        'line_display_type': row['line_display_type'],
                        'line_ref': row['line_ref'] or '/',
                        'line_date': row['line_date'],
                        'line_credit': round(row['line_credit'], 2),
                        'line_debit': round(row['line_debit'], 2),
                        'line_type': amnt_tp(row['line_credit']),
                        'line_account_code': row['account_code'],
                        'line_reconcile_id': row['line_reconcile_id'],
                        'line_reconcile_name': row['line_reconcile_name'],
                        'line_partner_id': row['line_partner_id'],
                        'line_move_name': row['move_is_invoice'] and row['line_move_name'],
                        'line_amount_currency': round(row['line_amount_currency'] if row['line_currency_id'] else row['line_balance'], 2),
                        'line_currency_name': row['line_currency_name'] if row['line_currency_id'] else row['line_company_currency_name'],
                    }
                )

            return vals_dict

        vals_dict = get_vals_dict()
        values = {
            **self._get_opening_balance_vals(options),
            'company': company,
            'account_data': list(vals_dict['account_data'].values()),
            'partner_data': list(vals_dict['partner_data'].values()),
            'journal_data': list(vals_dict['journal_data'].values()),
            'tax_data': list(vals_dict['tax_data'].values()),
            'periods': periods,
            'fiscal_year': date_from[0:4],
            'date_from': date_from,
            'date_to': date_to,
            'date_created': fields.Date.context_today(self),
            'software_version': release.version,
            'moves_count': vals_dict['moves_count'],
            'moves_debit': round(vals_dict['moves_debit'], 2) or 0.0,
            'moves_credit': round(vals_dict['moves_credit'], 2) or 0.0,
        }
        audit_content = self.env['ir.qweb']._render('l10n_nl_reports.xaf_audit_file_v2', values)
        with tools.file_open('l10n_nl_reports/data/xml_audit_file_3_2.xsd', 'rb') as xsd:
            _check_with_xsd(audit_content, xsd)

        return audit_content

    def l10n_nl_print_xaf(self, options):
        return {
                'type': 'ir_actions_account_report_download',
                'data': {'model': self.env.context.get('model'),
                         'options': json.dumps(options),
                         'output_format': 'xaf',
                         'financial_id': self.env.context.get('id'),
                         }
                }

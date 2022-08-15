# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import ast

from odoo import models, fields, api, _
from odoo.tools.misc import format_date


_logger = logging.getLogger(__name__)


class AccountBankReconciliationReport(models.AbstractModel):
    _name = 'account.bank.reconciliation.report'
    _description = 'Bank Reconciliation Report'
    _inherit = "account.report"

    filter_date = {'mode': 'single', 'filter': 'today'}
    filter_all_entries = False

    def _apply_groups(self, columns):
        if self.user_has_groups('base.group_multi_currency') and self.user_has_groups('base.group_no_one'):
            return columns

        return columns[:2] + columns[4:]

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    @api.model
    def _get_unconsistent_statements(self, options, journal):
        ''' Retrieve the account.bank.statements records on the range of the options date having different starting
        balance regarding its previous statement.
        :param options: The report options.
        :param journal: The account.journal from which this report has been opened.
        :return:        An account.bank.statements recordset.
        '''
        return self.env['account.bank.statement'].search([
            ('journal_id', '=', journal.id),
            ('date', '<=', options['date']['date_to']),
            ('is_valid_balance_start', '=', False),
            ('previous_statement_id', '!=', False),
        ])

    @api.model
    def _get_bank_miscellaneous_move_lines_domain(self, options, journal):
        ''' Get the domain to be used to retrieve the journal items affecting the bank accounts but not linked to
        a statement line.
        :param options: The report options.
        :param journal: The account.journal from which this report has been opened.
        :return:        A domain to search on the account.move.line model.
        '''

        if not journal.default_account_id:
            return None

        domain = [
            ('display_type', 'not in', ('line_section', 'line_note')),
            ('move_id.state', '!=', 'cancel'),
            ('account_id', '=', journal.default_account_id.id),
            ('statement_line_id', '=', False),
            ('date', '<=', options['date']['date_to']),
        ]

        if not options['all_entries']:
            domain.append(('move_id.state', '=', 'posted'))

        if journal.company_id.account_opening_move_id:
            domain.append(('move_id', '!=', journal.company_id.account_opening_move_id.id))

        return domain

    def open_unconsistent_statements(self, options, params=None):
        ''' An action opening the account.bank.statement view (form or list) depending the 'unconsistent_statement_ids'
        key set on the options.
        :param options: The report options.
        :param params:  -Not used-.
        :return:        An action redirecting to a view of statements.
        '''
        unconsistent_statement_ids = options.get('unconsistent_statement_ids', [])

        action = {
            'name': _("Inconsistent Statements"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement',
        }
        if len(unconsistent_statement_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': unconsistent_statement_ids[0],
                'views': [(False, 'form')],
            })
        else:
            action.update({
                'view_mode': 'list',
                'domain': [('id', 'in', unconsistent_statement_ids)],
                'views': [(False, 'list')],
            })
        return action

    def open_bank_miscellaneous_move_lines(self, options, params):
        ''' An action opening the account.move.line tree view affecting the bank account balance but not linked to
        a bank statement line.
        :param options: The report options.
        :param params:  -Not used-.
        :return:        An action redirecting to the tree view of journal items.
        '''
        journal = self.env['account.journal'].browse(options['active_id'])

        return {
            'name': _('Journal Items'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_type': 'list',
            'view_mode': 'list',
            'target': 'current',
            'views': [(self.env.ref('account.view_move_line_tree').id, 'list')],
            'domain': self._get_bank_miscellaneous_move_lines_domain(options, journal),
        }

    def action_redirect_to_bank_statement_form(self, options, params):
        ''' Redirect the user to the last bank statement found.
        :param options:     The report options.
        :param params:      The action params containing at least 'statement_id'.
        :return:            A dictionary representing an ir.actions.act_window.
        '''
        last_statement = self.env['account.bank.statement'].browse(params['statement_id'])

        return {
            'name': last_statement.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement',
            'context': {'create': False},
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_id': last_statement.id,
        }

    # -------------------------------------------------------------------------
    # REPORT
    # -------------------------------------------------------------------------

    @api.model
    def _get_templates(self):
        # OVERRIDE
        # - Add a custom main template to add a warning on top about unconsistent bank statements.
        # - Add a custom search template to get a not-editable date filter.
        templates = super()._get_templates()
        templates['main_template'] = 'account_reports.bank_reconciliation_report_main_template'
        return templates

    @api.model
    def _get_report_name(self):
        journal_id = self._context.get('active_id')
        if journal_id:
            journal = self.env['account.journal'].browse(journal_id)
            return _("Bank Reconciliation: %s", journal.name)
        return _("Bank Reconciliation")

    # -------------------------------------------------------------------------
    # COLUMNS / LINES
    # -------------------------------------------------------------------------

    @api.model
    def _get_columns_name(self, options):
        return [
            {'name': ''}
        ] + self._apply_groups([
            {'name': _("Date"), 'class': 'date'},
            {'name': _("Label"), 'class': 'o_account_report_line_ellipsis'},
            {'name': _("Amount Currency"), 'class': 'number'},
            {'name': _("Currency"), 'class': 'number'},
            {'name': _("Amount"), 'class': 'number'},
        ])

    @api.model
    def _build_section_report_lines(self, options, journal, unfolded_lines, total, title, title_hover):
        company_currency = journal.company_id.currency_id
        journal_currency = journal.currency_id if journal.currency_id and journal.currency_id != company_currency else False
        report_currency = journal_currency or company_currency
        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])
        report_lines = []

        if not unfolded_lines:
            return report_lines

        line_id = unfolded_lines[0]['parent_id']
        is_unfolded = unfold_all or line_id in options['unfolded_lines']

        section_report_line = {
            'id': line_id,
            'name': title,
            'title_hover': title_hover,
            'columns': self._apply_groups([
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {
                    'name': self.format_value(total, report_currency),
                    'no_format': total,
                },
            ]),
            'class': 'o_account_reports_totals_below_sections' if self.env.company.totals_below_sections else '',
            'level': 1,
            'unfolded': is_unfolded,
            'unfoldable': True,
        }
        report_lines += [section_report_line] + unfolded_lines

        if self.env.company.totals_below_sections:
            report_lines.append({
                'id': '%s_total' % line_id,
                'name': _("Total %s", section_report_line['name']),
                'columns': section_report_line['columns'],
                'class': 'total',
                'level': 3,
                'parent_id': line_id,
            })
        return report_lines

    @api.model
    def _get_statement_report_lines(self, options, journal):
        ''' Retrieve the journal items used by the statement lines that are not yet reconciled and then, need to be
        displayed inside the report.
        :param options: The report options.
        :param journal: The journal as an account.journal record.
        :return:        The report lines for sections about statement lines.
        '''
        company_currency = journal.company_id.currency_id
        journal_currency = journal.currency_id if journal.currency_id and journal.currency_id != company_currency else False
        report_currency = journal_currency or company_currency
        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])

        if not journal.default_account_id:
            return [], []

        # Compute the percentage corresponding of the remaining amount to reconcile.

        tables, where_clause, where_params = self.with_company(journal.company_id)._query_get(options, domain=[
            ('journal_id', '=', journal.id),
            ('account_id', '!=', journal.default_account_id.id),
        ])

        self._cr.execute('''
            SELECT
                st_line.id,
                move.name,
                move.ref,
                move.date,
                st_line.payment_ref,
                st_line.amount,
                st_line.amount_currency,
                st_line.foreign_currency_id,
                COALESCE(SUM(CASE WHEN account_move_line.account_id = %s THEN account_move_line.balance ELSE 0.0 END), 0.0) AS suspense_balance,
                COALESCE(SUM(CASE WHEN account_move_line.account_id = %s THEN 0.0 ELSE account_move_line.balance END), 0.0) AS other_balance
            FROM ''' + tables + '''
            JOIN account_bank_statement_line st_line ON st_line.move_id = account_move_line.move_id
            JOIN account_move move ON move.id = st_line.move_id
            WHERE ''' + where_clause + '''
                AND NOT st_line.is_reconciled
            GROUP BY
                st_line.id,
                move.name,
                move.ref,
                move.date,
                st_line.amount,
                st_line.amount_currency,
                st_line.foreign_currency_id
            ORDER BY st_line.statement_id DESC, move.date, st_line.sequence, st_line.id DESC
        ''', [journal.suspense_account_id.id, journal.suspense_account_id.id] + where_params)

        plus_report_lines = []
        less_report_lines = []
        plus_total = 0.0
        less_total = 0.0

        for res in self._cr.dictfetchall():

            # Rate representing the remaining percentage to be reconciled with something.
            reconcile_rate = abs(res['suspense_balance']) / (abs(res['suspense_balance']) + abs(res['other_balance']))

            amount = res['amount'] * reconcile_rate

            if res['foreign_currency_id']:
                # Foreign currency.

                amount_currency = res['amount_currency'] * reconcile_rate
                foreign_currency = self.env['res.currency'].browse(res['foreign_currency_id'])

                monetary_columns = [
                    {
                        'name': self.format_value(amount_currency, foreign_currency),
                        'no_format': amount_currency,
                    },
                    {'name': foreign_currency.name},
                    {
                        'name': self.format_value(amount, report_currency),
                        'no_format': amount,
                    },
                ]
            else:
                # Single currency.

                monetary_columns = [
                    {'name': ''},
                    {'name': ''},
                    {
                        'name': self.format_value(amount, report_currency),
                        'no_format': amount,
                    },
                ]

            st_report_line = {
                'name': res['name'],
                'columns': self._apply_groups([
                    {'name': format_date(self.env, res['date']), 'class': 'date'},
                    {'name': self._format_aml_name(res['payment_ref'], res['ref'], '/')},
                ] + monetary_columns),
                'model': 'account.bank.statement.line',
                'caret_options': 'account.bank.statement',
                'level': 3,
            }

            residual_amount = monetary_columns[2]['no_format']
            if residual_amount > 0.0:
                st_report_line['parent_id'] = self._get_generic_line_id(
                    None, None, markup='plus_unreconciled_statement_lines'
                )
                plus_total += residual_amount
                plus_report_lines.append(st_report_line)
            else:
                st_report_line['parent_id'] = self._get_generic_line_id(
                    None, None, markup='less_unreconciled_statement_lines'
                )
                less_total += residual_amount
                less_report_lines.append(st_report_line)
            st_report_line['id'] = self._get_generic_line_id(
                'account.bank.statement.line', res['id'],
                parent_line_id=st_report_line['parent_id']
            )

            is_parent_unfolded = unfold_all or st_report_line['parent_id'] in options['unfolded_lines']
            if not is_parent_unfolded:
                st_report_line['style'] = 'display: none;'

        return (
            self._build_section_report_lines(options, journal, plus_report_lines, plus_total,
                _("Including Unreconciled Bank Statement Receipts"),
                _("%s for Transactions(+) imported from your online bank account (dated today) that "
                  "are not yet reconciled in Odoo (Waiting the final reconciliation allowing finding the right "
                  "account)") % journal.suspense_account_id.display_name,
            ),
            self._build_section_report_lines(options, journal, less_report_lines, less_total,
                _("Including Unreconciled Bank Statement Payments"),
                _("%s for Transactions(-) imported from your online bank account (dated today) that "
                  "are not yet reconciled in Odoo (Waiting the final reconciliation allowing finding the right "
                  "account)") % journal.suspense_account_id.display_name,
            ),
        )

    @api.model
    def _get_payment_report_lines(self, options, journal):
        ''' Retrieve the journal items used by the payment lines that are not yet reconciled and then, need to be
        displayed inside the report.
        :param options: The report options.
        :param journal: The journal as an account.journal record.
        :return:        The report lines for sections about statement lines.
        '''
        company_currency = journal.company_id.currency_id
        journal_currency = journal.currency_id if journal.currency_id and journal.currency_id != company_currency else False
        report_currency = journal_currency or company_currency
        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])

        accounts = journal._get_journal_inbound_outstanding_payment_accounts() \
                   + journal._get_journal_outbound_outstanding_payment_accounts()
        if not accounts:
            return [], []

        # Allow user managing payments without any statement lines.
        # In that case, the user manages transactions only using the register payment wizard.
        if journal.default_account_id in accounts:
            return [], []

        current_date = fields.Date.from_string(options['date']['date_to'])
        if current_date < fields.Date.context_today(self):
            # If the user selected a date in the past, filter payments as well.
            new_options = options
        else:
            # Include payments made in the future.
            new_options = {**options, 'date': None}

        tables, where_clause, where_params = self.with_company(journal.company_id)._query_get(new_options, domain=[
            ('journal_id', '=', journal.id),
            ('account_id', 'in', accounts.ids),
            ('full_reconcile_id', '=', False),
            ('amount_residual_currency', '!=', 0.0)
        ])

        self._cr.execute('''
            SELECT
                account_move_line.account_id,
                account_move_line.payment_id,
                account_move_line__move_id.id as move_id,
                account_move_line.currency_id,
                account_move_line__move_id.name,
                account_move_line__move_id.ref,
                account_move_line__move_id.date,
                account.reconcile AS is_account_reconcile,
                SUM(account_move_line.amount_residual) AS amount_residual,
                SUM(account_move_line.balance) AS balance,
                SUM(account_move_line.amount_residual_currency) AS amount_residual_currency,
                SUM(account_move_line.amount_currency) AS amount_currency
            FROM ''' + tables + '''
            JOIN account_account account ON account.id = account_move_line.account_id
            WHERE ''' + where_clause + '''
            GROUP BY
                account_move_line.account_id,
                account_move_line.payment_id,
                account_move_line__move_id.id,
                account_move_line.currency_id,
                account_move_line__move_id.name,
                account_move_line__move_id.ref,
                account_move_line__move_id.date,
                account.reconcile
            ORDER BY account_move_line__move_id.date DESC, account_move_line.payment_id DESC
        ''', where_params)

        plus_report_lines = []
        less_report_lines = []
        plus_total = 0.0
        less_total = 0.0

        for res in self._cr.dictfetchall():
            amount_currency = res['amount_residual_currency'] if res['is_account_reconcile'] else res['amount_currency']
            balance = res['amount_residual'] if res['is_account_reconcile'] else res['balance']

            if res['currency_id'] and journal_currency and res['currency_id'] == journal_currency.id:
                # Foreign currency, same as the journal one.

                if journal_currency.is_zero(amount_currency):
                    continue

                monetary_columns = [
                    {'name': ''},
                    {'name': ''},
                    {
                        'name': self.format_value(amount_currency, journal_currency),
                        'no_format': amount_currency,
                    },
                ]

            elif res['currency_id']:
                # Payment using a foreign currency that needs to be converted to the report's currency.

                foreign_currency = self.env['res.currency'].browse(res['currency_id'])
                journal_balance = company_currency._convert(balance, report_currency, journal.company_id, options['date']['date_to'])

                if foreign_currency.is_zero(amount_currency) and company_currency.is_zero(balance):
                    continue

                monetary_columns = [
                    {
                        'name': self.format_value(amount_currency, foreign_currency),
                        'no_format': amount_currency,
                    },
                    {'name': foreign_currency.name},
                    {
                        'name': self.format_value(journal_balance, report_currency),
                        'no_format': journal_balance,
                    },
                ]

            elif not res['currency_id'] and journal_currency:
                # Single currency in the payment but a foreign currency on the journal.

                journal_balance = company_currency._convert(balance, journal_currency, journal.company_id, options['date']['date_to'])

                if company_currency.is_zero(balance):
                    continue

                monetary_columns = [
                    {
                        'name': self.format_value(balance, company_currency),
                        'no_format': balance,
                    },
                    {'name': company_currency.name},
                    {
                        'name': self.format_value(journal_balance, journal_currency),
                        'no_format': journal_balance,
                    },
                ]

            else:
                # Single currency.

                if company_currency.is_zero(balance):
                    continue

                monetary_columns = [
                    {'name': ''},
                    {'name': ''},
                    {
                        'name': self.format_value(balance, journal_currency),
                        'no_format': balance,
                    },
                ]

            model = 'account.payment' if res['payment_id'] else 'account.move'
            pay_report_line = {
                'name': res['name'],
                'columns': self._apply_groups([
                    {'name': format_date(self.env, res['date']), 'class': 'date'},
                    {'name': res['ref']},
                ] + monetary_columns),
                'model': model,
                'caret_options': model,
                'level': 3,
            }

            residual_amount = monetary_columns[2]['no_format']
            if res['account_id'] in journal._get_journal_inbound_outstanding_payment_accounts().ids:
                pay_report_line['parent_id'] = self._get_generic_line_id(
                    None, None, markup='plus_unreconciled_payment_lines'
                )
                plus_total += residual_amount
                plus_report_lines.append(pay_report_line)
            else:
                pay_report_line['parent_id'] = self._get_generic_line_id(
                    None, None, markup='less_unreconciled_payment_lines'
                )
                less_total += residual_amount
                less_report_lines.append(pay_report_line)
            pay_report_line['id'] = self._get_generic_line_id(
                model, res['payment_id'] or res['move_id'],
                parent_line_id=pay_report_line['parent_id']
            )

            is_parent_unfolded = unfold_all or pay_report_line['parent_id'] in options['unfolded_lines']
            if not is_parent_unfolded:
                pay_report_line['style'] = 'display: none;'

        return (
            self._build_section_report_lines(options, journal, plus_report_lines, plus_total,
                _("(+) Outstanding Receipts"),
                _("Transactions(+) that were entered into Odoo, but not yet reconciled (Payments triggered by "
                  "invoices/refunds or manually)"),
            ),
            self._build_section_report_lines(options, journal, less_report_lines, less_total,
                _("(-) Outstanding Payments"),
                _("Transactions(-) that were entered into Odoo, but not yet reconciled (Payments triggered by "
                  "bills/credit notes or manually)"),
            ),
        )

    @api.model
    def _get_lines(self, options, line_id=None):
        print_mode = self._context.get('print_mode')
        journal_id = self._context.get('active_id') or options.get('active_id')
        journal = self.env['account.journal'].browse(journal_id)

        if not journal:
            return []

        # Make sure to keep the 'active_id' inside the options to don't depend of the context when printing the report.
        options['active_id'] = journal_id

        company_currency = journal.company_id.currency_id
        journal_currency = journal.currency_id if journal.currency_id and journal.currency_id != company_currency else False
        report_currency = journal_currency or company_currency

        last_statement_domain = [('date', '<=', options['date']['date_to'])]
        if not options['all_entries']:
            last_statement_domain.append(('move_id.state', '=', 'posted'))
        last_statement = journal._get_last_bank_statement(domain=last_statement_domain)

        # === Warnings ====

        # Unconsistent statements.
        options['unconsistent_statement_ids'] = self._get_unconsistent_statements(options, journal).ids

        # Strange miscellaneous journal items affecting the bank accounts.
        domain = self._get_bank_miscellaneous_move_lines_domain(options, journal)
        if domain:
            options['has_bank_miscellaneous_move_lines'] = bool(self.env['account.move.line'].search_count(domain))
        else:
            options['has_bank_miscellaneous_move_lines'] = False
        options['account_names'] = journal.default_account_id.display_name

        # ==== Build sub-sections about journal items ====

        plus_st_lines, less_st_lines = self._get_statement_report_lines(options, journal)
        plus_pay_lines, less_pay_lines = self._get_payment_report_lines(options, journal)

        # ==== Build section block about statement lines ====

        domain = self._get_options_domain(options)
        balance_gl = journal._get_journal_bank_account_balance(domain=domain)[0]

        # Compute the 'Reference' cell.
        if last_statement and not print_mode:
            reference_cell = {
                'last_statement_name': last_statement.display_name,
                'last_statement_id': last_statement.id,
                'template': 'account_reports.bank_reconciliation_report_cell_template_link_last_statement',
            }
        else:
            reference_cell = {'name': ''}

        # Compute the 'Amount' cell.
        balance_cell = {
            'name': self.format_value(balance_gl, report_currency),
            'no_format': balance_gl,
        }
        if last_statement:
            report_date = fields.Date.from_string(options['date']['date_to'])
            lines_before_date_to = last_statement.line_ids.filtered(lambda line: line.date <= report_date)
            balance_end = last_statement.balance_start + sum(lines_before_date_to.mapped('amount'))
            difference = balance_gl - balance_end

            if not report_currency.is_zero(difference):
                balance_cell.update({
                    'template': 'account_reports.bank_reconciliation_report_cell_template_unexplained_difference',
                    'style': 'color:orange;',
                    'title': _("The current balance in the General Ledger %s doesn't match the balance of your last "
                               "bank statement %s leading to an unexplained difference of %s.") % (
                        balance_cell['name'],
                        self.format_value(balance_end, report_currency),
                        self.format_value(difference, report_currency),
                    ),
                })

        balance_gl_report_line = {
            'id': 'balance_gl_line',
            'name': _("Balance of %s", options['account_names']),
            'title_hover': _("The Book balance in Odoo dated today"),
            'columns': self._apply_groups([
                {'name': format_date(self.env, options['date']['date_to']), 'class': 'date'},
                reference_cell,
                {'name': ''},
                {'name': ''},
                balance_cell,
            ]),
            'class': 'o_account_reports_totals_below_sections' if self.env.company.totals_below_sections else '',
            'level': 0,
            'unfolded': True,
            'unfoldable': False,
        }

        section_st_report_lines = [balance_gl_report_line] + plus_st_lines + less_st_lines

        if self.env.company.totals_below_sections:
            section_st_report_lines.append({
                'id': '%s_total' % balance_gl_report_line,
                'name': _("Total %s", balance_gl_report_line['name']),
                'columns': balance_gl_report_line['columns'],
                'class': 'total',
                'level': balance_gl_report_line['level'] + 1,
            })

        # ==== Build section block about payments ====

        section_pay_report_lines = []

        if plus_pay_lines or less_pay_lines:

            # Compute total to display for this section.
            total = 0.0
            if plus_pay_lines:
                total += plus_pay_lines[0]['columns'][-1]['no_format']
            if less_pay_lines:
                total += less_pay_lines[0]['columns'][-1]['no_format']

            outstanding_payments_report_line = {
                'id': 'outstanding_payments',
                'name': _("Outstanding Payments/Receipts"),
                'title_hover': _("Transactions that were entered into Odoo, but not yet reconciled (Payments triggered by invoices/bills or manually)"),
                'columns': self._apply_groups([
                    {'name': ''},
                    {'name': ''},
                    {'name': ''},
                    {'name': ''},
                    {
                        'name': self.format_value(total, report_currency),
                        'no_format': total,
                    },
                ]),
                'class': 'o_account_reports_totals_below_sections' if self.env.company.totals_below_sections else '',
                'level': 0,
                'unfolded': True,
                'unfoldable': False,
            }
            section_pay_report_lines += [outstanding_payments_report_line] + plus_pay_lines + less_pay_lines

            if self.env.company.totals_below_sections:
                section_pay_report_lines.append({
                    'id': '%s_total' % outstanding_payments_report_line['id'],
                    'name': _("Total %s", outstanding_payments_report_line['name']),
                    'columns': outstanding_payments_report_line['columns'],
                    'class': 'total',
                    'level': outstanding_payments_report_line['level'] + 1,
                })

        # ==== Build trailing section block ====

        return section_st_report_lines + section_pay_report_lines

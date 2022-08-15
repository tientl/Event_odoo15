# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _, _lt, fields
from odoo.tools.misc import format_date
from datetime import timedelta

from collections import defaultdict

class ReportPartnerLedger(models.AbstractModel):
    _inherit = "account.report"
    _name = "account.partner.ledger"
    _description = "Partner Ledger"

    filter_date = {'mode': 'range', 'filter': 'this_year'}
    filter_all_entries = False
    filter_unfold_all = False
    filter_account_type = [
        {'id': 'receivable', 'name': _lt('Receivable'), 'selected': False},
        {'id': 'payable', 'name': _lt('Payable'), 'selected': False},
    ]
    filter_unreconciled = False
    filter_partner = True

    @api.model
    def _get_templates(self):
        templates = super(ReportPartnerLedger, self)._get_templates()
        templates['line_template'] = 'account_reports.line_template_partner_ledger_report'
        templates['main_template'] = 'account_reports.main_template_with_filter_input_partner'
        return templates

    ####################################################
    # OPTIONS
    ####################################################

    @api.model
    def _get_filter_partners_domain(self, options):
        if options.get('filter_accounts'):
            return [('partner_id', 'ilike', options['filter_accounts'])]

        return []

    @api.model
    def _get_options_account_type(self, options):
        ''' Get select account type in the filter widget (see filter_account_type).
        :param options: The report options.
        :return:        Selected account types.
        '''
        all_account_types = []
        account_types = []
        for account_type_option in options.get('account_type', []):
            if account_type_option['selected']:
                account_types.append(account_type_option)
            all_account_types.append(account_type_option)
        return account_types or all_account_types

    @api.model
    def _get_options_domain(self, options):
        # OVERRIDE
        # Handle filter_unreconciled + filter_account_type
        domain = super(ReportPartnerLedger, self)._get_options_domain(options)

        domain += self._get_filter_partners_domain(options)

        if options.get('unreconciled'):
            domain += ['&', ('full_reconcile_id', '=', False), ('balance', '!=', '0')]
        exch_code = self.env['res.company'].browse(self.env.context.get('company_ids')).mapped('currency_exchange_journal_id')
        if exch_code:
            domain += ['!', '&', '&', '&', ('credit', '=', 0.0), ('debit', '=', 0.0), ('amount_currency', '!=', 0.0), ('journal_id.id', 'in', exch_code.ids)]
        domain.append(('account_id.internal_type', 'in', [t['id'] for t in self._get_options_account_type(options)]))

        return domain

    @api.model
    def _get_options_sum_balance(self, options):
        ''' Create options with the 'strict_range' enabled on the filter_date.
        The resulting dates domain will be:
        [
            ('date' <= options['date_to']),
            ('date' >= options['date_from'])
        ]
        :param options: The report options.
        :return:        A copy of the options.
        '''
        new_options = options.copy()
        new_options['date'] = new_options['date'].copy()
        new_options['date']['strict_range'] = True
        return new_options

    @api.model
    def _get_options_initial_balance(self, options):
        ''' Create options used to compute the initial balances for each partner.
        The resulting dates domain will be:
        [('date' <= options['date_from'] - 1)]
        :param options: The report options.
        :return:        A copy of the options.
        '''
        new_options = options.copy()
        new_options['date'] = new_options['date'].copy()
        new_date_to = fields.Date.from_string(new_options['date']['date_from']) - timedelta(days=1)
        new_options['date'].update({
            'date_from': False,
            'date_to': fields.Date.to_string(new_date_to),
        })
        return new_options

    @api.model
    def _get_options_without_partner(self, options):
        ''' Create options used to compute the special case of lines without partner reconcile
        with another line having a partner for each partner.
        :param options: The report options.
        :return:        A copy of the options.
        '''
        new_options = options.copy()
        new_options['date'] = new_options['date'].copy()
        new_options['date'].update({
            'date_from': False,
        })
        return new_options

    ####################################################
    # QUERIES
    ####################################################

    @api.model
    def _get_query_sums(self, options, expanded_partner=None):
        ''' Construct a query retrieving all the aggregated sums to build the report. It includes:
        - sums for all partners.
        - sums for the initial balances.
        :param options:             The report options.
        :param expanded_partner:    An optional res.partner record that must be specified when expanding a line
                                    with of without the load more.
        :return:                    (query, params)
        '''
        params = []
        queries = []

        if expanded_partner is not None:
            domain = [('partner_id', '=', expanded_partner.id)]
        else:
            domain = []

        # Create the currency table.
        ct_query = self.env['res.currency']._get_query_currency_table(options)

        # Get sums for all partners.
        # period: [('date' <= options['date_to']), ('date' >= options['date_from'])]
        new_options = self._get_options_sum_balance(options)
        tables, where_clause, where_params = self._query_get(new_options, domain=domain)
        params += where_params
        queries.append('''
            SELECT
                account_move_line.partner_id        AS groupby,
                'sum'                               AS key,
                SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
            FROM %s
            LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
            WHERE %s
            GROUP BY account_move_line.partner_id
        ''' % (tables, ct_query, where_clause))

        # Get sums for the initial balance.
        # period: [('date' <= options['date_from'] - 1)]
        new_options = self._get_options_initial_balance(options)
        tables, where_clause, where_params = self._query_get(new_options, domain=domain)
        params += where_params
        queries.append('''
            SELECT
                account_move_line.partner_id        AS groupby,
                'initial_balance'                   AS key,
                SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
            FROM %s
            LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
            WHERE %s
            GROUP BY account_move_line.partner_id
        ''' % (tables, ct_query, where_clause))

        return ' UNION ALL '.join(queries), params

    @api.model
    def _get_lines_without_partner(self, options, expanded_partner=None, offset=0, limit=0):
        ''' Get the detail of lines without partner reconciled with a line with a partner. Those lines should be
        considered as belonging the partner for the reconciled amount as it may clear some of the partner invoice/bill
        and they have to be accounted in the partner balance.'''

        params = []
        if expanded_partner:
            partner_clause = '= %s'
            params = [expanded_partner.id] + params
        else:
            partner_clause = 'IS NOT NULL'
        new_options = self._get_options_without_partner(options)
        params += [options['date']['date_from'], options['date']['date_to']]
        tables, where_clause, where_params = self._query_get(new_options, domain=[])
        params += where_params + [offset]
        limit_clause = ''
        if limit != 0:
            params += [limit]
            limit_clause = "LIMIT %s"
        query = '''
            SELECT
                account_move_line.id,
                account_move_line.date,
                account_move_line.date_maturity,
                account_move_line.name,
                account_move_line.ref,
                account_move_line.company_id,
                account_move_line.account_id,
                account_move_line.payment_id,
                aml_with_partner.partner_id,
                account_move_line.currency_id,
                account_move_line.amount_currency,
                account_move_line.matching_number,
                CASE WHEN aml_with_partner.balance > 0 THEN 0 ELSE partial.amount END AS debit,
                CASE WHEN aml_with_partner.balance < 0 THEN 0 ELSE partial.amount END AS credit,
                CASE WHEN aml_with_partner.balance > 0 THEN -partial.amount ELSE partial.amount END AS balance,
                account_move_line__move_id.name         AS move_name,
                account_move_line__move_id.move_type    AS move_type,
                account.code                            AS account_code,
                account.name                            AS account_name,
                journal.code                            AS journal_code,
                journal.name                            AS journal_name,
                full_rec.name                           AS full_rec_name
            FROM {tables},
                account_partial_reconcile partial
                LEFT JOIN account_full_reconcile full_rec ON full_rec.id = partial.full_reconcile_id,
                account_move_line aml_with_partner,
                account_journal journal,
                account_account account
            WHERE (account_move_line.id = partial.debit_move_id OR account_move_line.id = partial.credit_move_id)
               AND account_move_line.partner_id IS NULL
               AND (aml_with_partner.id = partial.debit_move_id OR aml_with_partner.id = partial.credit_move_id)
               AND aml_with_partner.partner_id {partner_clause}
               AND journal.id = account_move_line.journal_id
               AND account.id = account_move_line.account_id
               AND partial.max_date BETWEEN %s AND %s
               AND {where_clause}
            ORDER BY account_move_line.date, account_move_line.id
            OFFSET %s
            {limit_clause}
        '''.format(tables=tables, partner_clause=partner_clause, where_clause=where_clause, limit_clause=limit_clause)

        return query, params

    @api.model
    def _get_sums_without_partner(self, options, expanded_partner=None):
        ''' Get the sum of lines without partner reconciled with a line with a partner, grouped by partner. Those lines
        should be considered as belonging the partner for the reconciled amount as it may clear some of the partner
        invoice/bill and they have to be accounted in the partner balance.'''

        params = []
        if expanded_partner:
            partner_clause = '= %s'
            params = [expanded_partner.id]
        else:
            partner_clause = 'IS NOT NULL'

        new_options = self._get_options_without_partner(options)
        params = [options['date']['date_from']] + params + [options['date']['date_to']]
        tables, where_clause, where_params = self._query_get(new_options, domain=[])
        params += where_params

        query = '''
            SELECT
                aml_with_partner.partner_id AS groupby,
                SUM(CASE WHEN aml_with_partner.balance > 0 THEN 0 ELSE partial.amount END) AS debit,
                SUM(CASE WHEN aml_with_partner.balance < 0 THEN 0 ELSE partial.amount END) AS credit,
                SUM(CASE WHEN aml_with_partner.balance > 0 THEN -partial.amount ELSE partial.amount END) AS balance,
                CASE WHEN partial.max_date < %s THEN 'initial_balance' ELSE 'sum' END as key
            FROM {tables}, account_partial_reconcile partial, account_move_line aml_with_partner
            WHERE (account_move_line.id = partial.debit_move_id OR account_move_line.id = partial.credit_move_id)
               AND account_move_line.partner_id IS NULL
               AND (aml_with_partner.id = partial.debit_move_id OR aml_with_partner.id = partial.credit_move_id)
               AND aml_with_partner.partner_id {partner_clause}
               AND partial.max_date <= %s
               AND {where_clause}
            GROUP BY aml_with_partner.partner_id, key
        '''.format(tables=tables, partner_clause=partner_clause, where_clause=where_clause)
        return query, params

    @api.model
    def _get_query_amls(self, options, expanded_partner=None, offset=None, limit=None):
        ''' Construct a query retrieving the account.move.lines when expanding a report line with or without the load
        more.
        :param options:             The report options.
        :param expanded_partner:    The res.partner record corresponding to the expanded line.
        :param offset:              The offset of the query (used by the load more).
        :param limit:               The limit of the query (used by the load more).
        :return:                    (query, params)
        '''
        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])

        # Get sums for the account move lines.
        # period: [('date' <= options['date_to']), ('date', '>=', options['date_from'])]
        if expanded_partner is not None:
            domain = [('partner_id', '=', expanded_partner.id)]
        elif unfold_all:
            domain = []
        elif options['unfolded_lines']:
            domain = [('partner_id', 'in', [int(line[8:]) for line in options['unfolded_lines']])]

        new_options = self._get_options_sum_balance(options)
        tables, where_clause, where_params = self._query_get(new_options, domain=domain)
        ct_query = self.env['res.currency']._get_query_currency_table(options)

        query = '''
            SELECT
                account_move_line.id,
                account_move_line.date,
                account_move_line.date_maturity,
                account_move_line.name,
                account_move_line.ref,
                account_move_line.company_id,
                account_move_line.account_id,
                account_move_line.payment_id,
                account_move_line.partner_id,
                account_move_line.currency_id,
                account_move_line.amount_currency,
                account_move_line.matching_number,
                ROUND(account_move_line.debit * currency_table.rate, currency_table.precision)   AS debit,
                ROUND(account_move_line.credit * currency_table.rate, currency_table.precision)  AS credit,
                ROUND(account_move_line.balance * currency_table.rate, currency_table.precision) AS balance,
                account_move_line__move_id.name         AS move_name,
                company.currency_id                     AS company_currency_id,
                partner.name                            AS partner_name,
                account_move_line__move_id.move_type    AS move_type,
                account.code                            AS account_code,
                account.name                            AS account_name,
                journal.code                            AS journal_code,
                journal.name                            AS journal_name
            FROM %s
            LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
            LEFT JOIN res_company company               ON company.id = account_move_line.company_id
            LEFT JOIN res_partner partner               ON partner.id = account_move_line.partner_id
            LEFT JOIN account_account account           ON account.id = account_move_line.account_id
            LEFT JOIN account_journal journal           ON journal.id = account_move_line.journal_id
            WHERE %s
            ORDER BY account_move_line.date, account_move_line.id
        ''' % (tables, ct_query, where_clause)

        if offset:
            query += ' OFFSET %s '
            where_params.append(offset)
        if limit:
            query += ' LIMIT %s '
            where_params.append(limit)

        return query, where_params

    @api.model
    def _do_query(self, options, expanded_partner=None):
        ''' Execute the queries, perform all the computation and return partners_results,
        a lists of tuple (partner, fetched_values) sorted by the table's model _order:
            - partner is a res.parter record.
            - fetched_values is a dictionary containing:
                - sum:                              {'debit': float, 'credit': float, 'balance': float}
                - (optional) initial_balance:       {'debit': float, 'credit': float, 'balance': float}
                - (optional) lines:                 [line_vals_1, line_vals_2, ...]
        :param options:             The report options.
        :param expanded_account:    An optional account.account record that must be specified when expanding a line
                                    with of without the load more.
        :param fetch_lines:         A flag to fetch the account.move.lines or not (the 'lines' key in accounts_values).
        :return:                    (accounts_values, taxes_results)
        '''
        def assign_sum(row):
            key = row['key']
            fields = ['balance', 'debit', 'credit'] if key == 'sum' else ['balance']
            if any(not company_currency.is_zero(row[field]) for field in fields):
                groupby_partners.setdefault(row['groupby'], defaultdict(lambda: defaultdict(float)))
                for field in fields:
                    groupby_partners[row['groupby']][key][field] += row[field]

        company_currency = self.env.company.currency_id

        # flush the tables that gonna be queried
        self.env['account.move.line'].flush(fnames=self.env['account.move.line']._fields)
        self.env['account.move'].flush(fnames=self.env['account.move']._fields)
        self.env['account.partial.reconcile'].flush(fnames=self.env['account.partial.reconcile']._fields)

        # Execute the queries and dispatch the results.
        query, params = self._get_query_sums(options, expanded_partner=expanded_partner)

        groupby_partners = {}

        self._cr.execute(query, params)
        for res in self._cr.dictfetchall():
            assign_sum(res)

        # Fetch the lines of unfolded accounts.
        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])
        if expanded_partner or unfold_all or options['unfolded_lines']:
            query, params = self._get_query_amls(options, expanded_partner=expanded_partner)
            self._cr.execute(query, params)
            for res in self._cr.dictfetchall():
                if res['partner_id'] not in groupby_partners:
                    continue
                groupby_partners[res['partner_id']].setdefault('lines', [])
                groupby_partners[res['partner_id']]['lines'].append(res)

            query, params = self._get_lines_without_partner(options, expanded_partner=expanded_partner)
            self._cr.execute(query, params)
            for row in self._cr.dictfetchall():
                # don't show lines of partners not expanded
                if row['partner_id'] in groupby_partners:
                    groupby_partners[row['partner_id']].setdefault('lines', [])
                    row['class'] = ' text-muted'
                    groupby_partners[row['partner_id']]['lines'].append(row)
                if None in groupby_partners:
                    # reconciled lines without partners are fetched to be displayed under the matched partner
                    # and thus but be inversed to be displayed under the unknown partner
                    none_row = row.copy()
                    none_row['class'] = ' text-muted'
                    none_row['debit'] = row['credit']
                    none_row['credit'] = row['debit']
                    none_row['balance'] = -row['balance']
                    groupby_partners[None].setdefault('lines', [])
                    groupby_partners[None]['lines'].append(none_row)

        # correct the sums per partner, for the lines without partner reconciled with a line having a partner
        query, params = self._get_sums_without_partner(options, expanded_partner=expanded_partner)
        self._cr.execute(query, params)
        total = total_debit = total_credit = total_initial_balance = 0
        for row in self._cr.dictfetchall():
            key = row['key']
            total_debit += key == 'sum' and row['debit'] or 0
            total_credit += key == 'sum' and row['credit'] or 0
            total_initial_balance += key == 'initial_balance' and row['balance'] or 0
            total += key == 'sum' and row['balance'] or 0
            if None not in groupby_partners and not (expanded_partner or unfold_all or options['unfolded_lines']):
                groupby_partners.setdefault(None, {})
            if row['groupby'] not in groupby_partners:
                continue
            assign_sum(row)

        if None in groupby_partners:
            if 'sum' not in groupby_partners[None]:
                groupby_partners[None].setdefault('sum', {'debit': 0, 'credit': 0, 'balance': 0})
            if 'initial_balance' not in groupby_partners[None]:
                groupby_partners[None].setdefault('initial_balance', {'balance': 0})
            #debit/credit are inversed for the unknown partner as the computation is made regarding the balance of the known partner
            groupby_partners[None]['sum']['debit'] += total_credit
            groupby_partners[None]['sum']['credit'] += total_debit
            groupby_partners[None]['sum']['balance'] -= total
            groupby_partners[None]['initial_balance']['balance'] -= total_initial_balance

        # Retrieve the partners to browse.
        # groupby_partners.keys() contains all account ids affected by:
        # - the amls in the current period.
        # - the amls affecting the initial balance.
        # Note a search is done instead of a browse to preserve the table ordering.
        if expanded_partner:
            partners = expanded_partner
        elif groupby_partners:
            partners = self.env['res.partner'].with_context(active_test=False).search([('id', 'in', list(groupby_partners.keys()))])
        else:
            partners = []

        # Add 'Partner Unknown' if needed
        if None in groupby_partners.keys():
            partners = [p for p in partners] + [None]
        return [(partner, groupby_partners[partner.id if partner else None]) for partner in partners]

    ####################################################
    # COLUMNS/LINES
    ####################################################

    @api.model
    def _get_report_line_partner(self, options, partner, initial_balance, debit, credit, balance):
        company_currency = self.env.company.currency_id
        unfold_all = self._context.get('print_mode') and not options.get('unfolded_lines')

        columns = [
            {'name': self.format_value(initial_balance), 'class': 'number'},
            {'name': self.format_value(debit), 'class': 'number'},
            {'name': self.format_value(credit), 'class': 'number'},
        ]
        if self.user_has_groups('base.group_multi_currency'):
            columns.append({'name': ''})
        columns.append({'name': self.format_value(balance), 'class': 'number'})

        return {
            'id': 'partner_%s' % (partner.id if partner else 0),
            'partner_id': partner.id if partner else None,
            'name': partner is not None and (partner.name or '')[:128] or _('Unknown Partner'),
            'columns': columns,
            'level': 2,
            'trust': partner.trust if partner else None,
            'unfoldable': not company_currency.is_zero(debit) or not company_currency.is_zero(credit),
            'unfolded': 'partner_%s' % (partner.id if partner else 0) in options['unfolded_lines'] or unfold_all,
            'colspan': 6,
        }

    @api.model
    def _get_report_line_move_line(self, options, partner, aml, cumulated_init_balance, cumulated_balance):
        if aml['payment_id']:
            caret_type = 'account.payment'
        else:
            caret_type = 'account.move'

        date_maturity = aml['date_maturity'] and format_date(self.env, fields.Date.from_string(aml['date_maturity']))
        columns = [
            {'name': aml['journal_code']},
            {'name': aml['account_code']},
            {'name': self._format_aml_name(aml['name'], aml['ref'], aml['move_name']), 'class': 'o_account_report_line_ellipsis'},
            {'name': date_maturity or '', 'class': 'date'},
            {'name': aml['matching_number'] or ''},
            {'name': self.format_value(cumulated_init_balance), 'class': 'number'},
            {'name': self.format_value(aml['debit'], blank_if_zero=True), 'class': 'number'},
            {'name': self.format_value(aml['credit'], blank_if_zero=True), 'class': 'number'},
        ]
        if self.user_has_groups('base.group_multi_currency'):
            if aml['currency_id']:
                currency = self.env['res.currency'].browse(aml['currency_id'])
                formatted_amount = self.format_value(aml['amount_currency'], currency=currency, blank_if_zero=True)
                columns.append({'name': formatted_amount, 'class': 'number'})
            else:
                columns.append({'name': ''})
        columns.append({'name': self.format_value(cumulated_balance), 'class': 'number'})
        return {
            'id': aml['id'],
            'parent_id': 'partner_%s' % (partner.id if partner else 0),
            'name': format_date(self.env, aml['date']),
            'class': 'text' + aml.get('class', ''),  # do not format as date to prevent text centering
            'columns': columns,
            'caret_options': caret_type,
            'level': 2,
        }

    @api.model
    def _get_report_line_load_more(self, options, partner, offset, remaining, progress):
        return {
            'id': 'loadmore_%s' % (partner.id if partner else 0),
            'offset': offset,
            'progress': progress,
            'remaining': remaining,
            'class': 'o_account_reports_load_more text-center',
            'parent_id': 'partner_%s' % (partner.id if partner else 0),
            'name': _('Load more... (%s remaining)', remaining),
            'colspan': 10 if self.user_has_groups('base.group_multi_currency') else 9,
            'columns': [{}],
        }

    @api.model
    def _get_report_line_total(self, options, initial_balance, debit, credit, balance):
        columns = [
            {'name': self.format_value(initial_balance), 'class': 'number'},
            {'name': self.format_value(debit), 'class': 'number'},
            {'name': self.format_value(credit), 'class': 'number'},
        ]
        if self.user_has_groups('base.group_multi_currency'):
            columns.append({'name': ''})
        columns.append({'name': self.format_value(balance), 'class': 'number'})
        return {
            'id': 'partner_ledger_total_%s' % self.env.company.id,
            'name': _('Total'),
            'class': 'total',
            'level': 1,
            'columns': columns,
            'colspan': 6,
        }

    @api.model
    def _get_partner_ledger_lines(self, options, line_id=None):
        ''' Get lines for the whole report or for a specific line.
        :param options: The report options.
        :return:        A list of lines, each one represented by a dictionary.
        '''
        lines = []
        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])

        expanded_partner = line_id and self.env['res.partner'].browse(int(line_id[8:]))
        partners_results = self._do_query(options, expanded_partner=expanded_partner)

        total_initial_balance = total_debit = total_credit = total_balance = 0.0
        for partner, results in partners_results:
            is_unfolded = 'partner_%s' % (partner.id if partner else 0) in options['unfolded_lines']

            # res.partner record line.
            partner_sum = results.get('sum', {})
            partner_init_bal = results.get('initial_balance', {})

            initial_balance = partner_init_bal.get('balance', 0.0)
            debit = partner_sum.get('debit', 0.0)
            credit = partner_sum.get('credit', 0.0)
            balance = initial_balance + partner_sum.get('balance', 0.0)

            lines.append(self._get_report_line_partner(options, partner, initial_balance, debit, credit, balance))

            total_initial_balance += initial_balance
            total_debit += debit
            total_credit += credit
            total_balance += balance

            if unfold_all or is_unfolded:
                cumulated_balance = initial_balance

                # account.move.line record lines.
                amls = results.get('lines', [])

                load_more_remaining = len(amls)
                load_more_counter = self._context.get('print_mode') and load_more_remaining or self.MAX_LINES

                for aml in amls:
                    # Don't show more line than load_more_counter.
                    if load_more_counter == 0:
                        break

                    cumulated_init_balance = cumulated_balance
                    cumulated_balance += aml['balance']
                    lines.append(self._get_report_line_move_line(options, partner, aml, cumulated_init_balance, cumulated_balance))

                    load_more_remaining -= 1
                    load_more_counter -= 1

                if load_more_remaining > 0:
                    # Load more line.
                    lines.append(self._get_report_line_load_more(
                        options,
                        partner,
                        self.MAX_LINES,
                        load_more_remaining,
                        cumulated_balance,
                    ))

        if not line_id:
            # Report total line.
            lines.append(self._get_report_line_total(
                options,
                total_initial_balance,
                total_debit,
                total_credit,
                total_balance
            ))
        return lines

    @api.model
    def _load_more_lines(self, options, line_id, offset, load_more_remaining, progress):
        ''' Get lines for an expanded line using the load more.
        :param options: The report options.
        :return:        A list of lines, each one represented by a dictionary.
        '''
        lines = []
        expanded_partner = line_id and self.env['res.partner'].browse(int(line_id[9:]))

        load_more_counter = self.MAX_LINES

        starting_offset = offset
        starting_load_more_counter = load_more_counter

        # Fetch the next batch of lines
        amls_query, amls_params = self._get_query_amls(options, expanded_partner=expanded_partner, offset=offset, limit=load_more_counter)
        self._cr.execute(amls_query, amls_params)
        for aml in self._cr.dictfetchall():
            # Don't show more line than load_more_counter.
            if load_more_counter == 0:
                break

            cumulated_init_balance = progress
            progress += aml['balance']

            # account.move.line record line.
            lines.append(self._get_report_line_move_line(options, expanded_partner, aml, cumulated_init_balance, progress))

            offset += 1
            load_more_remaining -= 1
            load_more_counter -= 1

        query, params = self._get_lines_without_partner(options, expanded_partner=expanded_partner, offset=offset-starting_offset, limit=starting_load_more_counter-load_more_counter)
        self._cr.execute(query, params)
        for row in self._cr.dictfetchall():
            # Don't show more line than load_more_counter.
            if load_more_counter == 0:
                break

            row['class'] = ' text-muted'
            if line_id == 'loadmore_0':
                # reconciled lines without partners are fetched to be displayed under the matched partner
                # and thus but be inversed to be displayed under the unknown partner
                row['debit'] = row['balance'] < 0 and row['credit'] or 0
                row['credit'] = row['balance'] > 0 and row['debit'] or 0
                row['balance'] = -row['balance']
            cumulated_init_balance = progress
            progress += row['balance']
            lines.append(self._get_report_line_move_line(options, expanded_partner, row, cumulated_init_balance, progress))

            offset += 1
            load_more_remaining -= 1
            load_more_counter -= 1

        if load_more_remaining > 0:
            # Load more line.
            lines.append(self._get_report_line_load_more(
                options,
                expanded_partner,
                offset,
                load_more_remaining,
                progress,
            ))
        return lines

    def _get_columns_name(self, options):
        columns = [
            {},
            {'name': _('JRNL')},
            {'name': _('Account')},
            {'name': _('Ref')},
            {'name': _('Due Date'), 'class': 'date'},
            {'name': _('Matching Number')},
            {'name': _('Initial Balance'), 'class': 'number'},
            {'name': _('Debit'), 'class': 'number'},
            {'name': _('Credit'), 'class': 'number'}]

        if self.user_has_groups('base.group_multi_currency'):
            columns.append({'name': _('Amount Currency'), 'class': 'number'})

        columns.append({'name': _('Balance'), 'class': 'number'})

        return columns

    @api.model
    def _get_lines(self, options, line_id=None):
        offset = int(options.get('lines_offset', 0))
        remaining = int(options.get('lines_remaining', 0))
        balance_progress = float(options.get('lines_progress', 0))

        if offset > 0:
            # Case a line is expanded using the load more.
            return self._load_more_lines(options, line_id, offset, remaining, balance_progress)
        else:
            # Case the whole report is loaded or a line is expanded for the first time.
            return self._get_partner_ledger_lines(options, line_id=line_id)

    @api.model
    def _get_report_name(self):
        return _('Partner Ledger')

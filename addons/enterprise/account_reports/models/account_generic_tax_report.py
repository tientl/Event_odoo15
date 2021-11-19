# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import ast
from collections import defaultdict
from datetime import datetime
import json
from math import copysign
import re

from odoo import models, api, fields, Command, _
from odoo.exceptions import UserError, RedirectWarning
from odoo.tools import safe_eval
from odoo.osv import expression


class AccountGenericTaxReport(models.AbstractModel):
    _inherit = 'account.report'
    _name = 'account.generic.tax.report'
    _description = 'Generic Tax Report'

    filter_multi_company = True # Actually disabled by default, can be activated by config parameter (see _get_options)
    filter_date = {'mode': 'range', 'filter': 'last_month'}
    filter_all_entries = False
    filter_comparison = {'date_from': '', 'date_to': '', 'filter': 'no_comparison', 'number_period': 1}
    filter_tax_report = None

    # -------------------------------------------------------------------------
    # OPTIONS
    # -------------------------------------------------------------------------

    def _init_filter_tax_report(self, options, previous_options=None):
        options['available_tax_reports'] = []
        available_reports = self.env.company.get_available_tax_reports()
        for report in available_reports:
            options['available_tax_reports'].append({
                'id': report.id,
                'name': "%s (%s)" % (report.name, report.country_id.code.upper()),
            })

        options['tax_report'] = (previous_options or {}).get('tax_report')

        if not self._is_generic_report(options) and options['tax_report'] not in available_reports.ids:
            # Replace the report in options by the default report if it is not the generic report
            # (always available for all companies) and the report in options is not available for this company
            options['tax_report'] = available_reports and available_reports[0].id or 'generic'

    def _init_filter_fiscal_position(self, options, previous_options=None):
        # Depends from the tax_report and tax_unit options
        if self._is_generic_report(options) or options['tax_unit'] != 'company_only':
            # The generic report never shows the fiscal position filter; always displays everything
            # Also, when displaying a tax unit, we always disable fiscal position filter and show everything
            if not previous_options:
                previous_options = {}
            previous_options['fiscal_position'] = 'all'

        super()._init_filter_fiscal_position(options, previous_options)

    def _init_filter_multi_company(self, options, previous_options=None):
        tax_units_domain = [('company_ids', 'in', self.env.company.id)]

        if not self._is_generic_report(options):
            report_country_code = self._get_report_country_code(options)
            tax_units_domain.append(('country_id.code', '=', report_country_code))

        available_tax_units = self.env['account.tax.unit'].search(tax_units_domain)

        # Filter available units to only consider the ones whose companies are all accessible to the user
        available_tax_units = available_tax_units.filtered(
            lambda x: all(unit_company in self.env.user.company_ids for unit_company in x.sudo().company_ids)
            # sudo() to avoid bypassing companies the current user does not have access to
        )

        options['available_tax_units'] = [{
            'id': tax_unit.id,
            'name': tax_unit.name,
            'company_ids': tax_unit.company_ids.ids
        } for tax_unit in available_tax_units]

        # Available tax_unit option values that are currently allowed by the company selector
        # A js hack ensures the page is reloaded and the selected companies modified
        # when clicking on a tax unit option in the UI, so we don't need to worry about that here.
        companies_authorized_tax_unit_opt = {
            *(available_tax_units.filtered(lambda x: set(self.env.companies) == set(x.company_ids)).ids),
            'company_only'
        }

        if previous_options and previous_options.get('tax_unit') in companies_authorized_tax_unit_opt:
            options['tax_unit'] = previous_options['tax_unit']

        else:
            # No tax_unit gotten from previous options; initialize it
            # A tax_unit will be set by default if only one tax unit is available for the report
            # (which should always be true for non-generic reports, whih have a country), and the companies of
            # the unit are the only ones currently selected.
            if companies_authorized_tax_unit_opt == {'company_only'}:
                options['tax_unit'] = 'company_only'
            elif len(available_tax_units) == 1 and available_tax_units[0].id in companies_authorized_tax_unit_opt:
                options['tax_unit'] = available_tax_units[0].id
            else:
                options['tax_unit'] = 'company_only'

        # Finally initialize multi_company filter
        if options['tax_unit'] != 'company_only':
            tax_unit = available_tax_units.filtered(lambda x: x.id == options['tax_unit'])
            options['multi_company'] = [{'name': company.name, 'id': company.id} for company in tax_unit.company_ids]

    def _init_filter_date(self, options, previous_options=None):
        # OVERRIDE
        super()._init_filter_date(options, previous_options=previous_options)
        options['date']['strict_range'] = True

    @api.model
    def _is_generic_report(self, options):
        return isinstance(options['tax_report'], str) and options['tax_report'].startswith('generic')

    @api.model
    def _is_grouped_report(self, options):
        return isinstance(options['tax_report'], str) and options['tax_report'].startswith('generic_grouped')

    @api.model
    def _get_options_domain(self, options):
        # Overridden to always filter on tax exigibility
        rslt = super()._get_options_domain(options)
        return rslt + self.env['account.move.line']._get_tax_exigible_domain()

    def _get_country_for_fiscal_position_filter(self, options):
        if self._is_generic_report(options):
            return None

        tax_report_id = int(options['tax_report'])
        return self.env['account.tax.report'].browse(tax_report_id).country_id

    def _get_forced_filter_init_sequence_map(self):
        rslt = super()._get_forced_filter_init_sequence_map()

        rslt['filter_tax_report'] = rslt['filter_multi_company'] - 1

        return rslt

    @api.model
    def get_vat_for_export(self, options):
        if options['tax_unit'] != 'company_only':
            tax_unit = self.env['account.tax.unit'].browse(options['tax_unit'])
            return tax_unit.vat

        return super().get_vat_for_export(options)

    @api.model
    def _get_sender_company_for_export(self, options):
        """ Return the sender company when generating an export file from this report.
            :return: self.env.company if not using a tax unit, else the main company of that unit
        """
        if options['tax_unit'] != 'company_only':
            tax_unit = self.env['account.tax.unit'].browse(options['tax_unit'])
            return tax_unit.main_company_id

        return self.env.company

    # -------------------------------------------------------------------------
    # DROPDOWN MENUS
    # -------------------------------------------------------------------------

    def _redirect_audit_default_tax_report(self, options, type_tax_use, tax_id):
        """ Create an action redirecting to a view of journal items having the right domain regarding the options
        passed as parameter and fitting the custom domain.

        :param options:         The report options.
        :param type_tax_use:    'sale' or 'purchase'.
        :param tax_id:          The id of an account.tax (optional).
        :param account_id:      The id of an account.account (optional).
        :return:                An action redirecting to the journal items.
        """
        tax = self.env['account.tax'].browse(tax_id or [])

        if tax.tax_exigibility == 'on_payment':
            # Cash basis taxes mixed with non-cash basis taxes on the same base
            # line are a trickier case: the line will be exigible because
            # of the non-cash basis tax, but we still don't want to show it when
            # auditing the cash basis tax.
            additional_base_line_domain = [
                '|', ('move_id.tax_cash_basis_rec_id', '!=', False),
                ('move_id.always_tax_exigible', '=', True),
            ]
        else:
            additional_base_line_domain = []

        domain = self._get_options_domain(options) + expression.OR((
            # Base lines
            [
                ('tax_ids', 'in', tax.ids),
                ('tax_ids.type_tax_use', '=', type_tax_use),
                ('tax_repartition_line_id', '=', False),
                *additional_base_line_domain,
            ],
            # Tax lines
            [
                ('group_tax_id', '=', tax.id) if tax.amount_type == 'group' else ('tax_line_id', '=', tax.id),
            ],
            # Tax lines acting as base lines
            [
                ('tax_ids', 'in', (tax.children_tax_ids if tax.amount_type == 'group' else tax).ids),
                ('tax_ids.type_tax_use', '=', type_tax_use),
                ('tax_repartition_line_id', '!=', False),
                *additional_base_line_domain,
            ],
        ))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Items for Tax Audit'),
            'res_model': 'account.move.line',
            'views': [[self.env.ref('account.view_move_line_tax_audit_tree').id, 'list'], [False, 'form']],
            'domain': domain,
            'context': dict(self._context, search_default_groupby_date=1),
        }

    def action_dropdown_audit_default_tax_report(self, options, data):
        args = ast.literal_eval(data['args'])
        return self._redirect_audit_default_tax_report(options, *args)

    # -------------------------------------------------------------------------
    # DEFAULT TAX REPORT
    # -------------------------------------------------------------------------

    @api.model
    def _read_default_tax_report_amounts(self, options_list, groupby_fields):
        """ Read the tax details to compute the tax amounts.

        :param options_list:    The list of report options, one for each period.
        :param groupby_fields:  A list of tuple (alias, field) representing the way the amounts must be grouped.
        :return:                A dictionary mapping each groupby key (e.g. a tax_id) to a sub dictionary containing:

            base_amount:    The tax base amount expressed in company's currency.
            tax_amount      The tax amount expressed in company's currency.
            children:       The children nodes following the same pattern as the current dictionary.
        """
        select_clause_str = ','.join('%s.%s AS %s_%s' % (alias, field, alias, field) for alias, field in groupby_fields)
        groupby_query_str = ','.join('%s.%s' % (alias, field) for alias, field in groupby_fields)

        res = {}
        for i, options in enumerate(options_list):
            tables, where_clause, where_params = self._query_get(options)
            tax_details_query, tax_details_params = self.env['account.move.line']._get_query_tax_details(tables, where_clause, where_params)

            # Avoid adding multiple times the same base amount sharing the same grouping_key.
            # It could happen when dealing with group of taxes for example.
            row_keys = set()

            self._cr.execute(f'''
                SELECT
                    {select_clause_str},
                    SUM(tdr.base_amount) AS base_amount,
                    SUM(tdr.tax_amount) AS tax_amount
                FROM ({tax_details_query}) AS tdr
                JOIN account_tax tax ON tax.id = tdr.tax_id
                JOIN account_tax src_tax ON
                    src_tax.id = COALESCE(tdr.group_tax_id, tdr.tax_id)
                    AND src_tax.type_tax_use IN ('sale', 'purchase')
                JOIN account_account account ON account.id = tdr.base_account_id
                WHERE tdr.tax_exigible
                GROUP BY tax.sequence, tax.id, {groupby_query_str}
                ORDER BY src_tax.sequence, src_tax.id, tax.sequence, tax.id
            ''', tax_details_params)

            for row in self._cr.dictfetchall():
                node = res

                cumulated_row_key = []
                for alias, field in groupby_fields:
                    grouping_key = '%s_%s' % (alias, field)
                    row_key = row[grouping_key]
                    cumulated_row_key.append(row_key)
                    cumulated_row_key_tuple = tuple(cumulated_row_key)

                    node.setdefault(row_key, {
                        'base_amount': [0.0] * len(options_list),
                        'tax_amount': [0.0] * len(options_list),
                        'children': {},
                    })
                    sub_node = node[row_key]

                    # Add amounts.
                    if cumulated_row_key_tuple not in row_keys:
                        sub_node['base_amount'][i] += row['base_amount']
                    sub_node['tax_amount'][i] += row['tax_amount']

                    node = sub_node['children']
                    row_keys.add(cumulated_row_key_tuple)

        return res

    @api.model
    def _default_tax_report_build_report_line(self, options, default_vals, groupby_key, value):
        """ Build the report line accordingly to its type.

        :param options:         The report options.
        :param default_vals:    The pre-computed report line values.
        :param groupby_key:     The grouping_key record.
        :param value:           The value that could be a record.
        :return:                A python dictionary.
        """
        report_line = dict(default_vals)

        if groupby_key == 'src_tax_type_tax_use':
            type_tax_use_option = value
            report_line['id'] = self._get_generic_line_id(None, None, markup=type_tax_use_option[0])
            report_line['name'] = type_tax_use_option[1]

        elif groupby_key == 'src_tax_id':
            tax = value
            report_line['id'] = self._get_generic_line_id(tax._name, tax.id)

            if tax.amount_type == 'percent':
                report_line['name'] = f"{tax.name} ({tax.amount}%)"
            elif tax.amount_type == 'fixed':
                report_line['name'] = f"{tax.name} ({tax.amount})"
            else:
                report_line['name'] = tax.name

            if options.get('multi-company'):
                report_line['name'] = f"{report_line['name']} - {tax.company_id.display_name}"

        elif groupby_key == 'account_id':
            account = value
            report_line['id'] = self._get_generic_line_id(account._name, account.id)

            if options.get('multi-company'):
                report_line['name'] = f"{account.display_name} - {account.company_id.display_name}"
            else:
                report_line['name'] = account.display_name

        return report_line

    @api.model
    def _default_tax_report_populate_lines_recursively(self, options, lines, sorting_map_list, groupby_fields, values_node, index=0, type_tax_use=None):
        ''' Populate the list of report lines passed as parameter recursively. At this point, every amounts is already
        fetched for every periods and every groupby.

        :param options:             The report options.
        :param lines:               The list of report lines to populate.
        :param sorting_map_list:    A list of dictionary mapping each encountered key with a weight to sort the results.
        :param index:               The index of the current element to process (also equals to the level into the hierarchy).
        :param groupby_fields:      A list of tuple <alias, field> defining in which way tax amounts should be grouped.
        :param values_node:         The node containing the amounts and children into the hierarchy.
        :param type_tax_use:        The type_tax_use of the tax.
        '''
        if index == len(groupby_fields):
            return

        alias, field = groupby_fields[index]
        groupby_key = '%s_%s' % (alias, field)

        # Sort the keys in order to add the lines in the same order as the records.
        sorting_map = sorting_map_list[index]
        sorted_keys = sorted(list(values_node.keys()), key=lambda x: sorting_map[x][1])

        for key in sorted_keys:

            # Compute 'type_tax_use' with the first grouping since 'src_tax_type_tax_use' is always
            # the first one.
            if groupby_key == 'src_tax_type_tax_use':
                type_tax_use = key
            sign = -1 if type_tax_use == 'sale' else 1

            # Prepare columns.
            tax_amount_dict = values_node[key]
            columns = []
            tax_base_amounts = tax_amount_dict['base_amount']
            tax_amounts = tax_amount_dict['tax_amount']
            for tax_base_amount, tax_amount in zip(tax_base_amounts, tax_amounts):
                # Add the tax base amount.
                if index == len(groupby_fields) - 1:
                    columns.append({
                       'no_format': sign * tax_base_amount,
                       'name': self.format_value(sign * tax_base_amount),
                    })
                else:
                    columns.append({'name': ''})

                # Add the tax amount.
                columns.append({
                   'no_format': sign * tax_amount,
                   'name': self.format_value(sign * tax_amount),
                })

            # Prepare line.
            default_vals = {
                'columns': columns,
                'level': index + 1,
                'unfoldable': False,
            }
            report_line = self._default_tax_report_build_report_line(options, default_vals, groupby_key, sorting_map[key][0])

            if index == 1 and groupby_key == 'src_tax_id':
                tax = sorting_map[key][0]
                report_line.update({
                    'caret_options': 'default.tax.report',
                    'caret_options_args': [type_tax_use, tax.id],
                })

            lines.append(report_line)

            # Process children recursively.
            self._default_tax_report_populate_lines_recursively(
                options,
                lines,
                sorting_map_list,
                groupby_fields,
                tax_amount_dict['children'],
                index=index + 1,
                type_tax_use=type_tax_use,
            )

    @api.model
    def _get_lines_default_tax_report(self, options):
        """ Compute the report lines for the default tax report.

        :param options: The report options.
        :return:        A list of lines, each one being a python dictionary.
        """
        options_list = self._get_options_periods_list(options)

        # Compute tax_base_amount / tax_amount for each selected groupby.
        if options['tax_report'] == 'generic_grouped_tax_account':
            groupby_fields = [('src_tax', 'type_tax_use'), ('src_tax', 'id'), ('account', 'id')]
            comodels = [None, 'account.tax', 'account.account']
        elif options['tax_report'] == 'generic_grouped_account_tax':
            groupby_fields = [('src_tax', 'type_tax_use'), ('account', 'id'), ('src_tax', 'id')]
            comodels = [None, 'account.account', 'account.tax']
        else:
            groupby_fields = [('src_tax', 'type_tax_use'), ('src_tax', 'id')]
            comodels = [None, 'account.tax']

        tax_amount_hierarchy = self._read_default_tax_report_amounts(options_list, groupby_fields)

        # Fetch involved records in order to ensure all lines are sorted according the comodel order.
        # To do so, we compute 'sorting_map_list' allowing to retrieve each record by id and the order
        # to be used.
        record_ids_gb = [set() for dummy in groupby_fields]

        def populate_record_ids_gb_recursively(node, level=0):
            for k, v in node.items():
                if k:
                    record_ids_gb[level].add(k)
                    populate_record_ids_gb_recursively(v['children'], level=level + 1)

        populate_record_ids_gb_recursively(tax_amount_hierarchy)

        sorting_map_list = []
        for i, comodel in enumerate(comodels):
            if comodel:
                # Relational records.
                records = self.env[comodel].search([('id', 'in', tuple(record_ids_gb[i]))])
                sorting_map = {r.id: (r, j) for j, r in enumerate(records)}
                sorting_map_list.append(sorting_map)
            else:
                # src_tax_type_tax_use.
                selection = self.env['account.tax']._fields['type_tax_use'].selection
                sorting_map_list.append({v[0]: (v, j) for j, v in enumerate(selection) if v[0] in record_ids_gb[i]})

        # Compute report lines.
        lines = []
        self._default_tax_report_populate_lines_recursively(
            options,
            lines,
            sorting_map_list,
            groupby_fields,
            tax_amount_hierarchy,
        )
        return lines

    # -------------------------------------------------------------------------
    # REPORT
    # -------------------------------------------------------------------------

    def _get_reports_buttons(self, options):
        res = super()._get_reports_buttons(options)
        if self.env.user.has_group('account.group_account_user'):
            res.append({'name': _('Closing Entry'), 'action': 'periodic_vat_entries', 'sequence': 8})
        return res

    def _compute_vat_closing_entry(self, company, options):
        """Compute the VAT closing entry.

        This method returns the one2many commands to balance the tax accounts for the selected period, and
        a dictionnary that will help balance the different accounts set per tax group.
        """
        self = self.with_company(company) # Needed to handle access to property fields correctly

        # first, for each tax group, gather the tax entries per tax and account
        self.env['account.tax'].flush(['name', 'tax_group_id'])
        self.env['account.tax.repartition.line'].flush(['use_in_tax_closing'])
        self.env['account.move.line'].flush(['account_id', 'debit', 'credit', 'move_id', 'tax_line_id', 'date', 'company_id', 'display_type'])
        self.env['account.move'].flush(['state'])
        sql = """
            SELECT "account_move_line".tax_line_id as tax_id,
                    tax.tax_group_id as tax_group_id,
                    tax.name as tax_name,
                    "account_move_line".account_id,
                    COALESCE(SUM("account_move_line".balance), 0) as amount
            FROM account_tax tax, account_tax_repartition_line repartition, %s
            WHERE %s
              AND tax.id = "account_move_line".tax_line_id
              AND repartition.id = "account_move_line".tax_repartition_line_id
              AND repartition.use_in_tax_closing
            GROUP BY tax.tax_group_id, "account_move_line".tax_line_id, tax.name, "account_move_line".account_id
        """

        new_options = {
            **options,
            'all_entries': False,
            'date': dict(options['date']),
            'multi_company': [{'id': company.id, 'name': company.name}],
        }

        period_start, period_end = company._get_tax_closing_period_boundaries(fields.Date.from_string(options['date']['date_to']))
        new_options['date']['date_from'] = fields.Date.to_string(period_start)
        new_options['date']['date_to'] = fields.Date.to_string(period_end)

        tables, where_clause, where_params = self._query_get(new_options)
        query = sql % (tables, where_clause)
        self.env.cr.execute(query, where_params)
        results = self.env.cr.dictfetchall()

        tax_group_ids = [r['tax_group_id'] for r in results]
        tax_groups = {}
        for tg, result in zip(self.env['account.tax.group'].browse(tax_group_ids), results):
            if tg not in tax_groups:
                tax_groups[tg] = {}
            if result.get('tax_id') not in tax_groups[tg]:
                tax_groups[tg][result.get('tax_id')] = []
            tax_groups[tg][result.get('tax_id')].append((result.get('tax_name'), result.get('account_id'), result.get('amount')))

        # then loop on previous results to
        #    * add the lines that will balance their sum per account
        #    * make the total per tax group's account triplet
        # (if 2 tax groups share the same 3 accounts, they should consolidate in the vat closing entry)
        move_vals_lines = []
        tax_group_subtotal = {}
        currency = self.env.company.currency_id
        for tg, values in tax_groups.items():
            total = 0
            # ignore line that have no property defined on tax group
            if not tg.property_tax_receivable_account_id or not tg.property_tax_payable_account_id:
                continue
            for dummy, value in values.items():
                for v in value:
                    tax_name, account_id, amt = v
                    # Line to balance
                    move_vals_lines.append((0, 0, {'name': tax_name, 'debit': abs(amt) if amt < 0 else 0, 'credit': amt if amt > 0 else 0, 'account_id': account_id}))
                    total += amt

            if not currency.is_zero(total):
                # Add total to correct group
                key = (tg.property_advance_tax_payment_account_id.id or False, tg.property_tax_receivable_account_id.id, tg.property_tax_payable_account_id.id)

                if tax_group_subtotal.get(key):
                    tax_group_subtotal[key] += total
                else:
                    tax_group_subtotal[key] = total

        # If the tax report is completely empty, we add two 0-valued lines, using the first in in and out
        # account id we find on the taxes.
        if len(move_vals_lines) == 0:
            rep_ln_in = self.env['account.tax.repartition.line'].search([
                ('account_id.deprecated', '=', False), ('repartition_type', '=', 'tax'),
                ('company_id', '=', company.id), ('invoice_tax_id.type_tax_use', '=', 'purchase')
            ], limit=1)
            rep_ln_out = self.env['account.tax.repartition.line'].search([
                ('account_id.deprecated', '=', False), ('repartition_type', '=', 'tax'),
                ('company_id', '=', company.id), ('invoice_tax_id.type_tax_use', '=', 'sale')
            ], limit=1)

            if rep_ln_out.account_id and rep_ln_in.account_id:
                move_vals_lines = [
                    Command.create({
                        'name': _('Tax Received Adjustment'),
                        'debit': 0,
                        'credit': 0.0,
                        'account_id': rep_ln_out.account_id.id
                    }),

                    Command.create({
                        'name': _('Tax Paid Adjustment'),
                        'debit': 0.0,
                        'credit': 0,
                        'account_id': rep_ln_in.account_id.id
                    })
                ]

        return move_vals_lines, tax_group_subtotal

    def _add_tax_group_closing_items(self, tax_group_subtotal, end_date):
        """Transform the parameter tax_group_subtotal dictionnary into one2many commands.

        Used to balance the tax group accounts for the creation of the vat closing entry.
        """
        def _add_line(account, name, company_currency):
            self.env.cr.execute(sql_account, (account, end_date))
            result = self.env.cr.dictfetchone()
            advance_balance = result.get('balance') or 0
            # Deduct/Add advance payment
            if not company_currency.is_zero(advance_balance):
                line_ids_vals.append((0, 0, {
                    'name': name,
                    'debit': abs(advance_balance) if advance_balance < 0 else 0,
                    'credit': abs(advance_balance) if advance_balance > 0 else 0,
                    'account_id': account
                }))
            return advance_balance

        currency = self.env.company.currency_id
        sql_account = '''
            SELECT SUM(aml.balance) AS balance
            FROM account_move_line aml
            LEFT JOIN account_move move ON move.id = aml.move_id
            WHERE aml.account_id = %s
              AND aml.date <= %s
              AND move.state = 'posted'
        '''
        line_ids_vals = []
        # keep track of already balanced account, as one can be used in several tax group
        account_already_balanced = []
        for key, value in tax_group_subtotal.items():
            total = value
            # Search if any advance payment done for that configuration
            if key[0] and key[0] not in account_already_balanced:
                total += _add_line(key[0], _('Balance tax advance payment account'), currency)
                account_already_balanced.append(key[0])
            if key[1] and key[1] not in account_already_balanced:
                total += _add_line(key[1], _('Balance tax current account (receivable)'), currency)
                account_already_balanced.append(key[1])
            if key[2] and key[2] not in account_already_balanced:
                total += _add_line(key[2], _('Balance tax current account (payable)'), currency)
                account_already_balanced.append(key[2])
            # Balance on the receivable/payable tax account
            if not currency.is_zero(total):
                line_ids_vals.append((0, 0, {
                    'name': total < 0 and _('Payable tax amount') or _('Receivable tax amount'),
                    'debit': total if total > 0 else 0,
                    'credit': abs(total) if total < 0 else 0,
                    'account_id': key[2] if total < 0 else key[1]
                }))
        return line_ids_vals

    def _generate_tax_closing_entries(self, options, closing_moves=False):
        """Generates and/or updates VAT closing entries.

        This method does computes the content of the tax closing in the following way:
        - Search on all taxe lines in the given period, group them by tax_group (each tax group might have its own
        tax receivable/payable account).
        - Create a move line that balances each tax account and add the difference in the correct receivable/payable
        account. Also take into account amounts already paid via advance tax payment account.

        The tax closing is done so that an individual move is created per available VAT number: so, one for each
        foreign vat fiscal position (each with fiscal_position_id set to this fiscal position), and one for the domestic
        position (with fiscal_position_id = None). The moves created by this function hence depends on the content of the
        options dictionnary, and what fiscal positions are accepted by it.

        :param options: the tax report options dict to use to make the closing.
        :param closing_moves: If provided, closing moves to update the content from.
                              They need to be compatible with the provided options (if they have a fiscal_position_id, for example).

        :return: The closing moves.
        """
        options_company_ids = [company_opt['id'] for company_opt in options.get('multi_company', [])]
        companies = self.env['res.company'].browse(options_company_ids) if options_company_ids else self.env.company
        end_date = fields.Date.from_string(options['date']['date_to'])

        closing_moves_by_company = defaultdict(lambda: self.env['account.move'])
        if closing_moves:
            for move in closing_moves.filtered(lambda x: x.state == 'draft'):
                closing_moves_by_company[move.company_id] |= move
        else:
            closing_moves = self.env['account.move']
            for company in companies:
                include_domestic, fiscal_positions = self._get_fpos_info_for_tax_closing(company, options)
                company_closing_moves = company._get_and_update_tax_closing_moves(end_date, fiscal_positions=fiscal_positions, include_domestic=include_domestic)
                closing_moves_by_company[company] = company_closing_moves
                closing_moves += company_closing_moves

        for company, company_closing_moves in closing_moves_by_company.items():

            # First gather the countries for which the closing is being done
            countries = self.env['res.country']
            for move in company_closing_moves:
                if move.fiscal_position_id.foreign_vat:
                    countries |= move.fiscal_position_id.country_id
                else:
                    countries |= company.account_fiscal_country_id

            # Check the tax groups from the company for any misconfiguration in these countries
            if self.env['account.tax.group']._check_misconfigured_tax_groups(company, countries):
                self._redirect_to_misconfigured_tax_groups(company, countries)

            if company.tax_lock_date and company.tax_lock_date >= end_date:
                raise UserError(_("This period is already closed for company %s", company.name))

            for move in company_closing_moves:
                # get tax entries by tax_group for the period defined in options
                move_options = {**options, 'fiscal_position': move.fiscal_position_id.id if move.fiscal_position_id else 'domestic'}
                line_ids_vals, tax_group_subtotal = self._compute_vat_closing_entry(company, move_options)

                line_ids_vals += self._add_tax_group_closing_items(tax_group_subtotal, end_date)

                if move.line_ids:
                    line_ids_vals += [Command.delete(aml.id) for aml in move.line_ids]

                move_vals = {}
                if line_ids_vals:
                    move_vals['line_ids'] = line_ids_vals

                move_vals['tax_report_control_error'] = bool(move_options.get('tax_report_control_error'))
                if move_options.get('tax_report_control_error'):
                    move.message_post(body=move_options.get('tax_report_control_error'))

                move.write(move_vals)

        return closing_moves

    def _redirect_to_misconfigured_tax_groups(self, company, countries):
        """ Raises a RedirectWarning informing the user his tax groups are missing configuration
        for a given company, redirecting him to the tree view of account.tax.group, filtered
        accordingly to the provided countries.
        """
        need_config_action = {
            'type': 'ir.actions.act_window',
            'name': 'Tax groups',
            'res_model': 'account.tax.group',
            'view_mode': 'tree',
            'views': [[False, 'list']],
            'context': len(countries) == 1 and {'search_default_country_id': countries.ids or {}},
            # More than 1 id into search_default isn't supported
        }

        raise RedirectWarning(
            _('Some of your tax groups are missing information in company %s. Please complete their configuration.', company.display_name),
            need_config_action,
            _('Configure your TAX accounts - %s', company.display_name),
            additional_context={'allowed_company_ids': company.ids, 'force_account_company': company.id}
        )

    def _get_fpos_info_for_tax_closing(self, company, options):
        """ Returns the fiscal positions information to use to generate the tax closing
        for this company, with the provided options.

        :return: (include_domestic, fiscal_positions), where fiscal positions is a recordset
                 and include_domestic is a boolean telling whehter or not the domestic closing
                 (i.e. the one without any fiscal position) must also be performed
        """
        if options['fiscal_position'] == 'domestic':
            fiscal_positions = self.env['account.fiscal.position']
        elif options['fiscal_position'] == 'all':
            fiscal_positions = self.env['account.fiscal.position'].search([('company_id', '=', company.id), ('foreign_vat', '!=', False)])
        else:
            fpos_ids = [options['fiscal_position']]
            fiscal_positions = self.env['account.fiscal.position'].browse(fpos_ids)

        if options['fiscal_position'] == 'all':
            report_country = self._get_country_for_fiscal_position_filter(options)
            fiscal_country = company.account_fiscal_country_id
            include_domestic = not fiscal_positions \
                               or not report_country \
                               or fiscal_country == fiscal_positions[0].country_id
        else:
            include_domestic = options['fiscal_position'] == 'domestic'

        return include_domestic, fiscal_positions

    def _get_columns_name(self, options):
        columns_header = [{'style': 'width: 100%'}]

        if self._is_generic_layout(options):
            columns_header += [{'name': '%s \n %s' % (_('NET'), self.format_date(options)), 'class': 'number'}, {'name': _('TAX'), 'class': 'number'}]
            if options.get('comparison') and options['comparison'].get('periods'):
                for p in options['comparison']['periods']:
                    columns_header += [{'name': '%s \n %s' % (_('NET'), p.get('string')), 'class': 'number'}, {'name': _('TAX'), 'class': 'number'}]
        else:
            columns_header.append({'name': '%s \n %s' % (_('Balance'), self.format_date(options)), 'class': 'number', 'style': 'white-space: pre;'})
            if options.get('comparison') and options['comparison'].get('periods'):
                for p in options['comparison']['periods']:
                    columns_header += [{'name': '%s \n %s' % (_('Balance'), p.get('string')), 'class': 'number', 'style': 'white-space: pre;'}]

        return columns_header

    def _get_templates(self):
        # Overridden to add an option to the tax report to display it grouped by tax grid.
        rslt = super()._get_templates()
        rslt['search_template'] = 'account_reports.search_template_generic_tax_report'
        rslt['main_template'] = 'account_reports.template_tax_report'
        return rslt

    def _compute_from_amls_grids(self, options, dict_to_fill, period_number):
        """Fill dict_to_fill with the data needed to generate the report.

        Used when the report is set to group its line by tax grid.
        """
        tables, where_clause, where_params = self._query_get(options)
        sql = """
            SELECT
                   account_tax_report_line_tags_rel.account_tax_report_line_id,
                   SUM(COALESCE(account_move_line.balance, 0)
                       * CASE WHEN acc_tag.tax_negate THEN -1 ELSE 1 END
                       * CASE WHEN account_move_line.tax_tag_invert THEN -1 ELSE 1 END
                   ) AS balance
              FROM """ + tables + """
              JOIN account_move
                ON account_move_line.move_id = account_move.id
              JOIN account_account_tag_account_move_line_rel aml_tag
                ON aml_tag.account_move_line_id = account_move_line.id
              JOIN account_journal
                ON account_move.journal_id = account_journal.id
              JOIN account_account_tag acc_tag
                ON aml_tag.account_account_tag_id = acc_tag.id
              JOIN account_tax_report_line_tags_rel
                ON acc_tag.id = account_tax_report_line_tags_rel.account_account_tag_id
              JOIN account_tax_report_line report_line
                ON account_tax_report_line_tags_rel.account_tax_report_line_id = report_line.id
             WHERE """ + where_clause + """
               AND report_line.report_id = %s
               AND account_journal.id = account_move_line.journal_id
             GROUP BY account_tax_report_line_tags_rel.account_tax_report_line_id
        """
        params = where_params + [options['tax_report']]
        self.env.cr.execute(sql, params)
        for account_tax_report_line_id, balance in self.env.cr.fetchall():
            if account_tax_report_line_id in dict_to_fill:
                dict_to_fill[account_tax_report_line_id][0]['periods'][period_number]['balance'] = balance
                dict_to_fill[account_tax_report_line_id][0]['show'] = True

    @api.model
    def _get_lines(self, options, line_id=None):
        self.flush()

        if self._is_generic_layout(options):
            return self._get_lines_default_tax_report(options)

        data = self._compute_tax_report_data(options)
        return self._get_lines_by_grid(options, line_id, data)

    @api.model
    def _is_generic_layout(self, options):
        """ Returns true if the provided options correspond to one of the generic variants of the tax report,
        not a localized one.
        """
        return not isinstance(options['tax_report'], int)

    def _get_lines_by_grid(self, options, line_id, grids):
        # Fetch the report layout to use
        report = self.env['account.tax.report'].browse(options['tax_report'])
        formulas_dict = dict(report.line_ids.filtered(lambda l: l.code and l.formula).mapped(lambda l: (l.code, l.formula)))

        # Build the report, line by line
        lines = []
        lines_mapping = {}
        deferred_total_lines = []  # list of tuples (index where to add the total in lines, tax report line object)
        for current_line in report.get_lines_in_hierarchy():

            hierarchy_level = self._get_hierarchy_level(current_line)
            parent_line_id = lines_mapping[current_line.parent_id.id]['id'] if current_line.parent_id.id else None

            if current_line.formula:
                # Then it's a total line
                # We defer the adding of total lines, since their balance depends
                # on the rest of the report. We use a special dictionnary for that,
                # keeping track of hierarchy level
                line = self._prepare_total_line(current_line, parent_line_id, hierarchy_level)
                # Using len(lines) since the line is appended later
                deferred_total_lines.append((len(lines), current_line))
            elif current_line.tag_name:
                # Then it's a tax grid line
                line = self._build_tax_grid_line(grids[current_line.id][0], parent_line_id, hierarchy_level, options)
            else:
                # Then it's a title line
                line = self._build_tax_section_line(current_line, parent_line_id, hierarchy_level)
            lines.append(line)
            lines_mapping[current_line.id] = line

        # Fill in in the total for each title line and get a mapping linking line codes to balances
        balances_by_code = self._postprocess_lines(lines, options)
        for (index, total_line) in deferred_total_lines:
            # number_period option contains 1 if no comparison, or the number of periods to compare with if there is one.
            total_period_number = 1 + (options['comparison'].get('periods') and options['comparison']['number_period'] or 0)
            parent_line_id = lines_mapping[total_line.parent_id.id]['id'] if total_line.parent_id.id else None
            line = self._build_total_line(total_line, parent_line_id, balances_by_code, formulas_dict,
                                          total_period_number, lines[index], options)
            lines[index] = line
            lines_mapping[total_line.id] = line

        return lines

    def _get_hierarchy_level(self, report_line):
        """Return the hierarchy level to be used by a tax report line, depending on its parents.

        A line with no parent will have a hierarchy of 1.
        A line with n parents will have a hierarchy of 2n+1.
        """
        return 1 + 2 * (len(report_line.parent_path[:-1].split('/')) - 1)

    def _postprocess_lines(self, lines, options):
        """Postprocess the report line dictionaries generated for a grouped by tax grid report.

        Used in order to compute the balance of each of its non-total sections.

        :param lines: The list of dictionnaries conaining all the line data generated for this report.
                      Title lines will be modified in place to have a balance corresponding to the sum
                      of their children's

        :param options: The dictionary of options used to buld the report.

        :return: A dictionary mapping the line codes defined in this report to the corresponding balances.
        """
        balances_by_code = {}
        totals_by_line = {}
        active_sections_stack = []
        col_nber = len(options['comparison']['periods']) + 1

        def assign_active_section(col_nber):
            line_to_assign = active_sections_stack.pop()
            total_balance_col = totals_by_line.get(line_to_assign['id'], [0] * col_nber)
            line_to_assign['columns'] = [{'name': self.format_value(balance), 'style': 'white-space:nowrap;', 'balance': balance} for balance in total_balance_col]

            if line_to_assign.get('line_code'):
                balances_by_code[line_to_assign['line_code']] = total_balance_col

        for line in lines:
            while active_sections_stack and line['level'] <= active_sections_stack[-1]['level']:
                assign_active_section(col_nber)

            markup = self._parse_line_id(line['id'])[-1][0]

            if markup == 'total':
                pass
            elif markup == 'section':
                active_sections_stack.append(line)
            else:
                if line.get('line_code'):
                    balances_by_code[line['line_code']] = [col['balance'] for col in line['columns']]

                if active_sections_stack:
                    for active_section in active_sections_stack:
                        line_balances = [col['balance'] for col in line['columns']]
                        rslt_balances = totals_by_line.get(active_section['id'])
                        totals_by_line[active_section['id']] = line_balances if not rslt_balances else [line_balances[i] + rslt_balances[i] for i in range(0, len(rslt_balances))]

        self.compute_check(lines, options)

        # Treat the last sections (the one that were not followed by a line with lower level)
        while active_sections_stack:
            assign_active_section(col_nber)

        return balances_by_code

    def compute_check(self, lines, options):
        """Apply the check process defined for the currently displayed tax report, if there is any.

        This function must only be called if the tax_report
        option is used.
        """
        tax_report = self.env['account.tax.report'].browse(options['tax_report'])

        col_nber = len(options['comparison']['periods']) + 1
        amounts = {}
        carried_over = {}
        controls = []
        html_lines = []
        for line in lines:
            if line.get('line_code'):
                amounts[line['line_code']] = line['columns'][0]['balance']
                carried_over[line['line_code']] = line['columns'][0].get('carryover_bounds', False)

        for i, calc in enumerate(tax_report.get_checks_to_perform(amounts, carried_over)):
            if calc[1]:
                if isinstance(calc[1], float):
                    value = self.format_value(calc[1])
                else:
                    value = calc[1]
                controls.append({'name': calc[0], 'id': 'control_' + str(i), 'columns': [{'name': value,
                                                                                          'style': 'white-space:nowrap;',
                                                                                          'balance': calc[1]}],
                                                                                          'is_control': True})
                html_lines.append("<tr><td>{name}</td><td>{amount}</td></tr>".format(name=calc[0], amount=value))
        if controls:
            lines.extend([{'id': 'section_control', 'name': _('Controls failed'), 'unfoldable': False,
                           'columns': [{'name': '',
                                        'style': 'white-space:nowrap;',
                                        'balance': ''}] * col_nber, 'level': 0, 'line_code': False, 'is_control': True}] + controls)
            options['tax_report_control_error'] = "<table width='100%'><tr><th>Control</th><th>Difference</th></tr>{}</table>".format("".join(html_lines))

    def _get_total_line_eval_dict(self, period_balances_by_code, period_date_from, period_date_to, options):
        """Return period_balances_by_code.

        By default, this function only returns period_balances_by_code; but it
        is meant to be overridden in the few situations where we need to evaluate
        something we cannot compute with only tax report line codes.
        """
        return period_balances_by_code

    def _prepare_total_line(self, current_line, parent_line_id, hierarchy_level):
        return {
            'id': self._get_generic_line_id('account.tax.report.line', current_line.id,
                                            parent_line_id=parent_line_id,
                                            markup='total'),
            'level': hierarchy_level
        }

    def _build_total_line(self, report_line, parent_id, balances_by_code, formulas_dict, number_periods, deferred_line, options):
        """Return the report line dictionary corresponding to a given total line.

        Compute if from its formula.
        """
        def expand_formula(formula):
            for word in re.split(r'\W+', formula):
                if formulas_dict.get(word):
                    formula = re.sub(r'\b%s\b' % word, '(%s)' % expand_formula(formulas_dict.get(word)), formula)
            return formula

        columns = []
        for period_index in range(0, number_periods):
            period_balances_by_code = {code: balances[period_index] for code, balances in balances_by_code.items()}
            period_date_from = (period_index == 0) and options['date']['date_from'] or options['comparison']['periods'][period_index-1]['date_from']
            period_date_to = (period_index == 0) and options['date']['date_to'] or options['comparison']['periods'][period_index-1]['date_to']

            eval_dict = self._get_total_line_eval_dict(period_balances_by_code, period_date_from, period_date_to, options)
            period_total = safe_eval.safe_eval(expand_formula(report_line.formula), eval_dict)

            carryover_account_balance = self.get_carried_over_balance_before_date(report_line, options, period_index)
            column = {
                'name': '' if period_total is None else self.format_value(period_total),
                'style': 'white-space:nowrap;',
                'balance': period_total or 0.0,
            }

            carryover_bounds = report_line._get_carryover_bounds(options, period_total, carryover_account_balance)
            if carryover_bounds:
                column['carryover_bounds'] = carryover_bounds

            columns.append(column)

        return {
            'id': deferred_line['id'],
            'name': report_line.name,
            'unfoldable': False,
            'columns': columns,
            'level': deferred_line['level'],
            'line_code': report_line.code,
            'tax_report_line': report_line
        }

    def _build_tax_section_line(self, section, parent_id, hierarchy_level):
        """Return the report line dictionary corresponding to a given section.

        Used when grouping the report by tax grid.
        """
        line_id = self._get_generic_line_id('account.tax.report.line', section.id, parent_line_id=parent_id, markup='section')

        return {
            'id': line_id,
            'name': section.name,
            'unfoldable': False,
            'columns': [],
            'level': hierarchy_level,
            'line_code': section.code,
        }

    def _build_tax_grid_line(self, grid_data, parent_id, hierarchy_level, options):
        """Return the report line dictionary corresponding to a given tax grid.

        Used when grouping the report by tax grid.
        """
        columns = []
        for i, period in enumerate(grid_data['periods']):
            carryover_account_balance = self.get_carried_over_balance_before_date(grid_data['obj'], options, i)

            value = period['balance']
            if grid_data['obj'].is_carryover_used_in_balance:
                value += carryover_account_balance

            column = {
                'name': self.format_value(value),
                'style': 'white-space:nowrap;',
                'balance': value
            }

            carryover_bounds = grid_data['obj']._get_carryover_bounds(options, value, carryover_account_balance)
            if carryover_bounds:
                column['carryover_bounds'] = carryover_bounds

            columns.append(column)

        line_id = self._get_generic_line_id('account.tax.report.line', grid_data['obj'].id, parent_line_id=parent_id)

        rslt = {
            'id': line_id,
            'name': grid_data['obj'].name,
            'unfoldable': False,
            'columns': columns,
            'level': hierarchy_level,
            'line_code': grid_data['obj'].code,
            'tax_report_line': grid_data['obj']
        }

        if grid_data['obj'].report_action_id:
            rslt['action_id'] = grid_data['obj'].report_action_id.id
        else:
            rslt['caret_options'] = 'account.tax.report.line'

        return rslt

    def _format_lines_for_display(self, lines, options):
        """
        Verify for each line if they are impacted by the carry over, and if so in which way.
        Then add a tooltip/styling if needed to represent this impact in the view.
        :param lines: A list with the lines for this report.
        :param options: The options for this report.
        :return: The formatted list of lines
        """
        if options.get('tax_report'):
            tax_report_line_report_line_mapping = {}

            for line in lines:
                if not line.get('tax_report_line'):
                    continue

                # If the line has carryover bounds, we'll take it.
                if any(c.get('carryover_bounds') for c in line['columns']):
                    for index, column in enumerate(line['columns']):
                        # The index of the column represent the periods, where 0 = current and 1+ the compared ones
                        self._format_column_after_carryover(line, column, index, options)

                # Keep track of the link between account.tax.report.line and our report line
                tax_report_line_report_line_mapping[line.get('tax_report_line').id] = line

                # So that we can find that line if it is target of another one.
                if line['tax_report_line'].carry_over_destination_line_id:
                    destination_line_id = line['tax_report_line'].carry_over_destination_line_id.id
                    if destination_line_id not in tax_report_line_report_line_mapping:
                        continue

                    columns = tax_report_line_report_line_mapping[destination_line_id]['columns']
                    for index, column in enumerate(columns):
                        self._format_column_after_carryover(line, column, index, options)

            # Also update the section totals to represent those changes
            # Filter to ignore control lines if any
            lines_without_controls = [line for line in lines if not line.get('is_control', False)]
            self._postprocess_lines(lines_without_controls, options)

        return lines

    def _format_column_after_carryover(self, line, column, period, options):
        """
        Format a single column for a line, and apply changes to display the status of the carryover for it.
        :param line: The line to which this column belongs.
        :param column: The column to be adapted.
        :param period: A int value representing the period of this column. By default 0 mean the current period, and 1+
        mean the past periods.
        :param options: The options of the report.
        """
        tax_report_line = line.get('tax_report_line', False)
        carryover_bounds = column.get('carryover_bounds', None)
        line_balance, carryover_balance = self.get_amounts_after_carryover(tax_report_line, column['balance'],
                                                                           carryover_bounds, options, period)
        carryover_balance = self.format_value(carryover_balance)

        # When we are not printing (on the web page) we'll show a contextual tooltip.
        if not self.env.context.get('print_mode') and carryover_bounds is not None:
            popup_data = {}
            messages = self._get_popup_messages(line_balance, carryover_balance, options, tax_report_line)
            column_styles = self._get_column_styles(line)
            column_style = column_styles.get('base_style', '')

            if carryover_bounds[0] is not None and column['balance'] < carryover_bounds[0]:
                popup_data.update(messages['out_of_bounds'])
                column_style += column_styles.get('below_bound_style', '')
            elif carryover_bounds[1] is not None and column['balance'] > carryover_bounds[1]:
                popup_data.update(messages['out_of_bounds'])
                column_style += column_styles.get('above_bound_style', '')

            # We are between the bounds. We'll take as much as possible in the carryover balance as we can without
            # going out of bounds
            else:
                balance = column['balance'] - line_balance
                if balance < 0:
                    popup_data.update(messages['positive'])
                elif balance > 0:
                    popup_data.update(messages['negative'])

            # Add the tooltip and style as needed
            if column_style:
                column['style'] = column_style

            if popup_data:
                popup_data.update({
                    'id': tax_report_line.id,
                    'debug': self.user_has_groups('base.group_no_one'),
                    'balance': messages.get('balance', ''),
                })
                column['carryover_popup_data'] = json.dumps(popup_data)
                column['popup_template'] = 'accountReports.CarryOverInfoTemplate'
        else:
            # Update the balance when printing
            # If the carryover is persistent, do not take the balance into account when formatting:
            # it'll already have been directly into the report.
            if tax_report_line.is_carryover_persistent:
                column['name'] = self.format_value(line_balance)
                column['balance'] = line_balance

    def _get_column_styles(self, report_line):
        return {
            'base_style': 'white-space:nowrap;',
            'above_bound_style': ' color:green;',
            'below_bound_style': ' color:red;',
        }

    def _get_popup_messages(self, line_balance, carryover_balance, options, tax_report_line):
        return {
            'positive': {
                'description1': _("This amount will be increased by the positive amount from"),
                'description2': _(" past period(s), previously stored on the corresponding tax line."),
                'description3': _("The amount will be : %s", self.format_value(line_balance)),
            },
            'negative': {
                'description1': _("This amount will be reduced by the negative amount from"),
                'description2': _(" past period(s), previously stored on the corresponding tax line."),
                'description3': _("The amount will be : %s", self.format_value(line_balance)),
            },
            'out_of_bounds': {
                'description1': _("This amount will be set to %s.", self.format_value(line_balance)),
                'description2': _("The difference will be carried over to the next period's declaration."),
            },
            'balance': _("The carried over balance will be : %s", carryover_balance),
        }

    def get_amounts_after_carryover(self, tax_report_line, amount, carryover_bounds, options, period, persistent=True):
        """
        Adapt the line amount based on the carried over balance for this line.
        If the amount is outside of the bounds, it'll be set to the nearest one and the difference will be
        added to the carryover balance.
        If the amount is between the bounds, we'll use as much we can without stepping out of them to try
        to neutralize the carryover balance.
        :param tax_report_line: The tax report line of which we are trying to find the carryover balance
        :param amount: The amount we are formatting.
        :param carryover_bounds: The upper and lower bounds for this line.
        :param options: The report options.
        :param period: An index representing the period of this line in the options.
        0 is the current period, and 1+ would be periods that are being compared to.
        :return: The newly adapted amount for the line, along with the one for the carryover
        """
        if carryover_bounds is None:
            return amount, self.get_carried_over_balance_before_date(tax_report_line, options, period)

        # Non-persistent carryover always bring the carryover balance to the balance of the line
        if not persistent:
            return amount, amount

        delta = 0

        # Get the balance from this account for chosen period
        carryover_balance = self.get_carried_over_balance_before_date(tax_report_line, options, period)

        # Amounts below the lower bounds are set to it
        if carryover_bounds[0] is not None and amount < carryover_bounds[0]:
            delta = carryover_bounds[0] - amount
            amount = carryover_bounds[0]
        # Amounts above the upper bounds are set to it
        elif carryover_bounds[1] is not None and amount > carryover_bounds[1]:
            delta = carryover_bounds[1] - amount
            amount = carryover_bounds[1]
        # Amounts between the bounds are changed according to the current balance of the carryover
        else:
            maximum_to_take = 0
            if carryover_balance < 0:
                maximum_to_take = amount - carryover_bounds[0] if carryover_bounds[0] is not None else carryover_balance
            elif carryover_balance > 0:
                maximum_to_take = carryover_bounds[1] - amount if carryover_bounds[1] is not None else carryover_balance

            if maximum_to_take != 0:
                if maximum_to_take >= abs(carryover_balance):
                    delta = carryover_balance
                else:
                    delta = copysign(maximum_to_take, carryover_balance)

            amount += delta

        return amount, carryover_balance - delta

    @api.model
    def _compute_tax_report_data(self, options):
        rslt = {}
        empty_data_dict = {'net': 0, 'tax': 0} if self._is_generic_layout(options) else {'balance': 0}
        for record in self.env['account.tax.report'].browse(options['tax_report']).line_ids:
            rslt[record.id] = defaultdict(lambda record=record: {
                'obj': record,
                'show': False,
                'periods': [empty_data_dict.copy() for i in range(len(options['comparison'].get('periods')) + 1)]
            })

        for period_number, period_options in enumerate(self._get_options_periods_list(options)):
            self._compute_from_amls_grids(period_options, rslt, period_number)

        return rslt

    @api.model
    def _get_report_name(self):
        return _('Tax Report')

    def get_carried_over_balance_before_date(self, tax_report_line, options, period=0):
        """
        Allows to get the carried over balance before a certain date.
        This allows us to keep the carry over for a certain period consistent even once the balance has changed.
        :param period: The period of the column we are trying to get the balance for.
        :param options: The options of the report.
        :param tax_report_line: The concerned tax report line.
        :return: The balance of the accounts before the given date.
        """
        if period == 0:
            date_from = options['date'].get('date_from')
        else:
            date_from = options['comparison']['periods'][period - 1].get('date_from')

        requested_date = datetime.strptime(date_from, "%Y-%m-%d").date()

        # Get the default domain for the carryover lines of this tax line.
        domain = tax_report_line._get_carryover_lines_domain(options)

        # Append to the domain the necessary filters depending on the current context.
        if options['fiscal_position'] == 'domestic':
            domain = expression.AND([domain, [('date', '<', requested_date),
                                              ('foreign_vat_fiscal_position_id', '=', False)]])
        elif options['fiscal_position'] == 'all':
            domain = expression.AND([domain, [('date', '<', requested_date)]])
        else:
            domain = expression.AND([domain, [('date', '<', requested_date),
                                              ('foreign_vat_fiscal_position_id', '=', options['fiscal_position'])]])

        # Get the correct carryover lines, and use them to get the balance
        carryover_lines = self.env['account.tax.carryover.line'].search(domain)
        balance = sum(line.amount for line in carryover_lines)

        return balance

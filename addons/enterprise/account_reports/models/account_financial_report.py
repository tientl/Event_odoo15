# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import ast
import json

from .formula import FormulaSolver, PROTECTED_KEYWORDS
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.tools import float_is_zero, ustr
from odoo.exceptions import ValidationError
from odoo.osv import expression


class ReportAccountFinancialReport(models.Model):
    _name = "account.financial.html.report"
    _description = "Account Report (HTML)"
    _inherit = "account.report"

    filter_all_entries = False
    filter_hierarchy = False

    @property
    def filter_date(self):
        if self.date_range:
            return {'mode': 'range', 'filter': 'this_year'}
        else:
            return {'mode': 'single', 'filter': 'today'}

    @property
    def filter_comparison(self):
        if self.comparison:
            return {'date_from': '', 'date_to': '', 'filter': 'no_comparison', 'number_period': 1}
        return super().filter_comparison

    @property
    def filter_unfold_all(self):
        if self.unfold_all_filter:
            return False
        return super().filter_unfold_all

    @property
    def filter_journals(self):
        if self.show_journal_filter:
            return True
        return super().filter_journals

    @property
    def filter_analytic(self):
        enable_filter_analytic_accounts = self.env.user.id in self.env.ref('analytic.group_analytic_accounting').users.ids
        enable_filter_analytic_tags = self.env.user.id in self.env.ref('analytic.group_analytic_tags').users.ids
        if self.analytic and not enable_filter_analytic_accounts and not enable_filter_analytic_tags:
            return None
        return self.analytic or None

    @property
    def filter_ir_filters(self):
        return self.applicable_filters_ids or None

    name = fields.Char(translate=True)
    line_ids = fields.One2many('account.financial.html.report.line', 'financial_report_id', string='Lines')
    date_range = fields.Boolean('Based on date ranges', default=True, help='specify if the report use date_range or single date')
    comparison = fields.Boolean('Allow comparison', default=True, help='display the comparison filter')
    analytic = fields.Boolean('Allow analytic filters', help='display the analytic filters')
    show_journal_filter = fields.Boolean('Allow filtering by journals', help='display the journal filter in the report')
    unfold_all_filter = fields.Boolean('Show unfold all filter', help='display the unfold all options in report')
    company_id = fields.Many2one('res.company', string='Company')
    generated_menu_id = fields.Many2one(
        string='Menu Item', comodel_name='ir.ui.menu', copy=False,
        help="The menu item generated for this report, or None if there isn't any."
    )
    parent_id = fields.Many2one('ir.ui.menu', related="generated_menu_id.parent_id", readonly=False)
    tax_report = fields.Boolean('Tax Report', help="Set to True to automatically filter out journal items that are not tax exigible.")
    applicable_filters_ids = fields.Many2many('ir.filters', domain="[('model_id', '=', 'account.move.line')]",
                                              help='Filters that can be used to filter and group lines in this report. This uses saved filters on journal items.')
    country_id = fields.Many2one(string="Country", comodel_name='res.country', help="The country this report is intended to.")

    # -------------------------------------------------------------------------
    # OPTIONS: ir_filters
    # -------------------------------------------------------------------------

    def _get_country_for_fiscal_position_filter(self, options):
        return self.tax_report and self.country_id or None

    def _init_filter_ir_filters(self, options, previous_options=None):
        ''' Initialize the ir_filters filter that is used to bring additional filters on the whole report.
        E.g. Create an ir.filter like [('partner_id', '=', 3)] and add it to the financial report.
        The filter is visible on the rendered financial report to be enabled/disabled by the user.
        :param options:             Current report options.
        :param previous_options:    Previous report options.
        '''
        if self.filter_ir_filters is None:
            return

        if previous_options and previous_options.get('ir_filters'):
            filters_map = dict((opt['id'], opt['selected']) for opt in previous_options['ir_filters'])
        else:
            filters_map = {}
        options['ir_filters'] = []
        for ir_filter in self.applicable_filters_ids:
            options['ir_filters'].append({
                'id': ir_filter.id,
                'name': ir_filter.name,
                'domain': ast.literal_eval(ir_filter.domain),
                'groupby': (ir_filter.context and ast.literal_eval(ir_filter.context) or {}).get('group_by', []),
                'selected': filters_map.get(ir_filter.id, False),
            })

    @api.model
    def _get_options_ir_filters_domain(self, options):
        ''' Helper to retrieve all selected ir.filter options.
        :param options:     The current report options.
        :return:            A list of ir.filter options inside the 'ir_filters' key.
        '''
        if not options.get('ir_filters'):
            return []
        domain = []
        for option in options['ir_filters']:
            if option['selected']:
                domain += option['domain']
        return domain

    @api.model
    def _is_allowed_groupby_field(self, field):
        ''' Method used to filter the fields to be used in the group by filter.
        :param field:   An ir.model.field record.
        :return:        True if the field is allowed in the group by filter, False otherwise.
        '''
        return field.name not in ('one2many', 'many2many') and field.store

    @api.model
    def _get_options_groupby_fields(self, options):
        ''' Helper to retrieve all selected groupby fields.
        :param options:     The current report options.
        :return:            A list of valid fields on which perform the horizontal groupby.
        '''
        if not options.get('ir_filters'):
            return []

        AccountMoveLine = self.env['account.move.line']
        groupby_fields = []
        for option in options['ir_filters']:
            if not option['selected']:
                continue

            selected_fields = option['groupby']
            for field in selected_fields:
                if field in AccountMoveLine._fields and self._is_allowed_groupby_field(AccountMoveLine._fields[field]):
                    groupby_fields.append(field)
        return groupby_fields

    @api.model
    def _get_options_domain(self, options):
        # OVERRIDE to handle custom domains by the ir.filter filter.
        domain = super(ReportAccountFinancialReport, self)._get_options_domain(options)
        domain += self._get_options_ir_filters_domain(options)
        return domain

    # -------------------------------------------------------------------------
    # OPTIONS
    # -------------------------------------------------------------------------

    def _get_options(self, previous_options=None):
        # OVERRIDE
        options = super(ReportAccountFinancialReport, self)._get_options(previous_options)

        # If manual values were stored in the context, we store them as options.
        # This is useful for report printing, were relying only on the context is
        # not enough, because of the use of a route to download the report (causing
        # a context loss, but keeping the options).
        if self._context.get('financial_report_line_values'):
            options['financial_report_line_values'] = self.env.context['financial_report_line_values']

        return options

    def _set_context(self, options):
        ctx = super(ReportAccountFinancialReport, self)._set_context(options)
        ctx['model'] = self._name
        return ctx

    def _get_templates(self):
        # Update the report_financial templates to include the buttons for the missing / excess journal items.
        templates = super()._get_templates()
        templates['main_template'] = 'account_reports.main_template_control_domain'
        return templates

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    @api.model
    def _format_cell_value(self, financial_line, amount, currency=False, blank_if_zero=False):
        ''' Format the value to display inside a cell depending the 'figure_type' field in the financial report line.
        :param financial_line:  An account.financial.html.report.line record.
        :param amount:          A number.
        :param currency:        An optional res.currency record.
        :param blank_if_zero:   An optional flag forcing the string to be empty if amount is zero.
        :return:
        '''
        if not financial_line.formulas:
            return ''

        if self._context.get('no_format'):
            return amount

        if financial_line.figure_type == 'float':
            return super().format_value(amount, currency=currency, blank_if_zero=blank_if_zero)
        elif financial_line.figure_type == 'percents':
            return str(round(amount * 100, 1)) + '%'
        elif financial_line.figure_type == 'no_unit':
            return round(amount, 1)
        return amount

    @api.model
    def _compute_growth_comparison_column(self, options, value1, value2, green_on_positive=True):
        ''' Helper to get the additional columns due to the growth comparison feature. When only one comparison is
        requested, an additional column is there to show the percentage of growth based on the compared period.
        :param options:             The report options.
        :param value1:              The value in the current period.
        :param value2:              The value in the compared period.
        :param green_on_positive:   A flag customizing the value with a green color depending if the growth is positive.
        :return:                    The new columns to add to line['columns'].
        '''
        if float_is_zero(value2, precision_rounding=0.1):
            return {'name': _('n/a'), 'class': 'number'}
        else:
            res = round((value1 - value2) / value2 * 100, 1)

            # In case the comparison is made on a negative figure, the color should be the other
            # way around. For example:
            #                       2018         2017           %
            # Product Sales      1000.00     -1000.00     -200.0%
            #
            # The percentage is negative, which is mathematically correct, but my sales increased
            # => it should be green, not red!
            if float_is_zero(res, precision_rounding=0.1):
                return {'name': '0.0%', 'class': 'number'}
            elif (res > 0) != (green_on_positive and value2 > 0):
                return {'name': str(res) + '%', 'class': 'number color-red'}
            else:
                return {'name': str(res) + '%', 'class': 'number color-green'}

    @api.model
    def _display_growth_comparison(self, options):
        ''' Helper determining if the growth comparison feature should be displayed or not.
        :param options: The report options.
        :return:        A boolean.
        '''
        return options.get('comparison') \
               and len(options['comparison'].get('periods', [])) == 1 \
               and not self._get_options_groupby_fields(options)

    @api.model
    def _compute_debug_info_column(self, options, solver, financial_line):
        ''' Helper to get the additional columns to display the debug info popup.
        :param options:             The report options.
        :param solver:              The FormulaSolver instance used to compute the formulas.
        :param financial_line:      An account.financial.html.report.line record.
        :return:                    The new columns to add to line['columns'].
        '''
        if financial_line.formulas:
            results = solver.get_results(financial_line)
            failed_control_domain = financial_line.id in options.get('control_domain_missing_ids', []) + options.get('control_domain_excess_ids', [])
            return {
                'style': 'width: 1%; text-align: right;',
                'template': 'account_reports.cell_template_debug_popup_financial_reports',
                'line_code': financial_line.code or '',
                'popup_template': 'accountReports.FinancialReportInfosTemplate',
                'popup_class': 'fa fa-info-circle',
                'popup_attributes': {'tabindex': 1},
                'popup_data': json.dumps({
                    'id': financial_line.id,
                    'name': financial_line.name,
                    'code': financial_line.code or '',
                    'formula': solver.get_formula_popup(financial_line),
                    'formula_with_values': solver.get_formula_string(financial_line),
                    'formula_balance': self._format_cell_value(financial_line, sum(results['formula'].values())),
                    'domain': str(financial_line.domain) if solver.is_leaf(financial_line) and financial_line.domain else '',
                    'control_domain': failed_control_domain and str(financial_line.control_domain),
                    'display_button': solver.has_move_lines(financial_line),
                }),
            }
        else:
            return {'style': 'width: 1%;'}

    @api.model
    def _display_debug_info(self, options):
        ''' Helper determining if the debug info popup column should be displayed or not.
        :param options: The report options.
        :return:        A boolean.
        '''
        return not self._context.get('print_mode') and self.user_has_groups('base.group_no_one') \
               and (not options.get('comparison') or not options['comparison'].get('periods'))

    def _get_report_country_code(self, options):
        # Overridden in order to also take the financial report's country_id into account.
        # Indeed, _get_country_for_fiscal_position_filter will not return it if the report
        # doesn't have tax_report = True.
        fp_country = self._get_country_for_fiscal_position_filter(options)
        return fp_country and fp_country.code or self.country_id.code or None

    # -------------------------------------------------------------------------
    # COLUMNS / LINES
    # -------------------------------------------------------------------------

    @api.model
    def _build_lines_hierarchy(self, options_list, financial_lines, solver, groupby_keys):
        ''' Travel the whole hierarchy and create the report lines to be rendered.
        :param options_list:        The report options list, first one being the current dates range, others being the
                                    comparisons.
        :param financial_lines:     An account.financial.html.report.line recordset.
        :param solver:              The FormulaSolver instance used to compute the formulas.
        :param groupby_keys:        The sorted encountered keys in the solver.
        :return:                    The lines.
        '''
        lines = []
        for financial_line in financial_lines:

            is_leaf = solver.is_leaf(financial_line)
            has_lines = solver.has_move_lines(financial_line)

            financial_report_line = self._get_financial_line_report_line(
                options_list[0],
                financial_line,
                solver,
                groupby_keys,
            )

            # Manage 'hide_if_zero' field.
            if financial_line.hide_if_zero and all(self.env.company.currency_id.is_zero(column['no_format'])
                                                   for column in financial_report_line['columns'] if 'no_format' in column):
                continue

            # Manage 'hide_if_empty' field.
            if financial_line.hide_if_empty and is_leaf and not has_lines:
                continue

            lines.append(financial_report_line)

            aml_lines = []
            if financial_line.children_ids:
                # Travel children.
                lines += self._build_lines_hierarchy(options_list, financial_line.children_ids, solver, groupby_keys)
            elif is_leaf and financial_report_line['unfolded']:
                # Fetch the account.move.lines.
                solver_results = solver.get_results(financial_line)
                sign = solver_results['amls']['sign']
                for groupby_id, display_name, results in financial_line._compute_amls_results(options_list, self, sign=sign):
                    aml_lines.append(self._get_financial_aml_report_line(
                        options_list[0],
                        financial_report_line['id'],
                        financial_line,
                        groupby_id,
                        display_name,
                        results,
                        groupby_keys,
                    ))
            lines += aml_lines

            if self.env.company.totals_below_sections and (financial_line.children_ids or (is_leaf and financial_report_line['unfolded'] and aml_lines)):
                lines.append(self._get_financial_total_section_report_line(options_list[0], financial_report_line))
                financial_report_line["unfolded"] = True  # enables adding "o_js_account_report_parent_row_unfolded" -> hides total amount in head line as it is displayed later in total line

        return lines

    @api.model
    def _build_headers_hierarchy(self, options_list, groupby_keys):
        ''' Build the report headers hierarchy by taking care about additional group bys enabled.

        Suppose a groupby partner_id,currency_id,date with 'groupby_keys' equals to
        (0,1,3,'2019-01-01'), (0,1,2,'2019-01-02'), (0,2,1,'2019-01-03'), (1,2,3,None).
        Make the assumption the many2one are sorted by ids.
        We want to build construct the following headers:

        |                   <current_report_date>                       |                   <comparison_1>                              |
        |           partner_id=1        |           partner_id=2        |           partner_id=1        |           partner_id=2        |
        | currency_id=2 | currency_id=3 | currency_id=1 | currency_id=3 | currency_id=2 | currency_id=3 | currency_id=1 | currency_id=3 |
        | '2019-01-02'  | '2019-01-01'  | '2019-01-03'  | None          | '2019-01-02'  | '2019-01-01'  | '2019-01-03'  | None          |

        :param options_list:        The report options list, first one being the current dates range, others being the
                                    comparisons.
        :param groupby_keys:        The keys used during formulas.
        :return:                    The headers hierarchy.
        '''
        groupby_list = self._get_options_groupby_fields(options_list[0])

        #########################################################################
        # Create the sorting_map used to track the order / name for each record / group by.
        # The complexity is to fetch the records using a minimum number of queries
        # according their table's order.
        #
        # Convert (0,1,3,'2019-01-01'), (0,1,2,'2019-01-02'), (0,2,1,'2019-01-03'), (1,2,3,None) into:
        #
        # keys_grouped_by_ids: [{1, 2}, {2, 3, 1}, {'2019-01-01', '2019-01-02', '2019-01-03'}]
        #
        # Then, fetch values and create the sorting_map:
        #
        # [
        #   {0: (0, 'period_date'), 1: (1, 'comparison_1')}
        #   {1: (0, 'partner_1'), 2: (1, 'partner_2')},
        #   {1: (0, 'currency_1'), 2: (1, 'currency_2'), 3: (2, 'currency_2')},
        #   {'2019-01-01': (0, '2019-01-01'), '2019-01-02': (1, '2019-01-02'), '2019-01-03': (2, '2019-01-03'), None: (3, 'Undefined')},
        # ]
        #
        #########################################################################

        keys_grouped_by_ids = [set() for gb in groupby_list]
        for key in groupby_keys:
            # Skip the first element that is the period number.
            # All comparisons must have the same headers.
            for i, value in enumerate(key[1:]):
                if value is not None:
                    keys_grouped_by_ids[i].add(value)

        sorting_map = [{i: (i, self.format_date(options)) for i, options in enumerate(options_list)}]
        for groupby, ids_set in zip(groupby_list, keys_grouped_by_ids):
            groupby_field = self.env['account.move.line']._fields[groupby]
            values_map = {None: (len(ids_set) + 1, _('Undefined'))}
            if groupby_field.relational:
                # Preserve the table order by using search instead of browse.
                sorted_records = self.env[groupby_field.comodel_name].with_context(active_test=False).search([('id', 'in', tuple(ids_set))])
                index = 0
                for record, name_get_res in zip(sorted_records, sorted_records.name_get()):
                    values_map[record.id] = (index, name_get_res[1])
                    index += 1
            else:
                # Sort the keys in a lexicographic order.
                if groupby_field.name == 'date':
                    format_func = lambda v: fields.Date.to_string(v)
                elif groupby_field.name == 'datetime':
                    format_func = lambda v: fields.Datetime.to_string(v)
                else:
                    format_func = lambda v: v
                for i, v in enumerate(sorted(list(ids_set))):
                    values_map[v] = (i, format_func(v))
            sorting_map.append(values_map)

        #########################################################################
        # Create the hierarchy of headers, sorted by keys with the right colspan.
        #
        # Convert (0,1,3,'2019-01-01'), (0,1,2,'2019-01-02'), (0,2,1,'2019-01-03'), (1,2,3,None) into:
        #
        # [
        #   {'name': '', 'colspan': 4, 'children': [
        #       {'name': 'partner_1', 'colspan': 2, 'children': [
        #           {'name': 'currency_2', 'colspan': 1, 'children': [
        #               {'name': '2019-01-02', 'colspan': 1, 'children': []},
        #           ]},
        #           {'name': 'currency_3', 'colspan': 1, 'children': [
        #               {'name': '2019-01-01', 'colspan': 1, 'children': []},
        #           ]},
        #       ]},
        #       {'name': 'partner_2', 'colspan': 2, 'children': [
        #           {'name': 'currency_1', 'colspan': 1, 'children': [
        #               {'name': '2019-01-03', 'colspan': 1, 'children': []},
        #           ]},
        #           {'name': 'currency_3', 'colspan': 1, 'children': [
        #               {'name': 'Undefined', 'colspan': 1, 'children': []},
        #           ]},
        #       ]},
        #   ]},
        # ]
        #
        #########################################################################

        def _create_headers_hierarchy(level_keys, level=0):
            current_node = {}
            for key in level_keys:
                current_node.setdefault(key[0], set())
                sub_key = key[1:]
                if sub_key:
                    current_node[key[0]].add(sub_key)
            headers = [{
                'name': sorting_map[level][key][1],
                'colspan': len(sub_keys) or 1,
                'children': _create_headers_hierarchy(sub_keys, level=level+1) if sub_keys else None,
                'key': key,
                'class': 'number'
            } for key, sub_keys in current_node.items()]
            headers = sorted(headers, key=lambda header: sorting_map[level][header['key']][0])
            return headers

        level_keys = [(0,) + key[1:] for key in groupby_keys] or [(0,)]
        headers_hierarchy = _create_headers_hierarchy(set(level_keys))

        #########################################################################
        # Convert the newly created hierarchy of headers to the list.
        # Collect keys in the right order to create lines's columns.
        # Duplicate keys in order to manage also the comparisons.
        #
        # 'headers_hierarchy' will be converted to:
        #
        # [
        #   [
        #       {'name': 'period_date', 'colspan': 4},                                      # period_0
        #       {'name': 'comparison_date', 'colspan': 4},                                  # comparison_1
        #   ],
        #   [
        #       {'name': 'partner_1', 'colspan': 2}, {'name': 'partner_2', 'colspan': 2}],  # period_0
        #       {'name': 'partner_1', 'colspan': 2}, {'name': 'partner_2', 'colspan': 2}],  # comparison_1
        #   [
        #       {'name': 'currency_2', 'colspan': 1}, {'name': 'currency_3', 'colspan': 1}, # period_0
        #       {'name': 'currency_1', 'colspan': 1}, {'name': 'currency_3', 'colspan': 1},
        #       {'name': 'currency_2', 'colspan': 1}, {'name': 'currency_3', 'colspan': 1}, # comparison_1
        #       {'name': 'currency_1', 'colspan': 1}, {'name': 'currency_3', 'colspan': 1},
        #   ],
        #   [
        #       {'name': '2019-01-02', 'colspan': 1}, {'name': '2019-01-01', 'colspan': 1},  # period_0
        #       {'name': '2019-01-03', 'colspan': 1}, {'name': 'Undefined', 'colspan': 1},
        #       {'name': '2019-01-02', 'colspan': 1}, {'name': '2019-01-01', 'colspan': 1}, # comparison_1
        #       {'name': '2019-01-03', 'colspan': 1}, {'name': 'Undefined', 'colspan': 1},
        #   ],
        # ]
        #
        # ... with the corresponding sorted keys:
        #
        # [
        #   (0,1,2,'2019-01-02'), (0,1,3,'2019-01-01'), (0,2,1,'2019-01-03'), (0,2,3,None),     # period_0
        #   (1,1,2,'2019-01-02'), (1,1,3,'2019-01-01'), (1,2,1,'2019-01-03'), (1,2,3,None),     # comparison_1
        # ]
        #
        #########################################################################

        headers = [[] for i in range(len(groupby_list) + 1)]
        sorted_groupby_keys = []

        def _populate_headers(current_node, current_key=[], level=0):
            headers[level] += current_node
            for header in current_node:
                children = header.pop('children')
                if children:
                    _populate_headers(children, current_key + [header['key']], level=level + 1)
                else:
                    sorted_groupby_keys.append(tuple(current_key + [header['key']]))

        _populate_headers(headers_hierarchy)

        # Add empty header if there is no data.
        for j in range(1, len(headers)):
            if not headers[j]:
                headers[j].append({'name': '', 'class': 'number', 'colspan': 1})

        # Manage comparison + update string.
        additional_sorted_groupby_keys = []
        additional_headers = [[] for i in range(len(groupby_list) + 1)]
        for i, options in enumerate(options_list):
            if i == 0:
                # Current period.
                headers[0][0]['name'] = sorting_map[0][0][1]
            else:
                for j in range(len(headers)):
                    if j == 0:
                        additional_headers[j].append(headers[j][-1].copy())
                    else:
                        additional_headers[j] += headers[j]
                additional_headers[0][-1]['name'] = sorting_map[0][i][1]
                for key in sorted_groupby_keys:
                    new_key = list(key)
                    new_key[0] = i
                    additional_sorted_groupby_keys.append(tuple(new_key))
        sorted_groupby_keys += additional_sorted_groupby_keys
        for i, headers_row in enumerate(additional_headers):
            headers[i] += headers_row

        # Add left unnamed header.
        for i in range(len(headers)):
            headers[i] = [{'name': '', 'class': 'number', 'colspan': 1}] + headers[i]

        # Manage the growth comparison feature.
        if self._display_growth_comparison(options_list[0]):
            headers[0].append({'name': '%', 'class': 'number', 'colspan': 1})

        # Manage the debug info columns.
        if self._display_debug_info(options_list[0]):
            for i in range(len(headers)):
                if i == 0:
                    headers[i].append({
                        'template': 'account_reports.cell_template_show_bug_financial_reports',
                        'style': 'width: 1%; text-align: right;',
                    })
                else:
                    headers[i].append({'name': '', 'style': 'width: 1%; text-align: right;'})

        return headers, sorted_groupby_keys

    def _get_lines(self, options, line_id=None):
        # OVERRIDE.
        # /!\ As '_get_table' is overrided, this method is called only when a line is unfolded.
        # Then, line_id will never be None.
        self.ensure_one()
        options_list = self._get_options_periods_list(options)

        model_name, model_id = self._get_model_info_from_id(line_id)
        if model_name != 'account.financial.html.report.line':
            raise Exception("Error: trying to unfold a line which isn't a financial report line.")

        financial_line = self.env['account.financial.html.report.line'].browse(model_id)
        formula_solver = FormulaSolver(options_list, self)
        formula_solver.fetch_lines(financial_line)
        sorted_groupby_keys = [tuple(key) for key in options.get('sorted_groupby_keys', [(0,)])]
        lines = self._build_lines_hierarchy(options_list, financial_line, formula_solver, sorted_groupby_keys)

        return lines

    def _get_table(self, options):
        # OVERRIDE of the _get_table in account.report because the columns are dependent of the data due to the
        # group by feature.
        self.ensure_one()

        options_list = self._get_options_periods_list(options)
        formula_solver = FormulaSolver(options_list, self)
        financial_lines = self.env['account.financial.html.report.line'].search([('id', 'child_of', self.line_ids.ids)])
        formula_solver.fetch_lines(financial_lines)
        groupby_keys = formula_solver.get_keys()
        headers, sorted_groupby_keys = self._build_headers_hierarchy(options_list, groupby_keys)
        lines = self._build_lines_hierarchy(options_list, self.line_ids, formula_solver, sorted_groupby_keys)

        options['sorted_groupby_keys'] = sorted_groupby_keys

        return headers, lines

    @api.model
    def _get_financial_line_report_line(self, options, financial_line, solver, groupby_keys):
        ''' Create the report line for an account.financial.html.report.line record.
        :param options:             The report options.
        :param financial_line:      An account.financial.html.report.line record.
        :param solver_results:      An instance of the FormulaSolver class.
        :param groupby_keys:        The sorted encountered keys in the solver.
        :return:                    The dictionary corresponding to a line to be rendered.
        '''
        results = solver.get_results(financial_line)['formula']

        is_leaf = solver.is_leaf(financial_line)
        has_lines = solver.has_move_lines(financial_line)
        has_something_to_unfold = is_leaf and has_lines and bool(financial_line.groupby)

        # Compute if the line is unfoldable or not.
        is_unfoldable = has_something_to_unfold and financial_line.show_domain == 'foldable'

        # Compute the id of the report line we'll generate
        report_line_id = self._get_generic_line_id('account.financial.html.report.line', financial_line.id)

        # Compute if the line is unfolded or not.
        # /!\ Take care about the case when the line is unfolded but not unfoldable with show_domain == 'always'.
        if not has_something_to_unfold or financial_line.show_domain == 'never':
            is_unfolded = False
        elif financial_line.show_domain == 'always':
            is_unfolded = True
        elif financial_line.show_domain == 'foldable' and report_line_id in options['unfolded_lines']:
            is_unfolded = True
        else:
            is_unfolded = False

        # Standard columns.
        columns = []
        for key in groupby_keys:
            amount = results.get(key, 0.0)
            columns.append({'name': self._format_cell_value(financial_line, amount), 'no_format': amount, 'class': 'number'})

        # Growth comparison column.
        if self._display_growth_comparison(options):
            columns.append(self._compute_growth_comparison_column(options,
                columns[0]['no_format'],
                columns[1]['no_format'],
                green_on_positive=financial_line.green_on_positive
            ))

        financial_report_line = {
            'id': report_line_id,
            'name': financial_line.name,
            'model_ref': ('account.financial.html.report.line', financial_line.id),
            'level': financial_line.level,
            'class': 'o_account_reports_totals_below_sections' if self.env.company.totals_below_sections else '',
            'columns': columns,
            'unfoldable': is_unfoldable,
            'unfolded': is_unfolded,
            'page_break': financial_line.print_on_new_page,
            'action_id': financial_line.action_id.id,
        }

        # Only run the checks in debug mode
        if self.user_has_groups('base.group_no_one'):
            # If a financial line has a control domain, a check is made to detect any potential discrepancy
            if financial_line.control_domain:
                if not financial_line._check_control_domain(options, results, self):
                    # If a discrepancy is found, a check is made to see if the current line is
                    # missing items or has items appearing more than once.
                    has_missing = solver._has_missing_control_domain(options, financial_line)
                    has_excess = solver._has_excess_control_domain(options, financial_line)
                    financial_report_line['has_missing'] = has_missing
                    financial_report_line['has_excess'] = has_excess
                    # In either case, the line is colored in red.
                    # The ids of the missing / excess report lines are stored in the options for the top yellow banner
                    if has_missing:
                        financial_report_line['class'] += ' alert alert-danger'
                        options.setdefault('control_domain_missing_ids', [])
                        options['control_domain_missing_ids'].append(financial_line.id)
                    if has_excess:
                        financial_report_line['class'] += ' alert alert-danger'
                        options.setdefault('control_domain_excess_ids', [])
                        options['control_domain_excess_ids'].append(financial_line.id)

        # Debug info columns.
        if self._display_debug_info(options):
            columns.append(self._compute_debug_info_column(options, solver, financial_line))

        # Custom caret_options for tax report.
        if self.tax_report and financial_line.domain and not financial_line.action_id:
            financial_report_line['caret_options'] = 'tax.report.line'

        return financial_report_line

    @api.model
    def _get_financial_aml_report_line(self, options, financial_report_line_id, financial_line, groupby_id, display_name, results, groupby_keys):
        ''' Create the report line for the account.move.line grouped by any key.
        :param options:                     The report options.
        :param financial_report_line_id:    Generic report line id string for financial_line
        :param financial_line:              An account.financial.html.report.line record.
        :param groupby_id:                  The key used as the vertical group_by. It could be a record's id or a value for regular field.
        :param display_name:                The full name of the line to display.
        :param results:                     The results given by the FormulaSolver class for the given line.
        :param groupby_keys:                The sorted encountered keys in the solver.
        :return:                            The dictionary corresponding to a line to be rendered.
        '''
        # Standard columns.
        columns = []
        for key in groupby_keys:
            amount = results.get(key, 0.0)
            columns.append({'name': self._format_cell_value(financial_line, amount), 'no_format': amount, 'class': 'number'})

        # Growth comparison column.
        if self._display_growth_comparison(options):
            columns.append(self._compute_growth_comparison_column(options,
                columns[0]['no_format'],
                columns[1]['no_format'],
                green_on_positive=financial_line.green_on_positive
            ))

        if self._display_debug_info(options):
            columns.append({'name': '', 'style': 'width: 1%;'})

        groupby_model = self.env['account.move.line']._fields[financial_line.groupby].comodel_name

        return {
            'id': self._get_generic_line_id(groupby_model, groupby_id, parent_line_id=financial_report_line_id),
            'name': display_name,
            'level': financial_line.level + 1,
            'parent_id': financial_report_line_id,
            'caret_options': financial_line.groupby == 'account_id' and 'account.account' or financial_line.groupby,
            'columns': columns,
        }

    @api.model
    def _get_financial_total_section_report_line(self, options, financial_report_line):
        ''' Create the total report line.
        :param options:                 The report options.
        :param financial_report_line:   The line dictionary created by the '_get_financial_line_report_line' method.
        :return:                        The dictionary corresponding to a line to be rendered.
        '''
        return {
            'id': self._get_generic_line_id('account.financial.html.report.line', None, parent_line_id=financial_report_line['id'], markup='total'),
            'name': _('Total') + ' ' + financial_report_line['name'],
            'level': financial_report_line['level'] + 1,
            'parent_id': financial_report_line['id'],
            'class': 'total',
            'columns': financial_report_line['columns'],
        }

    def _get_report_name(self):
        # OVERRIDE
        self.ensure_one()
        return self.name

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    @api.model
    def create(self, vals):
        parent_id = vals.pop('parent_id', False)
        res = super(ReportAccountFinancialReport, self).create(vals)
        res._create_action_and_menu(parent_id)
        return res

    def write(self, vals):
        parent_id = vals.pop('parent_id', False)
        res = super(ReportAccountFinancialReport, self).write(vals)
        if parent_id:
            # this keeps external ids "alive" when upgrading the module
            for report in self:
                report._create_action_and_menu(parent_id)
        return res

    def unlink(self):
        for report in self:
            menu = report.generated_menu_id
            if menu:
                if menu.action:
                    menu.action.unlink()
                menu.unlink()
        return super(ReportAccountFinancialReport, self).unlink()

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        '''Copy the whole financial report hierarchy by duplicating each line recursively.

        :param default: Default values.
        :return: The copied account.financial.html.report record.
        '''
        self.ensure_one()
        if default is None:
            default = {}
        default.update({'name': self._get_copied_name()})
        copied_report_id = super(ReportAccountFinancialReport, self).copy(default=default)
        for line in self.line_ids:
            line._copy_hierarchy(report_id=self, copied_report_id=copied_report_id)
        return copied_report_id

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def action_redirect_to_report(self, options, target_id):
        ''' Action when clicking in a code owned by another report in the debug info popup.

        :param options:     The report options.
        :param target_id:   The target report id.
        :return:            An action opening a new financial report.
        '''
        self.ensure_one()
        action = self.browse(target_id).generated_menu_id.action
        return self.execute_action(options, {'actionId': action.id})

    def _create_action_and_menu(self, parent_id):
        # create action and menu with corresponding external ids, in order to
        # remove those entries when deinstalling the corresponding module
        module = self._context.get('install_module', 'account_reports')
        IMD = self.env['ir.model.data']
        for report in self:
            if not report.generated_menu_id:
                action_vals = {
                    'name': report._get_report_name(),
                    'tag': 'account_report',
                    'context': {
                        'model': 'account.financial.html.report',
                        'id': report.id,
                    },
                }
                action_xmlid = "%s.%s" % (module, 'account_financial_html_report_action_' + str(report.id))
                data = dict(xml_id=action_xmlid, values=action_vals, noupdate=True)
                action = self.env['ir.actions.client'].sudo()._load_records([data])

                menu_vals = {
                    'name': report._get_report_name(),
                    'parent_id': parent_id or IMD._xmlid_to_res_id('account.menu_finance_reports'),
                    'action': 'ir.actions.client,%s' % (action.id,),
                }
                menu_xmlid = "%s.%s" % (module, 'account_financial_html_report_menu_' + str(report.id))
                data = dict(xml_id=menu_xmlid, values=menu_vals, noupdate=True)
                menu = self.env['ir.ui.menu'].sudo()._load_records([data])

                self.write({'generated_menu_id': menu.id})

    def _get_copied_name(self):
        '''Return a copied name of the account.financial.html.report record by adding the suffix (copy) at the end
        until the name is unique.

        :return: an unique name for the copied account.financial.html.report
        '''
        self.ensure_one()
        name = self.name + ' ' + _('(copy)')
        while self.search_count([('name', '=', name)]) > 0:
            name += ' ' + _('(copy)')
        return name

    def _prepare_control_domain_action(self, options, missing=True):
        """ Prepare the report lines, the solver and the action for the control domain buttons.
        Depending on the button used, 'active_ids' will include either the 'control_domain_missing_ids'
        or the 'control_domain_excess_ids'
        :return:    The missing / excess report lines, the solver and the action.
        """

        active_ids = options.get('control_domain_missing_ids') if missing else options.get('control_domain_excess_ids')
        lines = self.env['account.financial.html.report.line'].browse(active_ids)
        options_list = self._get_options_periods_list(options)
        solver = FormulaSolver(options_list, self)
        solver.fetch_lines(lines)

        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_type': 'list',
            'view_mode': 'list',
            'target': 'current',
            'views': [[self.env.ref('account.view_move_line_tree').id, 'list']],
            'domain': self._get_options_domain(options),
            'context': {
                **self._set_context(options),
                'group_by': 'account_id',
            },
        }

        return lines, solver, action

    def open_control_domain_missing(self, options, params=None):
        """ Action when clicking the link on the banner at the top that is shown
        when the control domain check fails because of missing journal items.
        :return:    A tree view with the missing items.
        """
        self.ensure_one()

        lines, solver, action = self._prepare_control_domain_action(options)
        action['domain'] += expression.OR([solver._get_missing_control_domain(options, line) for line in lines])
        action['name'] = _('Missing Journal Items')

        return action

    def open_control_domain_excess(self, options, params=None):
        """ Action when clicking the link on the banner at the top that is shown
        when the control domain check fails because of missing journal items.
        :return:    A tree view with the excess items.
        """
        self.ensure_one()

        lines, solver, action = self._prepare_control_domain_action(options, missing=False)
        action['domain'] += expression.OR([solver._get_excess_control_domain(options, line) for line in lines])
        action['name'] = _('Excess Journal Items')

        return action


class AccountFinancialReportLine(models.Model):
    _name = "account.financial.html.report.line"
    _description = "Account Report (HTML Line)"
    _order = "sequence"
    _parent_store = True

    name = fields.Char('Section Name', translate=True)
    code = fields.Char('Code')
    financial_report_id = fields.Many2one('account.financial.html.report', 'Financial Report')
    parent_id = fields.Many2one('account.financial.html.report.line', string='Parent', ondelete='cascade')
    children_ids = fields.One2many('account.financial.html.report.line', 'parent_id', string='Children')
    parent_path = fields.Char(index=True)
    sequence = fields.Integer()

    domain = fields.Char(default=None)
    control_domain = fields.Char(default=None, help='Specify a control domain that will raise a warning if the report line is not computed correctly.')
    formulas = fields.Char()
    groupby = fields.Char("Group by")
    figure_type = fields.Selection([('float', 'Float'), ('percents', 'Percents'), ('no_unit', 'No Unit')],
                                   'Type', default='float', required=True)
    print_on_new_page = fields.Boolean('Print On New Page', help='When checked this line and everything after it will be printed on a new page.')
    green_on_positive = fields.Boolean('Is growth good when positive', default=True)
    level = fields.Integer(required=True)
    special_date_changer = fields.Selection([
        ('from_beginning', 'From the beginning'),
        ('to_beginning_of_period', 'At the beginning of the period'),
        ('normal', 'Use the dates that should normally be used, depending on the account types'), # So, the start of the accounting if include_initial_balance is True on the account type
        ('strict_range', 'Force given dates for all accounts and account types'),
        ('from_fiscalyear', 'From the beginning of the fiscal year'),
    ], default='normal')
    show_domain = fields.Selection([('always', 'Always'), ('never', 'Never'), ('foldable', 'Foldable')], default='foldable')
    hide_if_zero = fields.Boolean(default=False)
    hide_if_empty = fields.Boolean(default=False)
    action_id = fields.Many2one('ir.actions.actions')

    _sql_constraints = [
        ('code_uniq', 'unique (code)', "A report line with the same code already exists."),
    ]

    # -------------------------------------------------------------------------
    # CONSTRAINS
    # -------------------------------------------------------------------------

    @api.constrains('code', 'groupby', 'formulas')
    def _check_line_consistency(self):
        AccountMoveLine = self.env['account.move.line']

        for rec in self:
            # Check 'code' must not be a protected keyword.
            if rec.code:
                protected_codes = set(dir(__builtins__)).union(set(PROTECTED_KEYWORDS))
                if rec.code and rec.code.strip().lower() in protected_codes:
                    raise ValidationError("The code '%s' is invalid on line with name '%s'") % (rec.code, rec.name)

            # Check 'groupby' must be a valid field.
            if rec.groupby:
                groupby_field = AccountMoveLine._fields.get(rec.groupby)
                if not groupby_field or not self.env['account.financial.html.report']._is_allowed_groupby_field(groupby_field):
                    raise ValidationError(_("Groupby field %s is invalid on line with name '%s'") % (rec.groupby, rec.name))

            # Make sure groupby is specified in conjunction with 'sum_if_pos_groupby' or 'sum_if_neg_groupby'
            if rec.formulas:
                if any(key in rec.formulas for key in ('sum_if_pos_groupby', 'sum_if_neg_groupby')) and not rec.groupby:
                    raise ValidationError(_("Please specify a Group by field when using '%s' in Formulas, on line with name '%s'")
                                          % (rec.formulas, rec.name))

    @api.constrains('domain')
    def _validate_domain(self):
        error_format = _("Error while validating the domain of line %s:\n%s")
        for record in self.filtered('domain'):
            try:
                domain = record._get_domain({}, record._get_financial_report())
                expression.expression(domain, self.env['account.move.line'])
            except Exception as e:
                raise ValidationError(error_format % (record.name, str(e)))

    # -------------------------------------------------------------------------
    # OPTIONS
    # -------------------------------------------------------------------------

    def _get_options_financial_line(self, options, calling_financial_report, parent_financial_report):
        ''' Create a new options specific to one financial line.
        :param options:                     The report options.
        :param calling_financial_report:    The financial report called by the user to be rendered.
        :param parent_financial_report:     The financial report owning the current financial report line that need to
                                            be evaluated by the solver.
        :return:                            The report options adapted to the financial line.
        '''
        self.ensure_one()

        # Make sure to adapt the options if the current report is not the one owning the current financial report line.
        # This is necessary when the 'date' filter mode is not the same in both reports. For example, some P&L lines
        # are used in some balance sheet formulas. However, the balance sheet is a single-date mode report but not the
        # P&L.
        if parent_financial_report and calling_financial_report != parent_financial_report:
            new_options = parent_financial_report._get_options(previous_options=options)

            # Propate the 'ir_filters' manually because 'applicable_filters_ids' could be different
            # in both reports. In that case, we need to propagate it whatever the configuration.
            if options.get('ir_filters'):
                new_options['ir_filters'] = options['ir_filters']

            options = new_options

        new_options = options.copy()
        new_options['date'] = options['date'].copy()
        date_from = options['date']['date_from']
        date_to = options['date']['date_to']
        if self.special_date_changer == 'strict_range':
            new_options['date']['strict_range'] = True
        elif self.special_date_changer == 'from_beginning':
            new_options['date']['date_from'] = False
        elif self.special_date_changer == 'to_beginning_of_period':
            date_tmp = fields.Date.from_string(date_from) - relativedelta(days=1)
            date_to = date_tmp.strftime('%Y-%m-%d')
            new_options['date'].update({'date_from': False, 'date_to': date_to, 'strict_range': False})
        elif self.special_date_changer == 'from_fiscalyear':
            date_tmp = fields.Date.from_string(date_to)
            date_tmp = self.env.company.compute_fiscalyear_dates(date_tmp)['date_from']
            date_from = date_tmp.strftime('%Y-%m-%d')
            new_options['date'].update({'date_from': date_from, 'date_to': date_to, 'strict_range': True, 'mode': 'range'})
        return new_options

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _get_financial_report(self):
        ''' Retrieve the financial report owning the current line.
        The current financial report you are rendering is not always the report owning the
        lines as you could reference a line in a formula coming from another report.

        :return: An account.financial.html.report record.
        '''
        self.ensure_one()
        line = self
        financial_report = False
        while not financial_report:
            financial_report = line.financial_report_id
            if not line.parent_id:
                break
            line = line.parent_id
        return financial_report

    def _get_domain(self, options, financial_report):
        ''' Get the domain to be applied on the current line.
        :return: A valid domain to apply on the account.move.line model.
        '''
        self.ensure_one()

        # Domain defined on the line.
        domain = self.domain and ast.literal_eval(ustr(self.domain)) or []

        # Take care of the tax exigibility.
        # /!\ Still needed as there are still some custom tax reports in localizations.
        if financial_report.tax_report:
            domain += self.env['account.move.line']._get_tax_exigible_domain()

        return domain

    # -------------------------------------------------------------------------
    # QUERIES
    # -------------------------------------------------------------------------

    def _compute_amls_results(self, options_list, calling_financial_report, sign=1):
        ''' Compute the results for the unfolded lines by taking care about the line order and the group by filter.

        Suppose the line has '-sum' as formulas with 'partner_id' in groupby and 'currency_id' in group by filter.
        The result will be something like:
        [
            (0, 'partner 0', {(0,1): amount1, (0,2): amount2, (1,1): amount3}),
            (1, 'partner 1', {(0,1): amount4, (0,2): amount5, (1,1): amount6}),
            ...               |
        ]    |                |
             |__ res.partner ids
                              |_ key where the first element is the period number, the second one being a res.currency id.

        :param options_list:                The report options list, first one being the current dates range, others
                                            being the comparisons.
        :param calling_financial_report:    The financial report called by the user to be rendered.
        :param sign:                        1 or -1 to get negative values in case of '-sum' formula.
        :return:                            A list (groupby_key, display_name, {key: <balance>...}).
        '''
        self.ensure_one()
        params = []
        queries = []

        AccountFinancialReportHtml = self.financial_report_id
        horizontal_groupby_list = AccountFinancialReportHtml._get_options_groupby_fields(options_list[0])
        groupby_list = [self.groupby] + horizontal_groupby_list
        groupby_clause = ','.join('account_move_line.%s' % gb for gb in groupby_list)
        groupby_field = self.env['account.move.line']._fields[self.groupby]

        ct_query = self.env['res.currency']._get_query_currency_table(options_list[0])
        parent_financial_report = self._get_financial_report()

        # Prepare a query by period as the date is different for each comparison.

        for i, options in enumerate(options_list):
            new_options = self._get_options_financial_line(options, calling_financial_report, parent_financial_report)
            line_domain = self._get_domain(new_options, parent_financial_report)

            tables, where_clause, where_params = AccountFinancialReportHtml._query_get(new_options, domain=line_domain)

            queries.append('''
                SELECT
                    ''' + (groupby_clause and '%s,' % groupby_clause) + '''
                    %s AS period_index,
                    COALESCE(SUM(ROUND(%s * account_move_line.balance * currency_table.rate, currency_table.precision)), 0.0) AS balance
                FROM ''' + tables + '''
                JOIN ''' + ct_query + ''' ON currency_table.company_id = account_move_line.company_id
                WHERE ''' + where_clause + '''
                ''' + (groupby_clause and 'GROUP BY %s' % groupby_clause) + '''
            ''')
            params += [i, sign] + where_params

        # Fetch the results.
        # /!\ Take care of both vertical and horizontal group by clauses.

        results = {}

        self._cr.execute(' UNION ALL '.join(queries), params)
        for res in self._cr.dictfetchall():
            # Build the key.
            key = [res['period_index']]
            for gb in horizontal_groupby_list:
                key.append(res[gb])
            key = tuple(key)

            results.setdefault(res[self.groupby], {})
            results[res[self.groupby]][key] = res['balance']

        # Sort the lines according to the vertical groupby and compute their display name.
        if groupby_field.relational:
            # Preserve the table order by using search instead of browse.
            sorted_records = self.env[groupby_field.comodel_name].search([('id', 'in', tuple(results.keys()))])
            sorted_values = sorted_records.name_get()
        else:
            # Sort the keys in a lexicographic order.
            sorted_values = [(v, v) for v in sorted(list(results.keys()))]

        return [(groupby_key, display_name, results[groupby_key]) for groupby_key, display_name in sorted_values]

    def _compute_control_domain(self, options_list, calling_financial_report):
        """ Run an SQL query to fetch the results from the control domain.

        :param calling_financial_report:    The financial report called by the user to be rendered.
        :return:                            A dictionary with he total for each period.
        """

        self.ensure_one()
        params = []
        queries = []

        parent_financial_report = self._get_financial_report()
        groupby_list = parent_financial_report._get_options_groupby_fields(options_list[0])
        groupby_clause = ','.join('account_move_line.%s' % gb for gb in groupby_list)

        ct_query = self.env['res.currency']._get_query_currency_table(options_list[0])

        # Prepare a query by period as the date is different for each comparison.

        for i, options in enumerate(options_list):
            new_options = self._get_options_financial_line(options, calling_financial_report, parent_financial_report)
            control_domain = self.control_domain and ast.literal_eval(ustr(self.control_domain)) or []

            tables, where_clause, where_params = parent_financial_report._query_get(new_options, domain=control_domain)

            queries.append(f'''
                SELECT
                    {groupby_clause and f'{groupby_clause},'} %s AS period_index,
                    COALESCE(SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)), 0.0) AS balance
                FROM {tables}
                JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                WHERE {where_clause}
                {groupby_clause and f'GROUP BY {groupby_clause}'}
            ''')
            params.append(i)
            params += where_params

        # Fetch the results.

        results = {}
        parent_financial_report._cr.execute(' UNION ALL '.join(queries), params)

        for res in self._cr.dictfetchall():
            # Build the key and save the balance
            key = [res['period_index']]
            for gb in groupby_list:
                key.append(res[gb])
            key = tuple(key)

            results[key] = res['balance']

        return results

    def _check_control_domain(self, options, results, calling_financial_report):
        """ Compare values from the solver with those from the control domain.
        :param calling_financial_report:    The financial report called by the user to be rendered.
        :return:                            False if values do not match.
        """

        options_list = self.env['account.report']._get_options_periods_list(options)
        results_control = self._compute_control_domain(options_list, calling_financial_report)
        company_round = self.env.company.currency_id.round

        # Values are compared in absolute terms since they are coming from different sources :
        # - Values in 'results' come from the Solver. Their sign is formatted based on how it should be displayed.
        # - Values in 'results_control' are raw.
        # The sign does not matter in this case, just that the (absolute) values are the same to pass the test.
        return all(
            abs(company_round(results_control[key])) == abs(company_round(results[key]))
            for key in results_control
        )

    def _compute_sum(self, options_list, calling_financial_report):
        ''' Compute the values to be used inside the formula for the current line.
        If called, it means the current line formula contains something making its line a leaf ('sum' or 'count_rows')
        for example.

        The results is something like:
        {
            'sum':                  {key: <balance>...},
            'sum_if_pos':           {key: <balance>...},
            'sum_if_pos_groupby':   {key: <balance>...},
            'sum_if_neg':           {key: <balance>...},
            'sum_if_neg_groupby':   {key: <balance>...},
            'count_rows':           {period_index: <number_of_rows_in_period>...},
        }

        ... where:
        'period_index' is the number of the period, 0 being the current one, others being comparisons.

        'key' is a composite key containing the period_index and the additional group by enabled on the financial report.
        For example, suppose a group by 'partner_id':

        The keys could be something like (0,1), (1,2), (1,3), meaning:
        * (0,1): At the period 0, the results for 'partner_id = 1' are...
        * (1,2): At the period 1 (first comparison), the results for 'partner_id = 2' are...
        * (1,3): At the period 1 (first comparison), the results for 'partner_id = 3' are...

        :param options_list:                The report options list, first one being the current dates range, others
                                            being the comparisons.
        :param calling_financial_report:    The financial report called by the user to be rendered.
        :return:                            A python dictionary.
        '''
        self.ensure_one()
        params = []
        queries = []

        AccountFinancialReportHtml = self.financial_report_id
        groupby_list = AccountFinancialReportHtml._get_options_groupby_fields(options_list[0])
        all_groupby_list = groupby_list.copy()
        groupby_in_formula = any(x in (self.formulas or '') for x in ('sum_if_pos_groupby', 'sum_if_neg_groupby'))
        if groupby_in_formula and self.groupby and self.groupby not in all_groupby_list:
            all_groupby_list.append(self.groupby)
        groupby_clause = ','.join('account_move_line.%s' % gb for gb in all_groupby_list)

        ct_query = self.env['res.currency']._get_query_currency_table(options_list[0])
        parent_financial_report = self._get_financial_report()

        # Prepare a query by period as the date is different for each comparison.

        for i, options in enumerate(options_list):
            new_options = self._get_options_financial_line(options, calling_financial_report, parent_financial_report)
            line_domain = self._get_domain(new_options, parent_financial_report)

            tables, where_clause, where_params = AccountFinancialReportHtml._query_get(new_options, domain=line_domain)

            queries.append('''
                SELECT
                    ''' + (groupby_clause and '%s,' % groupby_clause) + ''' %s AS period_index,
                    COUNT(DISTINCT account_move_line.''' + (self.groupby or 'id') + ''') AS count_rows,
                    COALESCE(SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)), 0.0) AS balance
                FROM ''' + tables + '''
                JOIN ''' + ct_query + ''' ON currency_table.company_id = account_move_line.company_id
                WHERE ''' + where_clause + '''
                ''' + (groupby_clause and 'GROUP BY %s' % groupby_clause) + '''
            ''')
            params.append(i)
            params += where_params

        # Fetch the results.

        results = {
            'sum': {},
            'sum_if_pos': {},
            'sum_if_pos_groupby': {},
            'sum_if_neg': {},
            'sum_if_neg_groupby': {},
            'count_rows': {},
        }

        self._cr.execute(' UNION ALL '.join(queries), params)
        for res in self._cr.dictfetchall():
            # Build the key.
            key = [res['period_index']]
            for gb in groupby_list:
                key.append(res[gb])
            key = tuple(key)

            # Compute values.
            results['count_rows'].setdefault(res['period_index'], 0)
            results['count_rows'][res['period_index']] += res['count_rows']
            results['sum'][key] = res['balance']
            if results['sum'][key] > 0:
                results['sum_if_pos'][key] = results['sum'][key]
                results['sum_if_pos_groupby'].setdefault(key, 0.0)
                results['sum_if_pos_groupby'][key] += res['balance']
            if results['sum'][key] < 0:
                results['sum_if_neg'][key] = results['sum'][key]
                results['sum_if_neg_groupby'].setdefault(key, 0.0)
                results['sum_if_neg_groupby'][key] += res['balance']

        return results

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def _get_copied_code(self):
        '''Look for an unique copied code.

        :return: an unique code for the copied account.financial.html.report.line
        '''
        self.ensure_one()
        code = self.code + '_COPY'
        while self.search_count([('code', '=', code)]) > 0:
            code += '_COPY'
        return code

    def _copy_hierarchy(self, report_id=None, copied_report_id=None, parent_id=None, code_mapping=None):
        ''' Copy the whole hierarchy from this line by copying each line children recursively and adapting the
        formulas with the new copied codes.

        :param report_id: The financial report that triggered the duplicate.
        :param copied_report_id: The copy of old_report_id.
        :param parent_id: The parent line in the hierarchy (a copy of the original parent line).
        :param code_mapping: A dictionary keeping track of mapping old_code -> new_code
        '''
        self.ensure_one()
        if code_mapping is None:
            code_mapping = {}
        # If the line points to the old report, replace with the new one.
        # Otherwise, cut the link to another financial report.
        if report_id and copied_report_id and self.financial_report_id.id == report_id.id:
            financial_report_id = copied_report_id.id
        else:
            financial_report_id = None
        copy_line_id = self.copy({
            'financial_report_id': financial_report_id,
            'parent_id': parent_id and parent_id.id,
            'code': self.code and self._get_copied_code(),
        })
        # Keep track of old_code -> new_code in a mutable dict
        if self.code:
            code_mapping[self.code] = copy_line_id.code
        # Copy children
        for line in self.children_ids:
            line._copy_hierarchy(parent_id=copy_line_id, code_mapping=code_mapping)
        # Update formulas
        if self.formulas:
            copied_formulas = self.formulas
            for k, v in code_mapping.items():
                for field in ('debit', 'credit', 'balance'):
                    suffix = '.' + field
                    copied_formulas = copied_formulas.replace(k + suffix, v + suffix)
            copy_line_id.formulas = copied_formulas

    def action_view_journal_entries(self, options, calling_financial_report_id):
        ''' Action when clicking on the "View Journal Items" in the debug info popup.

        :param options:                     The report options.
        :param calling_financial_report_id: The financial report's id called by the user to be rendered.
        :return:                            An action showing the account.move.lines for the current financial report
                                            line.
        '''
        self.ensure_one()
        parent_financial_report = self._get_financial_report()
        calling_financial_report = self.env['account.financial.html.report'].browse(calling_financial_report_id)
        new_options = self._get_options_financial_line(options, calling_financial_report, parent_financial_report)
        domain = self._get_domain(new_options, parent_financial_report) + parent_financial_report._get_options_domain(new_options)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Items'),
            'res_model': 'account.move.line',
            'view_type': 'list',
            'view_mode': 'list',
            'target': 'current',
            'views': [[self.env.ref('account.view_move_line_tree').id, 'list']],
            'domain': domain,
            'context': {**parent_financial_report._set_context(options)},
        }

    def action_view_coa(self, options):
        """ Action when clicking on the "Accounts" button in the debug info popup."""
        self.ensure_one()

        options_list = self._get_financial_report()._get_options_periods_list(options)
        solver = FormulaSolver(options_list, self)
        solver.fetch_lines(self)

        missing_amls = solver._get_missing_control_domain(options, self)
        excess_amls = solver._get_excess_control_domain(options, self)
        amls = self.env['account.move.line'].search(expression.OR([missing_amls + excess_amls]))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Chart of Accounts'),
            'res_model': 'account.account',
            'view_mode': 'tree',
            'limit': 99999999,
            'search_view_id': [self.env.ref('account.view_account_search').id],
            'views': [[self.env.ref('account_reports.view_account_coa').id, 'list']],
            'domain': [('id', 'in', amls.mapped('account_id.id'))],
        }

    def action_view_line_computation(self):
        """ Action when clicking on the "Report Line Computation" button in the debug info popup."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Computation: %s', self.name),
            'res_model': 'account.financial.html.report.line',
            'view_mode': 'form',
            'views': [[False, 'form']],
            'target': 'new',
            'res_id': self.id,
            'context': {'create': False},
        }

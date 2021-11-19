# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import ast
import copy
import datetime
import io
import json
import logging
import markupsafe
from collections import defaultdict
from math import copysign, inf

import lxml.html
from babel.dates import get_quarter_names
from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import models, fields, api, _
from odoo.addons.web.controllers.main import clean_action
from odoo.exceptions import RedirectWarning
from odoo.osv import expression
from odoo.tools import config, date_utils, get_lang
from odoo.tools.misc import formatLang, format_date
from odoo.tools.misc import xlsxwriter

_logger = logging.getLogger(__name__)


class AccountReportManager(models.Model):
    _name = 'account.report.manager'
    _description = 'Manage Summary and Footnotes of Reports'

    # must work with multi-company, in case of multi company, no company_id defined
    report_name = fields.Char(required=True, help='name of the model of the report')
    summary = fields.Char()
    footnotes_ids = fields.One2many('account.report.footnote', 'manager_id')
    company_id = fields.Many2one('res.company')
    financial_report_id = fields.Many2one('account.financial.html.report')

    def add_footnote(self, text, line):
        return self.env['account.report.footnote'].create({'line': line, 'text': text, 'manager_id': self.id})

class AccountReportFootnote(models.Model):
    _name = 'account.report.footnote'
    _description = 'Account Report Footnote'

    text = fields.Char()
    line = fields.Char(index=True)
    manager_id = fields.Many2one('account.report.manager')

class AccountReport(models.AbstractModel):
    _name = 'account.report'
    _description = 'Account Report'

    MAX_LINES = 80
    filter_multi_company = True
    filter_date = None
    filter_all_entries = None
    filter_comparison = None
    filter_journals = None
    filter_analytic = None
    filter_unfold_all = None
    filter_hierarchy = None
    filter_partner = None
    filter_fiscal_position = None
    order_selected_column = None

    ####################################################
    # OPTIONS: journals
    ####################################################

    @api.model
    def _get_filter_journals(self):
        return self.env['account.journal'].with_context(active_test=False).search([
            ('company_id', 'in', self.env.user.company_ids.ids or [self.env.company.id])
        ], order="company_id, name")

    @api.model
    def _get_filter_journal_groups(self):
        journals = self._get_filter_journals()
        groups = self.env['account.journal.group'].search([], order='sequence')
        ret = self.env['account.journal.group']
        for journal_group in groups:
            # Only display the group if it doesn't exclude every journal
            if journals - journal_group.excluded_journal_ids:
                ret += journal_group
        return ret

    def _init_filter_journals(self, options, previous_options=None):
        if self.filter_journals is None:
            return

        previous_company = False
        if previous_options and previous_options.get('journals'):
            journal_map = dict((opt['id'], opt['selected']) for opt in previous_options['journals'] if opt['id'] != 'divider' and 'selected' in opt)
        else:
            journal_map = {}
        options['journals'] = []

        group_header_displayed = False
        default_group_ids = []
        for group in self._get_filter_journal_groups():
            journal_ids = (self._get_filter_journals() - group.excluded_journal_ids).ids
            if len(journal_ids):
                if not group_header_displayed:
                    group_header_displayed = True
                    options['journals'].append({'id': 'divider', 'name': _('Journal Groups')})
                    default_group_ids = journal_ids
                options['journals'].append({'id': 'group', 'name': group.name, 'ids': journal_ids})

        for j in self._get_filter_journals():
            if j.company_id != previous_company:
                options['journals'].append({'id': 'divider', 'name': j.company_id.name})
                previous_company = j.company_id
            options['journals'].append({
                'id': j.id,
                'name': j.name,
                'code': j.code,
                'type': j.type,
                'selected': journal_map.get(j.id, j.id in default_group_ids),
            })

    @api.model
    def _get_options_journals(self, options):
        return [
            journal for journal in options.get('journals', []) if
            not journal['id'] in ('divider', 'group') and journal['selected']
        ]

    @api.model
    def _get_options_journals_domain(self, options):
        # Make sure to return an empty array when nothing selected to handle archived journals.
        selected_journals = self._get_options_journals(options)
        return selected_journals and [('journal_id', 'in', [j['id'] for j in selected_journals])] or []

    ####################################################
    # OPTIONS: date + comparison
    ####################################################

    @api.model
    def _get_options_periods_list(self, options):
        ''' Get periods as a list of options, one per impacted period.
        The first element is the range of dates requested in the report, others are the comparisons.

        :param options: The report options.
        :return:        A list of options having size 1 + len(options['comparison']['periods']).
        '''
        periods_options_list = []
        if options.get('date'):
            periods_options_list.append(options)
        if options.get('comparison') and options['comparison'].get('periods'):
            for period in options['comparison']['periods']:
                period_options = options.copy()
                period_options['date'] = period
                periods_options_list.append(period_options)
        return periods_options_list

    @api.model
    def _get_dates_period(self, options, date_from, date_to, mode, period_type=None, strict_range=False):
        '''Compute some information about the period:
        * The name to display on the report.
        * The period type (e.g. quarter) if not specified explicitly.
        :param date_from:   The starting date of the period.
        :param date_to:     The ending date of the period.
        :param period_type: The type of the interval date_from -> date_to.
        :return:            A dictionary containing:
            * date_from * date_to * string * period_type * mode *
        '''
        def match(dt_from, dt_to):
            return (dt_from, dt_to) == (date_from, date_to)

        string = None
        # If no date_from or not date_to, we are unable to determine a period
        if not period_type or period_type == 'custom':
            date = date_to or date_from
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date)
            if match(company_fiscalyear_dates['date_from'], company_fiscalyear_dates['date_to']):
                period_type = 'fiscalyear'
                if company_fiscalyear_dates.get('record'):
                    string = company_fiscalyear_dates['record'].name
            elif match(*date_utils.get_month(date)):
                period_type = 'month'
            elif match(*date_utils.get_quarter(date)):
                period_type = 'quarter'
            elif match(*date_utils.get_fiscal_year(date)):
                period_type = 'year'
            elif match(date_utils.get_month(date)[0], fields.Date.today()):
                period_type = 'today'
            else:
                period_type = 'custom'
        elif period_type == 'fiscalyear':
            date = date_to or date_from
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date)
            record = company_fiscalyear_dates.get('record')
            string = record and record.name

        if not string:
            fy_day = self.env.company.fiscalyear_last_day
            fy_month = int(self.env.company.fiscalyear_last_month)
            if mode == 'single':
                string = _('As of %s') % (format_date(self.env, fields.Date.to_string(date_to)))
            elif period_type == 'year' or (
                    period_type == 'fiscalyear' and (date_from, date_to) == date_utils.get_fiscal_year(date_to)):
                string = date_to.strftime('%Y')
            elif period_type == 'fiscalyear' and (date_from, date_to) == date_utils.get_fiscal_year(date_to, day=fy_day, month=fy_month):
                string = '%s - %s' % (date_to.year - 1, date_to.year)
            elif period_type == 'month':
                string = format_date(self.env, fields.Date.to_string(date_to), date_format='MMM yyyy')
            elif period_type == 'quarter':
                quarter_names = get_quarter_names('abbreviated', locale=get_lang(self.env).code)
                string = u'%s\N{NO-BREAK SPACE}%s' % (
                    quarter_names[date_utils.get_quarter_number(date_to)], date_to.year)
            else:
                dt_from_str = format_date(self.env, fields.Date.to_string(date_from))
                dt_to_str = format_date(self.env, fields.Date.to_string(date_to))
                string = _('From %s\nto  %s') % (dt_from_str, dt_to_str)

        return {
            'string': string,
            'period_type': period_type,
            'mode': mode,
            'strict_range': strict_range,
            'date_from': date_from and fields.Date.to_string(date_from) or False,
            'date_to': fields.Date.to_string(date_to),
        }

    @api.model
    def _get_dates_previous_period(self, options, period_vals):
        '''Shift the period to the previous one.
        :param period_vals: A dictionary generated by the _get_dates_period method.
        :return:            A dictionary containing:
            * date_from * date_to * string * period_type *
        '''
        period_type = period_vals['period_type']
        mode = period_vals['mode']
        strict_range = period_vals.get('strict_range', False)
        date_from = fields.Date.from_string(period_vals['date_from'])
        date_to = date_from - datetime.timedelta(days=1)

        if period_type == 'fiscalyear':
            # Don't pass the period_type to _get_dates_period to be able to retrieve the account.fiscal.year record if
            # necessary.
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date_to)
            return self._get_dates_period(options, company_fiscalyear_dates['date_from'], company_fiscalyear_dates['date_to'], mode, strict_range=strict_range)
        if period_type in ('month', 'today', 'custom'):
            return self._get_dates_period(options, *date_utils.get_month(date_to), mode, period_type='month', strict_range=strict_range)
        if period_type == 'quarter':
            return self._get_dates_period(options, *date_utils.get_quarter(date_to), mode, period_type='quarter', strict_range=strict_range)
        if period_type == 'year':
            return self._get_dates_period(options, *date_utils.get_fiscal_year(date_to), mode, period_type='year', strict_range=strict_range)
        return None

    @api.model
    def _get_dates_previous_year(self, options, period_vals):
        '''Shift the period to the previous year.
        :param options:     The report options.
        :param period_vals: A dictionary generated by the _get_dates_period method.
        :return:            A dictionary containing:
            * date_from * date_to * string * period_type *
        '''
        period_type = period_vals['period_type']
        mode = period_vals['mode']
        strict_range = period_vals.get('strict_range', False)
        date_from = fields.Date.from_string(period_vals['date_from'])
        date_from = date_from - relativedelta(years=1)
        date_to = fields.Date.from_string(period_vals['date_to'])
        date_to = date_to - relativedelta(years=1)

        if period_type == 'month':
            date_from, date_to = date_utils.get_month(date_to)
        return self._get_dates_period(options, date_from, date_to, mode, period_type=period_type, strict_range=strict_range)

    def _init_filter_date(self, options, previous_options=None):
        """ Initialize the 'date' options key.

        :param options:             The current report options to build.
        :param previous_options:    The previous options coming from another report.
        """
        if self.filter_date is None:
            return

        previous_date = (previous_options or {}).get('date', {})
        previous_date_to = previous_date.get('date_to')
        previous_date_from = previous_date.get('date_from')
        previous_mode = previous_date.get('mode')
        previous_filter = previous_date.get('filter', 'custom')

        default_filter = self.filter_date['filter']
        options_mode = self.filter_date['mode']
        options_strict_range = self.filter_date.get('strict_range', False)
        date_from = date_to = period_type = False

        if previous_mode == 'single' and options_mode == 'range':
            # 'single' date mode to 'range'.

            if previous_filter == 'custom':
                date_to = fields.Date.from_string(previous_date_to or previous_date_from)
                date_from = self.env.company.compute_fiscalyear_dates(date_to)['date_from']
                options_filter = 'custom'
            elif previous_filter == 'today':
                date_to = fields.Date.context_today(self)
                date_from = date_utils.get_month(date_to)[0]
                options_filter = 'custom'
            elif previous_filter:
                options_filter = previous_filter
            else:
                options_filter = default_filter

        elif previous_mode == 'range' and options_mode == 'single':
            # 'range' date mode to 'single'.

            if previous_filter == 'custom':
                date_to = fields.Date.from_string(previous_date_to or previous_date_from)
                date_from = date_utils.get_month(date_to)[0]
                options_filter = 'custom'
            elif previous_filter:
                options_filter = previous_filter
            else:
                options_filter = default_filter

        elif previous_mode == options_mode:
            # Same date mode.

            if previous_filter == 'custom':
                if options_mode == 'range':
                    date_from = fields.Date.from_string(previous_date_from)
                    date_to = fields.Date.from_string(previous_date_to)
                else:
                    date_to = fields.Date.from_string(previous_date_to or previous_date_from)
                    date_from = date_utils.get_month(date_to)[0]
                options_filter = 'custom'
            else:
                options_filter = previous_filter

        else:
            # Default.
            options_filter = default_filter

        # Compute 'date_from' / 'date_to'.
        if not date_from or not date_to:
            if options_filter == 'today':
                date_to = fields.Date.context_today(self)
                date_from = date_utils.get_month(date_to)[0]
            elif 'month' in options_filter:
                date_from, date_to = date_utils.get_month(fields.Date.context_today(self))
                period_type = 'month'
            elif 'quarter' in options_filter:
                date_from, date_to = date_utils.get_quarter(fields.Date.context_today(self))
                period_type = 'quarter'
            elif 'year' in options_filter:
                company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(fields.Date.context_today(self))
                date_from = company_fiscalyear_dates['date_from']
                date_to = company_fiscalyear_dates['date_to']
            elif options_filter == 'custom':
                custom_date_from = self.filter_date.get('date_from')
                custom_date_to = self.filter_date.get('date_to')
                date_to = fields.Date.from_string(custom_date_to or custom_date_from)
                date_from = fields.Date.from_string(custom_date_from) if custom_date_from else date_utils.get_month(date_to)[0]

        options['date'] = self._get_dates_period(
            options,
            date_from,
            date_to,
            options_mode,
            period_type=period_type,
            strict_range=options_strict_range,
        )
        if 'last' in options_filter:
            options['date'] = self._get_dates_previous_period(options, options['date'])
        options['date']['filter'] = options_filter

    def _init_filter_comparison(self, options, previous_options=None):
        """ Initialize the 'comparison' options key.

        This filter must be loaded after the 'date' filter.

        :param options:             The current report options to build.
        :param previous_options:    The previous options coming from another report.
        """
        if self.filter_comparison is None:
            return

        previous_comparison = (previous_options or {}).get('comparison', {})
        previous_filter = previous_comparison.get('filter')

        default_filter = self.filter_comparison.get('filter', 'no_comparison')
        strict_range = options['date']['strict_range']

        if previous_filter == 'custom':
            # Try to adapt the previous 'custom' filter.
            date_from = previous_comparison.get('date_from')
            date_to = previous_comparison.get('date_to')
            number_period = 1
            options_filter = 'custom'
        elif default_filter == 'custom':
            # Retrieve custom dates given by the user.
            if options['date']['mode'] == 'range':
                date_from = self.filter_comparison['date_from']
                date_to = self.filter_comparison['date_to']
            else:
                date_from = False
                date_to = self.filter_comparison.get('date_to') or self.filter_comparison.get('date_from')
            number_period = 1
            options_filter = 'custom'
        else:
            # Use the 'date' options.
            date_from = options['date']['date_from']
            date_to = options['date']['date_to']
            number_period = previous_comparison.get('number_period') or self.filter_comparison.get('number_period', 1)
            options_filter = previous_filter or default_filter

        options['comparison'] = {
            'filter': options_filter,
            'number_period': number_period,
            'date_from': date_from,
            'date_to': date_to,
            'periods': [],
        }

        date_from_obj = fields.Date.from_string(date_from)
        date_to_obj = fields.Date.from_string(date_to)

        if options_filter == 'custom':
            options['comparison']['periods'].append(self._get_dates_period(
                options,
                date_from_obj,
                date_to_obj,
                options['date']['mode'],
                strict_range=strict_range,
            ))
        elif options_filter in ('previous_period', 'same_last_year'):
            previous_period = options['date']
            for dummy in range(0, number_period):
                if options_filter == 'previous_period':
                    period_vals = self._get_dates_previous_period(options, previous_period)
                elif options_filter == 'same_last_year':
                    period_vals = self._get_dates_previous_year(options, previous_period)
                else:
                    date_from_obj = fields.Date.from_string(date_from)
                    date_to_obj = fields.Date.from_string(date_to)
                    strict_range = previous_period.get('strict_range', False)
                    period_vals = self._get_dates_period(options, date_from_obj, date_to_obj, previous_period['mode'], strict_range=strict_range)
                options['comparison']['periods'].append(period_vals)
                previous_period = period_vals

        if len(options['comparison']['periods']) > 0:
            options['comparison'].update(options['comparison']['periods'][0])

    @api.model
    def _get_options_date_domain(self, options):
        def create_date_domain(options_date):
            date_field = options_date.get('date_field', 'date')
            domain = [(date_field, '<=', options_date['date_to'])]
            if options_date['mode'] == 'range':
                strict_range = options_date.get('strict_range')
                if not strict_range:
                    domain += [
                        '|',
                        (date_field, '>=', options_date['date_from']),
                        ('account_id.user_type_id.include_initial_balance', '=', True)
                    ]
                else:
                    domain += [(date_field, '>=', options_date['date_from'])]
            return domain

        if not options.get('date'):
            return []
        return create_date_domain(options['date'])

    ####################################################
    # OPTIONS: analytic
    ####################################################

    def _init_filter_analytic(self, options, previous_options=None):
        if not self.filter_analytic:
            return

        options['analytic'] = True

        enable_analytic_accounts = self.user_has_groups('analytic.group_analytic_accounting')
        enable_analytic_tags = self.user_has_groups('analytic.group_analytic_tags')
        if not enable_analytic_accounts and not enable_analytic_tags:
            return

        if enable_analytic_accounts:
            previous_analytic_accounts = (previous_options or {}).get('analytic_accounts', [])
            analytic_account_ids = [int(x) for x in previous_analytic_accounts]
            selected_analytic_accounts = self.env['account.analytic.account'].search([('id', 'in', analytic_account_ids)])
            options['analytic_accounts'] = selected_analytic_accounts.ids
            options['selected_analytic_account_names'] = selected_analytic_accounts.mapped('name')

        if enable_analytic_tags:
            previous_analytic_tags = (previous_options or {}).get('analytic_tags', [])
            analytic_tag_ids = [int(x) for x in previous_analytic_tags]
            selected_analytic_tags = self.env['account.analytic.tag'].search([('id', 'in', analytic_tag_ids)])
            options['analytic_tags'] = selected_analytic_tags.ids
            options['selected_analytic_tag_names'] = selected_analytic_tags.mapped('name')

    @api.model
    def _get_options_analytic_domain(self, options):
        domain = []
        if options.get('analytic_accounts'):
            analytic_account_ids = [int(acc) for acc in options['analytic_accounts']]
            domain.append(('analytic_account_id', 'in', analytic_account_ids))
        if options.get('analytic_tags'):
            analytic_tag_ids = [int(tag) for tag in options['analytic_tags']]
            domain.append(('analytic_tag_ids', 'in', analytic_tag_ids))
        return domain

    ####################################################
    # OPTIONS: partners
    ####################################################

    def _init_filter_partner(self, options, previous_options=None):
        if not self.filter_partner:
            return

        options['partner'] = True
        options['partner_ids'] = previous_options and previous_options.get('partner_ids') or []
        options['partner_categories'] = previous_options and previous_options.get('partner_categories') or []
        selected_partner_ids = [int(partner) for partner in options['partner_ids']]
        selected_partners = selected_partner_ids and self.env['res.partner'].browse(selected_partner_ids) or self.env['res.partner']
        options['selected_partner_ids'] = selected_partners.mapped('name')
        selected_partner_category_ids = [int(category) for category in options['partner_categories']]
        selected_partner_categories = selected_partner_category_ids and self.env['res.partner.category'].browse(selected_partner_category_ids) or self.env['res.partner.category']
        options['selected_partner_categories'] = selected_partner_categories.mapped('name')

    @api.model
    def _get_options_partner_domain(self, options):
        domain = []
        if options.get('partner_ids'):
            partner_ids = [int(partner) for partner in options['partner_ids']]
            domain.append(('partner_id', 'in', partner_ids))
        if options.get('partner_categories'):
            partner_category_ids = [int(category) for category in options['partner_categories']]
            domain.append(('partner_id.category_id', 'in', partner_category_ids))
        return domain

    ####################################################
    # OPTIONS: all_entries
    ####################################################

    @api.model
    def _get_options_all_entries_domain(self, options):
        if not options.get('all_entries'):
            return [('move_id.state', '=', 'posted')]
        else:
            return [('move_id.state', '!=', 'cancel')]

    ####################################################
    # OPTIONS: order column
    ####################################################

    @api.model
    def _init_order_selected_column(self, options, previous_options=None):
        if self.order_selected_column is not None:
            options['selected_column'] = previous_options and previous_options.get('selected_column') or self.order_selected_column['default']

    ####################################################
    # OPTIONS: hierarchy
    ####################################################

    def _init_filter_hierarchy(self, options, previous_options=None):
        # Only propose the option if there are groups
        if self.filter_hierarchy is not None and self.env['account.group'].search([('company_id', 'in', self.env.companies.ids)], limit=1):
            if previous_options and 'hierarchy' in previous_options:
                options['hierarchy'] = previous_options['hierarchy']
            else:
                options['hierarchy'] = self.filter_hierarchy

    # Create codes path in the hierarchy based on account.
    def get_account_codes(self, account):
        # A code is tuple(id, name)
        codes = []
        if account.group_id:
            group = account.group_id
            while group:
                codes.append((group.id, group.display_name))
                group = group.parent_id
        else:
            codes.append((0, _('(No Group)')))
        return list(reversed(codes))

    @api.model
    def _create_hierarchy(self, lines, options):
        """Compute the hierarchy based on account groups when the option is activated.

        The option is available only when there are account.group for the company.
        It should be called when before returning the lines to the client/templater.
        The lines are the result of _get_lines(). If there is a hierarchy, it is left
        untouched, only the lines related to an account.account are put in a hierarchy
        according to the account.group's and their prefixes.
        """
        unfold_all = self.env.context.get('print_mode') and len(options.get('unfolded_lines')) == 0 or options.get('unfold_all')

        def add_to_hierarchy(lines, key, level, parent_id, hierarchy):
            val_dict = hierarchy[key]
            unfolded = val_dict['id'] in options.get('unfolded_lines') or unfold_all
            # add the group totals
            lines.append({
                'id': val_dict['id'],
                'name': val_dict['name'],
                'title_hover': val_dict['name'],
                'unfoldable': True,
                'unfolded': unfolded,
                'level': level,
                'parent_id': parent_id,
                'columns': [{'name': self.format_value(c) if isinstance(c, (int, float)) else c, 'no_format_name': c} for c in val_dict['totals']],
            })
            if not self._context.get('print_mode') or unfolded:
                # add every direct child group recursively
                children = []
                for child in sorted(val_dict['children_codes']):
                    add_to_hierarchy(children, child, level + 1, val_dict['id'], hierarchy)
                # add all the lines that are in this group but not in one of this group's children groups
                for l in val_dict['lines']:
                    l['level'] = level + 1
                    l['parent_id'] = val_dict['id']
                lines.extend(sorted(val_dict['lines'] + children, key=lambda k: k.get('account_code', '') + k['name']))

        def compute_hierarchy(lines, level, parent_id):
            # put every line in each of its parents (from less global to more global) and compute the totals
            hierarchy = defaultdict(lambda: {'totals': [None] * len(lines[0]['columns']), 'lines': [], 'children_codes': set(), 'name': '', 'parent_id': None, 'id': ''})
            for line in lines:
                account = self.env['account.account'].browse(line.get('account_id', self._get_caret_option_target_id(line.get('id'))))
                codes = self.get_account_codes(account)  # id, name
                for code in codes:
                    hierarchy[code[0]]['id'] = self._get_generic_line_id('account.group', code[0], parent_line_id=line['id'])
                    hierarchy[code[0]]['name'] = code[1]
                    for i, column in enumerate(line['columns']):
                        if 'no_format_name' in column:
                            no_format = column['no_format_name']
                        elif 'no_format' in column:
                            no_format = column['no_format']
                        else:
                            no_format = None
                        if isinstance(no_format, (int, float)):
                            if hierarchy[code[0]]['totals'][i] is None:
                                hierarchy[code[0]]['totals'][i] = no_format
                            else:
                                hierarchy[code[0]]['totals'][i] += no_format
                for code, child in zip(codes[:-1], codes[1:]):
                    hierarchy[code[0]]['children_codes'].add(child[0])
                    hierarchy[child[0]]['parent_id'] = hierarchy[code[0]]['id']
                hierarchy[codes[-1][0]]['lines'] += [line]
            # compute the tree-like structure by starting at the roots (being groups without parents)
            hierarchy_lines = []
            for root in [k for k, v in hierarchy.items() if not v['parent_id']]:
                add_to_hierarchy(hierarchy_lines, root, level, parent_id, hierarchy)
            return hierarchy_lines

        new_lines = []
        account_lines = []
        current_level = 0
        parent_id = 'root'
        for line in lines:
            if not (line.get('caret_options') == 'account.account' or line.get('account_id')):
                # make the hierarchy with the lines we gathered, append it to the new lines and restart the gathering
                if account_lines:
                    new_lines.extend(compute_hierarchy(account_lines, current_level + 1, parent_id))
                account_lines = []
                new_lines.append(line)
                current_level = line['level']
                parent_id = line['id']
            else:
                # gather all the lines we can create a hierarchy on
                account_lines.append(line)
        # do it one last time for the gathered lines remaining
        if account_lines:
            new_lines.extend(compute_hierarchy(account_lines, current_level + 1, parent_id))
        return new_lines

    ####################################################
    # OPTIONS: fiscal position (multi vat)
    ####################################################

    def _init_filter_fiscal_position(self, options, previous_options=None):
        # Depents from multi_company option
        vat_fpos_domain = [
            ('company_id', 'in', [comp['id'] for comp in options.get('multi_company', self.env.company)]),
            ('foreign_vat', '!=', False),
        ]
        country = self._get_country_for_fiscal_position_filter(options)
        if country:
            vat_fiscal_positions = self.env['account.fiscal.position'].search([
                *vat_fpos_domain,
                ('country_id', '=', country.id),
            ])

            options['allow_domestic'] = self.env.company.account_fiscal_country_id == country

            accepted_prev_vals = {*vat_fiscal_positions.ids}
            if options['allow_domestic']:
                accepted_prev_vals.add('domestic')
            if len(vat_fiscal_positions) > (0 if options['allow_domestic'] else 1) or not accepted_prev_vals:
                accepted_prev_vals.add('all')

            if previous_options and previous_options.get('fiscal_position') in accepted_prev_vals:
                # Legit value from previous options; keep it
                options['fiscal_position'] = previous_options['fiscal_position']
            elif len(vat_fiscal_positions) == 1 and not options['allow_domestic']:
                # Only one foreign fiscal position: always select it, menu will be hidden
                options['fiscal_position'] = vat_fiscal_positions.id
            else:
                # Multiple possible values; by default, show the values of the company's area (if allowed), or everything
                options['fiscal_position'] = options['allow_domestic'] and 'domestic' or 'all'
        else:
            vat_fiscal_positions = []
            options['allow_domestic'] = False
            options['fiscal_position'] = 'all'

        options['available_vat_fiscal_positions'] = [{
            'id': fiscal_pos.id,
            'name': fiscal_pos.name,
            'company_id': fiscal_pos.company_id.id,
        } for fiscal_pos in vat_fiscal_positions]

    def _get_country_for_fiscal_position_filter(self, options):
        """ Gets the country to use to fetch the available foreign VAT fiscal positions for the
        fiscal_position option. By default, this function returns None, meaning that no fiscal position
        will ever be available, and the fiscal_position option is disabled. Subclasses need to override
        it to change that.
        """
        return None

    def _get_options_fiscal_position_domain(self, options):
        fiscal_position_opt = options.get('fiscal_position')

        if fiscal_position_opt == 'domestic':
            return [
                '|',
                ('move_id.fiscal_position_id', '=', False),
                ('move_id.fiscal_position_id.foreign_vat', '=', False),
            ]

        if fiscal_position_opt == 'all':
            return []

        # Else it's a fiscal position id
        return [('move_id.fiscal_position_id', '=', fiscal_position_opt)]

    ####################################################
    # OPTIONS: MULTI COMPANY
    ####################################################

    def _init_filter_multi_company(self, options, previous_options=None):
        if self.filter_multi_company:
            if self._context.get('allowed_company_ids'):
                # Retrieve the companies through the multi-companies widget.
                companies = self.env['res.company'].browse(self._context['allowed_company_ids'])
            else:
                # When called from testing files, 'allowed_company_ids' is missing.
                # Then, give access to all user's companies.
                companies = self.env.companies
            if len(companies) > 1:
                options['multi_company'] = [
                    {'id': c.id, 'name': c.name} for c in companies
                ]

    ####################################################
    # OPTIONS: CORE
    ####################################################

    def _get_options(self, previous_options=None):
        # Create default options.
        options = {
            'unfolded_lines': previous_options and previous_options.get('unfolded_lines') or [],
        }

        for filter_key in self._get_filters_in_init_sequence():
            options_key = filter_key[7:]
            init_func = getattr(self, '_init_%s' % filter_key, None)
            if init_func:
                init_func(options, previous_options=previous_options)
            else:
                filter_opt = getattr(self, filter_key, None)
                if filter_opt is not None:
                    if previous_options and options_key in previous_options:
                        options[options_key] = previous_options[options_key]
                    else:
                        options[options_key] = filter_opt

        return options

    def _get_filters_in_init_sequence(self):
        """ Gets all filters in the right order to initialize them, so that each filters is
        guaranteed to be after all of its dependencies in the resulting list.

        :return: a list of stings, corresponding to the filter names
        """
        # Get all filters
        filter_list = [
            attr for attr in dir(self)
            if (
                (attr.startswith('filter_') or attr.startswith('order_'))
                and len(attr) > 7
                and not callable(getattr(self, attr))
            )
        ]

        # Order them in a dependency-compliant way
        forced_sequence_map = self._get_forced_filter_init_sequence_map()
        filter_list.sort(key=lambda x: forced_sequence_map.get(x, inf))

        return filter_list

    def _get_forced_filter_init_sequence_map(self):
        """ By default, not specific order is ensured for the filters when calling _get_filters_in_init_sequence.
        This function allows giving them a sequence number. It can be overridden
        to make filters depend on each other.

        :return: dict(str, int): str is the filter name, int is its sequence (lowest = first).
                                 Multiple filters may share the same sequence, their relative order is then not guaranteed.
        """
        return {'filter_multi_company': 10, 'filter_fiscal_position': 20, 'filter_date': 30, 'filter_comparison': 40}

    @api.model
    def _get_options_domain(self, options):
        domain = [
            ('display_type', 'not in', ('line_section', 'line_note')),
            ('move_id.state', '!=', 'cancel'),
            ('company_id', 'in', self.get_report_company_ids(options)),
        ]
        domain += self._get_options_journals_domain(options)
        domain += self._get_options_date_domain(options)
        domain += self._get_options_analytic_domain(options)
        domain += self._get_options_partner_domain(options)
        domain += self._get_options_all_entries_domain(options)
        domain += self._get_options_fiscal_position_domain(options)
        return domain

    ####################################################
    # QUERIES
    ####################################################

    @api.model
    def _query_get(self, options, domain=None):
        domain = self._get_options_domain(options) + (domain or [])
        self.env['account.move.line'].check_access_rights('read')

        query = self.env['account.move.line']._where_calc(domain)

        # Wrap the query with 'company_id IN (...)' to avoid bypassing company access rights.
        self.env['account.move.line']._apply_ir_rules(query)

        return query.get_sql()

    ####################################################
    # LINE IDS MANAGEMENT HELPERS
    ####################################################

    def _get_generic_line_id(self, model_name, value, markup='', parent_line_id=None):
        """ Generates a generic line id from the provided parameters.

        Such a generic id consists of a string repating 1 to n times the following pattern:
        markup-model-value, each occurence separated by a | character from the previous one.

        Each pattern corresponds to a level of hierarchy in the report, so that
        the n-1 patterns starting the id of a line actually form the id of its generator line.
        EX: a-b-c|d-e-f|g-h-i => This line is a subline generated by a-b-c|d-e-f

        Each pattern consists of the three following elements:
        - markup:  a (possibly empty) string allowing finer idenfication of the line
                   (like the name of the field for account.accounting.reports)

        - model:   the model this line has been generated for, or an empty string if there is none

        - value:   the groupby value for this line (typically the id of a record
                   or the value of a field), or an empty string if there isn't any.
        """
        parent_id_list = self._parse_line_id(parent_line_id) if parent_line_id else []

        return self._build_line_id(parent_id_list + [(markup, model_name, value)])

    def _get_model_info_from_id(self, line_id):
        """ Parse the provided generic report line id.

        :param line_id: the report line id (i.e. markup-model-value|markup2-model2-value2)
        :return: tuple(model, id) of the report line. Each of those values can be None if the id contains no information about them.
        """
        last_id_tuple = self._parse_line_id(line_id)[-1]
        return last_id_tuple[-2:]

    def _build_line_id(self, current):
        """ Build a generic line id string from its list representation, converting
        the None values for model and value to empty strings.
        :param current (list<tuple>): list of tuple(markup, model, value)
        """
        def convert_none(x):
            return x if x is not None else ''
        return '|'.join('%s-%s-%s' % (markup, convert_none(model), convert_none(value)) for markup, model, value in current)

    def _build_parent_line_id(self, current):
        """Build the parent_line id based on the current position in the report.

        For instance, if current is [(account_id, 5), (partner_id, 8)], it will return
        account_id-5
        :param current (list<tuple>): list of tuple(markup, model, value)
        """
        return self._build_line_id(current[:-1])

    def _parse_line_id(self, line_id):
        """Parse the provided string line id and convert it to its list representation.
        Empty strings for model and value will be converted to None.

        For instance if line_id is account_id-5|partner_id-8, it will return
        [(account_id, 5), (partner_id, 8)]
        :param line_id (str): the id of the line to parse
        """
        return line_id and [
            (markup, model or None, ast.literal_eval(value) if value else None)
            for markup, model, value in (key.split('-') for key in line_id.split('|'))
        ] or []

    ####################################################
    # MISC
    ####################################################

    def get_header(self, options):
        columns = self._get_columns(options)
        if 'selected_column' in options and self.order_selected_column:
            selected_column = columns[0][abs(options['selected_column']) - 1]
            if 'sortable' in selected_column.get('class', ''):
                selected_column['class'] = (options['selected_column'] > 0 and 'up ' or 'down ') + selected_column['class']
        return columns

    # TO BE OVERWRITTEN
    def _get_columns(self, options):
        return [self._get_columns_name(options)]

    # TO BE OVERWRITTEN
    def _get_columns_name(self, options):
        return []

    #TO BE OVERWRITTEN
    def _get_lines(self, options, line_id=None):
        return []

    #TO BE OVERWRITTEN
    def _get_table(self, options):
        return self.get_header(options), self._get_lines(options)

    #TO BE OVERWRITTEN
    def _get_templates(self):
        return {
                'main_template': 'account_reports.main_template',
                'main_table_header_template': 'account_reports.main_table_header',
                'line_template': 'account_reports.line_template',
                'footnotes_template': 'account_reports.footnotes_template',
                'search_template': 'account_reports.search_template',
                'line_caret_options': 'account_reports.line_caret_options',
        }

    #TO BE OVERWRITTEN
    def _get_report_name(self):
        return _('General Report')

    def get_report_filename(self, options):
        """The name that will be used for the file when downloading pdf,xlsx,..."""
        return self._get_report_name().lower().replace(' ', '_')

    def execute_action(self, options, params=None):
        action_id = int(params.get('actionId'))
        action = self.env['ir.actions.actions'].sudo().browse([action_id])
        action_type = action.type
        action = self.env[action.type].sudo().browse([action_id])
        action_read = clean_action(action.read()[0], env=action.env)
        if action_type == 'ir.actions.client':
            # Check if we are opening another report and if yes, pass options and ignore_session
            if action.tag == 'account_report':
                options['unfolded_lines'] = []
                options['unfold_all'] = False
                action_read.update({'params': {'options': options, 'ignore_session': 'read'}})
        if params.get('id'):
            # Add the id of the calling object in the action's context

            if isinstance(params['id'], int):
                # id of the report line might directly be the id of the model we want.
                model_id = params['id']
            else:
                # It can also be a generic account.report id, as defined by _get_generic_line_id
                model_id = self._get_model_info_from_id(params['id'])[1]

            context = action_read.get('context') and ast.literal_eval(action_read['context']) or {}
            context.setdefault('active_id', model_id)
            action_read['context'] = context
        return action_read

    @api.model
    def _resolve_caret_option_document(self, model, res_id, document):
        '''Retrieve the target record of the caret option.

        :param model:       The source model of the report line, 'account.move.line' by default.
        :param res_id:      The source id of the report line.
        :param document:    The target model of the redirection.
        :return: The target record.
        '''
        if model == document:
            return self.env[model].browse(res_id)

        if model == 'account.move':
            if document == 'res.partner':
                return self.env[model].browse(res_id).partner_id.commercial_partner_id
        elif model == 'account.bank.statement.line':
            if document == 'account.bank.statement':
                return self.env[model].browse(res_id).statement_id

        # model == 'account.move.line' by default.
        if document == 'account.move':
            return self.env[model].browse(res_id).move_id
        if document == 'account.payment':
            return self.env[model].browse(res_id).payment_id
        if document == 'account.bank.statement':
            return self.env[model].browse(res_id).statement_id

        return self.env[model].browse(res_id)

    @api.model
    def _resolve_caret_option_view(self, target):
        '''Retrieve the target view name of the caret option.

        :param target:  The target record of the redirection.
        :return: The target view name as a string.
        '''
        if target._name == 'account.payment':
            return 'account.view_account_payment_form'
        if target._name == 'res.partner':
            return 'base.view_partner_form'
        if target._name == 'account.bank.statement':
            return 'account.view_bank_statement_form'

        # document == 'account.move' by default.
        return 'view_move_form'

    def open_document(self, options, params=None):
        if not params:
            params = {}

        ctx = self.env.context.copy()
        ctx.pop('id', '')

        # Decode params
        model = params.get('model', 'account.move.line')
        report_line_id = params.get('id')
        document = params.get('object', 'account.move')

        # Redirection data
        res_id = self._get_caret_option_target_id(report_line_id)
        target = self._resolve_caret_option_document(model, res_id, document)
        view_name = self._resolve_caret_option_view(target)
        module = 'account'
        if '.' in view_name:
            module, view_name = view_name.split('.')

        # Redirect
        view_id = self.env['ir.model.data']._xmlid_lookup("%s.%s" % (module, view_name))[2]
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'res_model': document,
            'view_id': view_id,
            'res_id': target.id,
            'context': ctx,
        }

    def open_action(self, options, domain):
        assert isinstance(domain, (list, tuple))
        domain += [('date', '>=', options.get('date').get('date_from')),
                   ('date', '<=', options.get('date').get('date_to'))]
        if not options.get('all_entries'):
            domain += [('move_id.state', '=', 'posted')]

        ctx = self.env.context.copy()
        ctx.update({'search_default_account': 1, 'search_default_groupby_date': 1})

        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Items for Tax Audit'),
            'res_model': 'account.move.line',
            'views': [[self.env.ref('account.view_move_line_tax_audit_tree').id, 'list'], [False, 'form']],
            'domain': domain,
            'context': ctx,
        }

    def open_tax(self, options, params=None):
        active_id = self._parse_line_id(params.get('id'))[-1][2]
        tax = self.env['account.tax'].browse(active_id)
        domain = ['|', ('tax_ids', 'in', [active_id]),
                       ('tax_line_id', 'in', [active_id])]
        if tax.tax_exigibility == 'on_payment':
            domain += self.env['account.move.line']._get_tax_exigible_domain()
        return self.open_action(options, domain)

    def tax_tag_template_open_aml(self, options, params=None):
        active_id = self._parse_line_id(params.get('id'))[-1][2]
        tag_template = self.env['account.tax.report.line'].browse(active_id)
        domain = [('tax_tag_ids', 'in', tag_template.tag_ids.ids)] + self.env['account.move.line']._get_tax_exigible_domain()
        return self.open_action(options, domain)

    def open_tax_report_line(self, options, params=None):
        active_id = self._parse_line_id(params.get('id'))[-1][2]
        line = self.env['account.financial.html.report.line'].browse(active_id)
        domain = ast.literal_eval(line.domain)
        action = self.open_action(options, domain)
        action['display_name'] = _('Journal Items (%s)', line.name)
        return action

    def open_general_ledger(self, options, params=None):
        if params.get('id'):
            account_id = self._get_caret_option_target_id(params.get('id', 0))
            options = dict(options)
            options['unfolded_lines'] = ['account_%s' % account_id]
        action_vals = self.env['ir.actions.actions']._for_xml_id('account_reports.action_account_report_general_ledger')
        action_vals['params'] = {
            'options': options,
            'ignore_session': 'read',
        }
        return action_vals

    def _get_caret_option_target_id(self, line_id):
        """ Retrieve the target model's id for lines obtained from a financial
        report groupby. These lines have a string as id to ensure it is unique,
        in case some accounts appear multiple times in the same report
        """
        if type(line_id) == str:
            return self._get_model_info_from_id(line_id)[1]
        else:
            # For custom uses passing the model id directly instead of the line's generic id
            return line_id

    def open_unposted_moves(self, options, params=None):
        ''' Open the list of draft journal entries that might impact the reporting'''
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_journal_line")
        action = clean_action(action, env=self.env)
        domain = [('state', '=', 'draft')]
        if options.get('date'):
            #there's no condition on the date from, as a draft entry might change the initial balance of a line
            date_to = options['date'].get('date_to') or options['date'].get('date') or fields.Date.today()
            domain += [('date', '<=', date_to)]
        action['domain'] = domain
        #overwrite the context to avoid default filtering on 'misc' journals
        action['context'] = {}
        return action

    def periodic_vat_entries(self, options):
        # Return action to open form view of newly entry created
        ctx = self._set_context(options)
        ctx['strict_range'] = True
        self = self.with_context(ctx)
        moves = self.env['account.generic.tax.report']._generate_tax_closing_entries(options)
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_journal_line")
        action = clean_action(action, env=self.env)
        if len(moves) == 1:
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = moves.id
        else:
            action['domain'] = [('id', 'in', moves.ids)]
        return action

    def _get_vat_report_attachments(self, options):
        # Fetch pdf
        pdf = self.get_pdf(options)
        return [('vat_report.pdf', pdf)]

    def action_partner_reconcile(self, options, params):
        form = self.env.ref('account_accountant.action_manual_reconciliation', False).sudo()
        ctx = self.env.context.copy()
        ctx['partner_ids'] = ctx['active_id'] = [params.get('partner_id')]
        ctx['all_entries'] = True
        return {
            'type': 'ir.actions.client',
            'view_id': form.id,
            'tag': form.tag,
            'context': ctx,
        }

    def open_journal_items(self, options, params):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_line_select")
        action = clean_action(action, env=self.env)
        ctx = self.env.context.copy()
        if params and 'id' in params:
            active_id = self._get_caret_option_target_id(params['id'])
            ctx.update({
                    'active_id': active_id,
                    'search_default_account_id': [active_id],
            })

        if options:
            domain = expression.normalize_domain(ast.literal_eval(action.get('domain') or '[]'))
            if options.get('journals'):
                selected_journals = [journal['id'] for journal in options['journals'] if journal.get('selected')]
                if len(selected_journals) == 1:
                    ctx['search_default_journal_id'] = selected_journals
                elif selected_journals:  # Otherwise, nothing is selected, so we want to display everything
                    domain = expression.AND([domain, [('journal_id', 'in', selected_journals)]])

            if options.get('analytic_accounts'):
                analytic_ids = [int(r) for r in options['analytic_accounts']]
                domain = expression.AND([domain, [('analytic_account_id', 'in', analytic_ids)]])
            if options.get('date'):
                opt_date = options['date']
                domain = expression.AND([domain, self._get_options_date_domain(options)])
            # In case the line has been generated for a "group by" financial line, append the parent line's domain to the one we created
            if params.get('financial_group_line_id'):
                # In case the hierarchy is enabled, 'financial_group_line_id' might be a string such
                # as 'hierarchy_xxx'. This will obviously cause a crash at domain evaluation.
                if not (isinstance(params['financial_group_line_id'], str) and 'hierarchy_' in params['financial_group_line_id']):
                    parent_financial_report_line = self.env['account.financial.html.report.line'].browse(params['financial_group_line_id'])
                    domain = expression.AND([domain, ast.literal_eval(parent_financial_report_line.domain)])

            if not options.get('all_entries'):
                ctx['search_default_posted'] = True

            action['domain'] = domain
        action['context'] = ctx
        return action

    def reverse(self, values):
        """Utility method used to reverse a list, this method is used during template generation in order to reverse periods for example"""
        if type(values) != list:
            return values
        else:
            inv_values = copy.deepcopy(values)
            inv_values.reverse()
        return inv_values

    @api.model
    def _sort_lines(self, lines, options):
        ''' Sort report lines based on the 'selected_column' key inside the options.
        The value of options['selected_column'] is an integer, positive or negative, indicating on which column
        to sort and also if it must be an ascending sort (positive value) or a descending sort (negative value).
        If this key is missing or falsy, lines is returned directly.

        This method has some limitations:
        - The selected_column must have 'sortable' in its classes.
        - All lines are sorted expect those having the 'total' class.
        - This only works when each line has an unique id.
        - All lines inside the selected_column must have a 'no_format' value.

        Example:

        parent_line_1           no_format=11
            child_line_1        no_format=1
            child_line_2        no_format=3
            child_line_3        no_format=2
            child_line_4        no_format=7
            child_line_5        no_format=4
            child_line_6        (total line)
        parent_line_2           no_format=10
            child_line_7        no_format=5
            child_line_8        no_format=6
            child_line_9        (total line)


        The resulting lines will be:

        parent_line_2           no_format=10
            child_line_7        no_format=5
            child_line_8        no_format=6
            child_line_9        (total line)
        parent_line_1           no_format=11
            child_line_1        no_format=1
            child_line_3        no_format=2
            child_line_2        no_format=3
            child_line_5        no_format=4
            child_line_4        no_format=7
            child_line_6        (total line)

        :param lines:   The report lines.
        :param options: The report options.
        :return:        Lines sorted by the selected column.
        '''
        def merge_tree(line):
            sorted_list.append(line)
            for l in sorted(tree[line['id']], key=lambda k: selected_sign * k['columns'][selected_column - k.get('colspan', 1)]['no_format']):
                merge_tree(l)

        sorted_list = []
        selected_column = abs(options['selected_column']) - 1
        selected_sign = -copysign(1, options['selected_column'])
        tree = defaultdict(list)
        if 'sortable' not in self._get_columns_name(options)[selected_column].get('class', ''):
            return lines  # Nothing to do here
        for line in lines:
            tree[line.get('parent_id') or None].append(line)
        for line in sorted(tree[None], key=lambda k: ('total' in k.get('class', ''), selected_sign * k['columns'][selected_column - k.get('colspan', 1)]['no_format'])):
            merge_tree(line)

        return sorted_list

    def _set_context(self, options):
        """This method will set information inside the context based on the options dict as some options need to be in context for the query_get method defined in account_move_line"""
        ctx = self.env.context.copy()
        if options.get('date') and options['date'].get('date_from'):
            ctx['date_from'] = options['date']['date_from']
        if options.get('date'):
            ctx['date_to'] = options['date'].get('date_to') or options['date'].get('date')
        if options.get('all_entries') is not None:
            ctx['state'] = options.get('all_entries') and 'all' or 'posted'
        if options.get('journals'):
            ctx['journal_ids'] = [j.get('id') for j in options.get('journals') if j.get('selected')]
        if options.get('analytic_accounts'):
            ctx['analytic_account_ids'] = self.env['account.analytic.account'].browse([int(acc) for acc in options['analytic_accounts']])
        if options.get('analytic_tags'):
            ctx['analytic_tag_ids'] = self.env['account.analytic.tag'].browse([int(t) for t in options['analytic_tags']])
        if options.get('partner_ids'):
            ctx['partner_ids'] = self.env['res.partner'].browse([int(partner) for partner in options['partner_ids']])
        if options.get('partner_categories'):
            ctx['partner_categories'] = self.env['res.partner.category'].browse([int(category) for category in options['partner_categories']])

        # Some reports call the ORM at some point when generating their lines (for example, tax report, with carry over lines).
        # Setting allowed companies from the options like this allows keeping these operations consistent with the options.
        ctx['allowed_company_ids'] = self.get_report_company_ids(options)

        return ctx

    def get_report_informations(self, options):
        '''
        return a dictionary of informations that will be needed by the js widget, manager_id, footnotes, html of report and searchview, ...
        '''
        options = self._get_options(options)
        self = self.with_context(self._set_context(options)) # For multicompany, when allowed companies are changed by options (such as aggregare_tax_unit)

        searchview_dict = {'options': options, 'context': self.env.context}
        # Check if report needs analytic
        if options.get('analytic_accounts') is not None:
            options['selected_analytic_account_names'] = [self.env['account.analytic.account'].browse(int(account)).name for account in options['analytic_accounts']]
        if options.get('analytic_tags') is not None:
            options['selected_analytic_tag_names'] = [self.env['account.analytic.tag'].browse(int(tag)).name for tag in options['analytic_tags']]
        if options.get('partner'):
            options['selected_partner_ids'] = [self.env['res.partner'].browse(int(partner)).name for partner in options['partner_ids']]
            options['selected_partner_categories'] = [self.env['res.partner.category'].browse(int(category)).name for category in (options.get('partner_categories') or [])]

        # Check whether there are unposted entries for the selected period or not (if the report allows it)
        if options.get('date') and options.get('all_entries') is not None:
            date_to = options['date'].get('date_to') or options['date'].get('date') or fields.Date.today()
            period_domain = [('state', '=', 'draft'), ('date', '<=', date_to)]
            options['unposted_in_period'] = bool(self.env['account.move'].search_count(period_domain))

        if options.get('journals'):
            journals_selected = set(journal['id'] for journal in options['journals'] if journal.get('selected'))
            for journal_group in self.env['account.journal.group'].search([('company_id', '=', self.env.company.id)]):
                if journals_selected and journals_selected == set(self._get_filter_journals().ids) - set(journal_group.excluded_journal_ids.ids):
                    options['name_journal_group'] = journal_group.name
                    break

        report_manager = self._get_report_manager(options)
        info = {'options': options,
                'context': self.env.context,
                'report_manager_id': report_manager.id,
                'footnotes': [{'id': f.id, 'line': f.line, 'text': f.text} for f in report_manager.footnotes_ids],
                'buttons': self._get_reports_buttons_in_sequence(options),
                'main_html': self.get_html(options),
                'searchview_html': self.env['ir.ui.view']._render_template(self._get_templates().get('search_template', 'account_report.search_template'), values=searchview_dict),
                }
        return info

    def _get_html_render_values(self, options, report_manager):
        return {
            'report': {
                'name': self._get_report_name(),
                'summary': report_manager.summary,
                'company_name': self.env.company.name,
            },
            'options': options,
            'context': self.env.context,
            'model': self,
        }

    def _format_lines_for_display(self, lines, options):
        """
        This method should be overridden in a report in order to apply specific formatting when printing
        the report lines.

        Used for example by the carryover functionnality in the generic tax report.
        :param lines: A list with the lines for this report.
        :param options: The options for this report.
        :return: The formatted list of lines
        """
        return lines

    def get_html(self, options, line_id=None, additional_context=None):
        '''
        return the html value of report, or html value of unfolded line
        * if line_id is set, the template used will be the line_template
        otherwise it uses the main_template. Reason is for efficiency, when unfolding a line in the report
        we don't want to reload all lines, just get the one we unfolded.
        '''
        # Prevent inconsistency between options and context.
        self = self.with_context(self._set_context(options))

        templates = self._get_templates()
        report_manager = self._get_report_manager(options)

        render_values = self._get_html_render_values(options, report_manager)
        if additional_context:
            render_values.update(additional_context)

        # Create lines/headers.
        if line_id:
            headers = options['headers']
            lines = self._get_lines(options, line_id=line_id)
            template = templates['line_template']
        else:
            headers, lines = self._get_table(options)
            options['headers'] = headers
            template = templates['main_template']
        if options.get('hierarchy'):
            lines = self._create_hierarchy(lines, options)
        if options.get('selected_column'):
            lines = self._sort_lines(lines, options)

        lines = self._format_lines_for_display(lines, options)

        render_values['lines'] = {'columns_header': headers, 'lines': lines}

        # Manage footnotes.
        footnotes_to_render = []
        if self.env.context.get('print_mode', False):
            # we are in print mode, so compute footnote number and include them in lines values, otherwise, let the js compute the number correctly as
            # we don't know all the visible lines.
            footnotes = dict([(str(f.line), f) for f in report_manager.footnotes_ids])
            number = 0
            for line in lines:
                f = footnotes.get(str(line.get('id')))
                if f:
                    number += 1
                    line['footnote'] = str(number)
                    footnotes_to_render.append({'id': f.id, 'number': number, 'text': f.text})

        # Render.
        html = self.env.ref(template)._render(render_values)
        if self.env.context.get('print_mode', False):
            for k,v in self._replace_class().items():
                html = html.replace(k, v)
            # append footnote as well
            html = html.replace(markupsafe.Markup('<div class="js_account_report_footnotes"></div>'), self.get_html_footnotes(footnotes_to_render))
        return html

    def get_html_footnotes(self, footnotes):
        template = self._get_templates().get('footnotes_template', 'account_reports.footnotes_template')
        rcontext = {'footnotes': footnotes, 'context': self.env.context}
        html = self.env['ir.ui.view']._render_template(template, values=rcontext)
        return html

    def _get_reports_buttons_in_sequence(self, options):
        return sorted(self._get_reports_buttons(options), key=lambda x: x.get('sequence', 9))

    def _get_reports_buttons(self, options):
        return [
            {'name': _('PDF'), 'sequence': 1, 'action': 'print_pdf', 'file_export_type': _('PDF')},
            {'name': _('XLSX'), 'sequence': 2, 'action': 'print_xlsx', 'file_export_type': _('XLSX')},
            {'name': _('Save'), 'sequence': 10, 'action': 'open_report_export_wizard'},
        ]

    def open_report_export_wizard(self, options):
        """ Creates a new export wizard for this report and returns an act_window
        opening it. A new account_report_generation_options key is also added to
        the context, containing the current options selected on this report
        (which must hence be taken into account when exporting it to a file).
        """
        new_context = self.env.context.copy()
        new_context['account_report_generation_options'] = options
        new_wizard = self.with_context(new_context).env['account_reports.export.wizard'].create({'report_model': self._name, 'report_id': getattr(self, 'id', 0)})
        view_id = self.env.ref('account_reports.view_report_export_wizard').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Export'),
            'view_mode': 'form',
            'res_model': 'account_reports.export.wizard',
            'target': 'new',
            'res_id': new_wizard.id,
            'views': [[view_id, 'form']],
            'context': new_context,
        }

    @api.model
    def get_export_mime_type(self, file_type):
        """ Returns the MIME type associated with a report export file type,
        for attachment generation.
        """
        type_mapping = {
            'xlsx': 'application/vnd.ms-excel',
            'pdf': 'application/pdf',
            'xml': 'application/xml',
            'xaf': 'application/vnd.sun.xml.writer',
            'txt': 'text/plain',
            'csv': 'text/csv',
            'zip': 'application/zip',
        }
        return type_mapping.get(file_type, False)

    def _get_report_manager(self, options):
        domain = [('report_name', '=', self._name)]
        domain = (domain + [('financial_report_id', '=', self.id)]) if 'id' in dir(self) else domain
        multi_company_report = options.get('multi_company', False)
        if not multi_company_report:
            domain += [('company_id', '=', self.env.company.id)]
        else:
            domain += [('company_id', '=', False)]
        existing_manager = self.env['account.report.manager'].search(domain, limit=1)
        if not existing_manager:
            existing_manager = self.env['account.report.manager'].create({
                'report_name': self._name,
                'company_id': self.env.company.id if not multi_company_report else False,
                'financial_report_id': self.id if 'id' in dir(self) else False,
            })
        return existing_manager

    @api.model
    def format_value(self, amount, currency=False, blank_if_zero=False):
        ''' Format amount to have a monetary display (with a currency symbol).
        E.g: 1000 => 1000.0 $

        :param amount:          A number.
        :param currency:        An optional res.currency record.
        :param blank_if_zero:   An optional flag forcing the string to be empty if amount is zero.
        :return:                The formatted amount as a string.
        '''
        currency_id = currency or self.env.company.currency_id
        if currency_id.is_zero(amount):
            if blank_if_zero:
                return ''
            # don't print -0.0 in reports
            amount = abs(amount)

        if self.env.context.get('no_format'):
            return amount
        return formatLang(self.env, amount, currency_obj=currency_id)

    @api.model
    def _format_aml_name(self, line_name, move_ref, move_name=None):
        ''' Format the display of an account.move.line record. As its very costly to fetch the account.move.line
        records, only line_name, move_ref, move_name are passed as parameters to deal with sql-queries more easily.

        :param line_name:   The name of the account.move.line record.
        :param move_ref:    The reference of the account.move record.
        :param move_name:   The name of the account.move record.
        :return:            The formatted name of the account.move.line record.
        '''
        names = []
        if move_name is not None and move_name != '/':
            names.append(move_name)
        if move_ref and move_ref != '/':
            names.append(move_ref)
        if line_name and line_name != move_name and line_name != '/':
            names.append(line_name)
        name = '-'.join(names)
        return name

    def format_date(self, options, dt_filter='date'):
        date_from = fields.Date.from_string(options[dt_filter]['date_from'])
        date_to = fields.Date.from_string(options[dt_filter]['date_to'])
        strict_range = options['date'].get('strict_range', False)
        return self._get_dates_period(options, date_from, date_to, options['date']['mode'], strict_range=strict_range)['string']

    def print_pdf(self, options):
        return {
                'type': 'ir_actions_account_report_download',
                'data': {'model': self.env.context.get('model'),
                         'options': json.dumps(options),
                         'output_format': 'pdf',
                         'financial_id': self.env.context.get('id'),
                         }
                }

    def _replace_class(self):
        """When printing pdf, we sometime want to remove/add/replace class for the report to look a bit different on paper
        this method is used for this, it will replace occurence of value key by the dict value in the generated pdf
        """
        return {
            'o_account_reports_no_print': '',
            'table-responsive': '',
            markupsafe.Markup('<a'): markupsafe.Markup('<span'),
            markupsafe.Markup('</a>'): markupsafe.Markup('</span>')
        }

    def get_pdf(self, options):
        # As the assets are generated during the same transaction as the rendering of the
        # templates calling them, there is a scenario where the assets are unreachable: when
        # you make a request to read the assets while the transaction creating them is not done.
        # Indeed, when you make an asset request, the controller has to read the `ir.attachment`
        # table.
        # This scenario happens when you want to print a PDF report for the first time, as the
        # assets are not in cache and must be generated. To workaround this issue, we manually
        # commit the writes in the `ir.attachment` table. It is done thanks to a key in the context.
        if not config['test_enable']:
            self = self.with_context(commit_assetsbundle=True)

        base_url = self.env['ir.config_parameter'].sudo().get_param('report.url') or self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        rcontext = {
            'mode': 'print',
            'base_url': base_url,
            'company': self.env.company,
        }

        body_html = self.with_context(print_mode=True).get_html(options)
        body = self.env['ir.ui.view']._render_template(
            "account_reports.print_template",
            values=dict(rcontext, body_html=body_html),
        )
        footer = self.env['ir.actions.report']._render_template("web.internal_layout", values=rcontext)
        footer = self.env['ir.actions.report']._render_template("web.minimal_layout", values=dict(rcontext, subst=True, body=Markup(footer.decode())))

        landscape = False
        if len(self.with_context(print_mode=True).get_header(options)[-1]) > 5:
            landscape = True

        return self.env['ir.actions.report']._run_wkhtmltopdf(
            [body],
            footer=footer.decode(),
            landscape=landscape,
            specific_paperformat_args={
                'data-report-margin-top': 10,
                'data-report-header-spacing': 10
            }
        )

    def print_xlsx(self, options):
        return {
                'type': 'ir_actions_account_report_download',
                'data': {'model': self.env.context.get('model'),
                         'options': json.dumps(options),
                         'output_format': 'xlsx',
                         'financial_id': self.env.context.get('id'),
                         }
                }

    def get_xlsx(self, options, response=None):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,
        })
        sheet = workbook.add_worksheet(self._get_report_name()[:31])

        date_default_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2, 'num_format': 'yyyy-mm-dd'})
        date_default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'num_format': 'yyyy-mm-dd'})
        default_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2})
        default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666'})
        title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
        level_0_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 6, 'font_color': '#666666'})
        level_1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 1, 'font_color': '#666666'})
        level_2_col1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'indent': 1})
        level_2_col1_total_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666'})
        level_2_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666'})
        level_3_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2})
        level_3_col1_total_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'indent': 1})
        level_3_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666'})

        #Set the first column width to 50
        sheet.set_column(0, 0, 50)

        y_offset = 0
        headers, lines = self.with_context(no_format=True, print_mode=True, prefetch_fields=False)._get_table(options)

        # Add headers.
        for header in headers:
            x_offset = 0
            for column in header:
                column_name_formated = column.get('name', '').replace('<br/>', ' ').replace('&nbsp;', ' ')
                colspan = column.get('colspan', 1)
                if colspan == 1:
                    sheet.write(y_offset, x_offset, column_name_formated, title_style)
                else:
                    sheet.merge_range(y_offset, x_offset, y_offset, x_offset + colspan - 1, column_name_formated, title_style)
                x_offset += colspan
            y_offset += 1

        if options.get('hierarchy'):
            lines = self._create_hierarchy(lines, options)
        if options.get('selected_column'):
            lines = self._sort_lines(lines, options)

        # Add lines.
        for y in range(0, len(lines)):
            level = lines[y].get('level')
            if lines[y].get('caret_options'):
                style = level_3_style
                col1_style = level_3_col1_style
            elif level == 0:
                y_offset += 1
                style = level_0_style
                col1_style = style
            elif level == 1:
                style = level_1_style
                col1_style = style
            elif level == 2:
                style = level_2_style
                col1_style = 'total' in lines[y].get('class', '').split(' ') and level_2_col1_total_style or level_2_col1_style
            elif level == 3:
                style = level_3_style
                col1_style = 'total' in lines[y].get('class', '').split(' ') and level_3_col1_total_style or level_3_col1_style
            else:
                style = default_style
                col1_style = default_col1_style

            #write the first column, with a specific style to manage the indentation
            cell_type, cell_value = self._get_cell_type_value(lines[y])
            if cell_type == 'date':
                sheet.write_datetime(y + y_offset, 0, cell_value, date_default_col1_style)
            else:
                sheet.write(y + y_offset, 0, cell_value, col1_style)

            #write all the remaining cells
            for x in range(1, len(lines[y]['columns']) + 1):
                cell_type, cell_value = self._get_cell_type_value(lines[y]['columns'][x - 1])
                if cell_type == 'date':
                    sheet.write_datetime(y + y_offset, x + lines[y].get('colspan', 1) - 1, cell_value, date_default_style)
                else:
                    sheet.write(y + y_offset, x + lines[y].get('colspan', 1) - 1, cell_value, style)

        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()

        return generated_file

    def _get_cell_type_value(self, cell):
        if 'date' not in cell.get('class', '') or not cell.get('name'):
            # cell is not a date
            return ('text', cell.get('name', ''))
        if isinstance(cell['name'], (float, datetime.date, datetime.datetime)):
            # the date is xlsx compatible
            return ('date', cell['name'])
        try:
            # the date is parsable to a xlsx compatible date
            lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(self.env)
            return ('date', datetime.datetime.strptime(cell['name'], lg.date_format))
        except:
            # the date is not parsable thus is returned as text
            return ('text', cell['name'])

    def print_xml(self, options):
        return {
                'type': 'ir_actions_account_report_download',
                'data': {'model': self.env.context.get('model'),
                         'options': json.dumps(options),
                         'output_format': 'xml',
                         'financial_id': self.env.context.get('id'),
                         }
                }

    def get_xml(self, options):
        return False

    def print_txt(self, options):
        return {
                'type': 'ir_actions_account_report_download',
                'data': {'model': self.env.context.get('model'),
                         'options': json.dumps(options),
                         'output_format': 'txt',
                         'financial_id': self.env.context.get('id'),
                         }
                }

    def get_txt(self, options):
        return False

    @api.model
    def get_vat_for_export(self, options):
        """ Returns the VAT number to use when exporting this report with the provided
        options. If a single fiscal_position option is set, its VAT number will be
        used; else the current company's will be, raising an error if its empty.
        """
        if options['fiscal_position'] in {'all', 'domestic'}:
            company = self.env.company
            if not company.vat:
                action = self.env.ref('base.action_res_company_form')
                raise RedirectWarning(_('No VAT number associated with your company. Please define one.'), action.id, _("Company Settings"))
            return company.vat
        else:
            fiscal_position = self.env['account.fiscal.position'].browse(options['fiscal_position'])
            return fiscal_position.foreign_vat

    def _get_report_country_code(self, options):
        """ Gets the country this report is for, or None if it's generic.
        This function is to be overridden by the different report subtypes if needed.
        By default, it will consider the fiscal_position option (if available) and return
        its country it it's set.

        :return: The code of this report's country.
        """
        fp_country = self._get_country_for_fiscal_position_filter(options)
        return fp_country and fp_country.code or None

    @api.model
    def get_report_company_ids(self, options):
        """ Returns a list containing the ids of the companies to be used to
        render this report, following the provided options.
        """
        if options.get('multi_company'):
            return [comp_data['id'] for comp_data in options['multi_company']]
        else:
            return self.env.company.ids

    ####################################################
    # HOOKS
    ####################################################

    def _get_account_groups_for_asset_report(self):
        """ Get the groups of account code
        return: dict whose keys are the 2 first digits of an account (xx) or a
                range of 2 first digits (xx-yy). If it is not a range, the value
                for that key shouldbe a dict containeing the key 'name'. If it
                is a range, it should also contain a dict for the key 'children'
                that is defined the same way as this return value.
        """
        return {}

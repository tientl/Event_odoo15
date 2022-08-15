# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _

from collections import defaultdict
from itertools import accumulate


class AccountDisallowedExpensesReport(models.AbstractModel):
    _name = 'account.disallowed.expenses.report'
    _description = 'Disallowed Expenses Report'
    _inherit = 'account.report'

    filter_multi_company = True
    filter_date = {'mode': 'range', 'filter': 'this_year'}
    filter_all_entries = False
    filter_journals = True
    filter_unfold_all = False

    def _get_report_name(self):
        return _("Disallowed Expenses")

    def _get_templates(self):
        templates = super(AccountDisallowedExpensesReport, self)._get_templates()
        templates['main_template'] = 'account_disallowed_expenses.main_template_de'
        return templates

    def _get_columns_name(self, options):
        columns = [{'name': ""},
                   {'name': _('Total Amount'), 'class': 'number'},
                   {'name': _('Rate'), 'class': 'number'},
                   {'name': _('Disallowed Amount'), 'class': 'number'}]
        return columns

    def _get_options(self, previous_options=None):
        options = super(AccountDisallowedExpensesReport, self)._get_options(previous_options)
        # check if there are multiple rates
        period_domain = [('date_from', '>=', options['date']['date_from']), ('date_from', '<=', options['date']['date_to'])]
        rg = self.env['account.disallowed.expenses.rate'].read_group(period_domain, ['rate'], 'category_id')
        options['multi_rate_in_period'] = any(cat['category_id_count'] > 1 for cat in rg)
        return options

    @api.model
    def _need_to_unfold(self, current, options, parent=False):
        return self._build_line_id(current, parent) in options.get('unfolded_lines') or options.get('unfold_all')

    def _get_query(self, options, line_id):
        company_ids = tuple(self.env.companies.ids) if options.get('multi_company', False) else tuple(self.env.company.ids)
        params = {'date_to': options['date']['date_to'], 'date_from': options['date']['date_from'], 'company_ids': company_ids}
        current = self._parse_line_id(line_id)
        params.update(current)
        select = """
            SELECT COALESCE(SUM(aml.balance), 0) as balance,
                account.name as account_name,
                account.code as account_code,
                category.id as category_id,
                category.name as category_name,
                category.code as category_code,
                account.company_id,
                aml.account_id,
                COALESCE(MAX(rate.rate), 0) as account_rate"""
        from_ = """
            FROM account_move_line aml
            JOIN account_move move ON aml.move_id = move.id
            JOIN account_account account ON aml.account_id = account.id
            JOIN account_disallowed_expenses_category category ON account.disallowed_expenses_category_id = category.id
            LEFT JOIN account_disallowed_expenses_rate rate ON rate.id = (
                SELECT r2.id FROM account_disallowed_expenses_rate r2
                LEFT JOIN account_disallowed_expenses_category c2 ON r2.category_id = c2.id
                WHERE r2.date_from <= aml.date
                  AND c2.id = category.id
                ORDER BY r2.date_from DESC LIMIT 1
            )"""
        where = """
            WHERE aml.company_id in %(company_ids)s
              AND aml.date >= %(date_from)s AND aml.date <= %(date_to)s
              AND move.state != 'cancel'"""
        where += current.get('category') and """
              AND category.id = %(category)s""" or ""
        where += current.get('account') and """
              AND aml.account_id = %(account)s""" or ""
        where += current.get('account_rate') and """
              AND rate.rate = %(account_rate)s""" or ""
        where += not options.get('all_entries') and """
              AND move.state = 'posted'""" or ""
        group_by = """
            GROUP BY aml.account_id, account.id, category.id"""
        group_by += options['multi_rate_in_period'] and ", rate.rate" or ""
        order_by = """
            ORDER BY category_code, account_code"""
        order_by_rate = ", account_rate"
        return select, from_, where, group_by, order_by, order_by_rate, params

    def _parse_line_id(self, line_id):
        if not line_id:
            return {'category': None}
        split = line_id.split('_')
        current = {'category': int(split[1])}
        if len(split) > 2 and split[2] == 'account':
            current['account'] = int(split[3])
            if len(split) > 4 and split[4] == 'rate':
                current['account_rate'] = float(split[5])
        return current

    def _build_line_id(self, current, parent=False):
        res = 'category_' + str(current['category'])
        if current.get('account'):
            res += '_account_' + str(current['account'])
            if current.get('account_rate'):
                res += '_rate_' + str(current['account_rate'])
        return '_'.join(res.split('_')[:-2]) if parent else res

    @api.model
    def _get_lines(self, options, line_id=None):
        select, from_, where, group_by, order_by, order_by_rate, params = self._get_query(options, line_id)
        self.env.cr.execute(select + from_ + where + group_by + order_by + order_by_rate, params)
        results = self.env.cr.dictfetchall()

        lines = []
        totals = defaultdict(lambda: [0, 0])
        if results:
            current = self._parse_line_id(line_id and '_'.join(line_id.split('_')[:-2]))
            for values in results:
                self._set_line(options, values, lines, current, totals)
        for line in lines:
            line['columns'][0] = {'name': self.format_value(totals[line['id']][0]), 'no_format': totals[line['id']][0]}
            line['columns'][2] = {'name': self.format_value(totals[line['id']][1]), 'no_format': totals[line['id']][1]}
        return lines

    def _set_line(self, options, values, lines, current, totals):
        if values['category_id'] != current['category']:
            current['category'] = values['category_id']
            current['account'] = current['account_rate'] = None
            lines.append(self._get_category_line(options, values, current))
        if values['account_id'] != current.get('account'):
            current['account'] = values['account_id']
            current['account_rate'] = None
            if self._need_to_unfold(current, options, parent=True):
                lines.append(self._get_account_line(options, values, current))
        if options['multi_rate_in_period'] and values['account_rate'] != current.get('account_rate'):
            current['account_rate'] = values['account_rate']
            if self._need_to_unfold(current, options, parent=True):
                lines.append(self._get_rate_line(options, values, current))
        for id in ['_'.join(v) for v in accumulate(zip(*[iter(self._build_line_id(current).split('_'))]*2))]:
            totals[id][0] += values['balance']
            totals[id][1] += values['balance'] * values['account_rate'] / 100

    def _get_category_line(self, options, values, current):
        return {
            **self._get_base_line(options, values, current),
            'name': '%s %s' % (values['category_code'], values['category_name']),
            'level': 1,
            'unfoldable': True,
        }

    def _get_account_line(self, options, values, current):
        return {
            **self._get_base_line(options, values, current),
            'name': '%s %s' % (values['account_code'], values['account_name']),
            'level': 2,
            'unfoldable': options['multi_rate_in_period'],
            'caret_options': False if options['multi_rate_in_period'] else 'account.account',
            'account_id': values['account_id'],
        }

    def _get_rate_line(self, options, values, current):
        return {
            **self._get_base_line(options, values, current),
            'name': '%s %s' % (values['account_code'], values['account_name']),
            'level': 3,
            'unfoldable': False,
            'caret_options': 'account.account',
            'account_id': values['account_id'],
        }

    def _get_base_line(self, options, values, current):
        return {
            'id': self._build_line_id(current),
            'columns': [{'name': ''},
                        {'name': ('%s %%' % values['account_rate']) if not options['multi_rate_in_period'] or (current.get('account_rate') is not None) else ''},
                        {'name': ''}],
            'parent_id': self._build_line_id(current, parent=True),
            'unfolded': self._need_to_unfold(current, options),
        }

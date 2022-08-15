# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.tools import float_compare
from itertools import accumulate


class AccountDisallowedExpensesReport(models.AbstractModel):
    _inherit = 'account.disallowed.expenses.report'

    filter_vehicle_split = False

    def _get_options(self, previous_options=None):
        options = super(AccountDisallowedExpensesReport, self)._get_options(previous_options)
        # check if there are multiple rates
        period_domain = [('date_from', '>=', options['date']['date_from']), ('date_from', '<=', options['date']['date_to'])]
        rg = self.env['fleet.disallowed.expenses.rate'].read_group(period_domain, ['rate'], 'vehicle_id')
        options['multi_rate_in_period'] = options['multi_rate_in_period'] or any(cat['vehicle_id_count'] > 1 for cat in rg)
        return options

    def _get_query(self, options, line_id):
        select, from_, where, group_by, order_by, order_by_rate, params = super()._get_query(options, line_id)
        current = self._parse_line_id(line_id)
        select += """,
                COALESCE(MAX(fleet_rate.rate), 0) as fleet_rate,
                vehicle.id as vehicle_id,
                vehicle.name as vehicle_name"""
        from_ += """
                LEFT JOIN fleet_vehicle vehicle ON aml.vehicle_id = vehicle.id
                LEFT JOIN fleet_disallowed_expenses_rate fleet_rate ON fleet_rate.id = (
                    SELECT r2.id FROm fleet_disallowed_expenses_rate r2
                    JOIN fleet_vehicle v2 ON r2.vehicle_id = v2.id
                    WHERE r2.date_from <= aml.date
                      AND v2.id = vehicle.id
                    ORDER BY r2.date_from DESC LIMIT 1
                )
        """
        where += current.get('vehicle') and """
              AND vehicle.id = %(vehicle)s""" or ""
        where += current.get('account') and not current.get('vehicle') and options.get('vehicle_split') and """
              AND vehicle.id IS NULL""" or ""
        group_by += ", vehicle.id, vehicle.name"
        group_by += options['multi_rate_in_period'] and ", fleet_rate.rate" or ""
        order_by = """
            ORDER BY category_code, vehicle.name IS NOT NULL, vehicle.name, account_code"""
        order_by_rate += ", fleet_rate"
        return select, from_, where, group_by, order_by, order_by_rate, params

    def _parse_line_id(self, line_id):
        current = super()._parse_line_id(line_id)
        if not line_id:
            return current
        split = line_id.split('_')
        if len(split) > 2 and split[2] == 'vehicle':
            current['vehicle'] = int(split[3])
            if len(split) > 4 and split[4] == 'account':
                current['account'] = int(split[5])
                if len(split) > 6 and split[6] == 'rate':
                    current['rate'] = float(split[7])
        return current

    def _build_line_id(self, current, parent=False):
        res = super()._build_line_id(current)
        if current.get('vehicle'):
            res = 'category_' + str(current['category'])
            res += '_vehicle_' + str(current['vehicle'])
            if current.get('account'):
                res += '_account_' + str(current['account'])
                if current.get('rate') is not None:
                    res += '_rate_' + str(current['rate'])
        return '_'.join(res.split('_')[:-2]) if parent else res

    def _get_applicable_rate(self, values):
        # EXTENDS 'account_disallowed_expenses' in order to use the vehicle rate, if it has been defined.
        return values['fleet_rate'] or super()._get_applicable_rate(values)

    @api.model
    def _get_lines(self, options, line_id=None):
        # Overridden in order to hide rates that are inconsistent (to avoid confusion).
        # A rate can be defined on the expense category and/or the vehicle,
        # which could lead to inconsistencies in the report when aggregating values.
        lines = super()._get_lines(options, line_id)
        for line in lines:
            total, rate, disallowed = line['columns']
            computed_rate = disallowed['no_format'] / total['no_format'] * 100 if total['no_format'] else 0
            if float_compare(computed_rate, rate['no_format'], precision_digits=2):
                rate['name'] = ''
        return lines

    def _set_line(self, options, values, lines, current, totals):
        if not values['vehicle_id']:
            if current.get('vehicle'):
                current['vehicle'] = None
            super()._set_line(options, values, lines, current, totals)
        else:
            if values['category_id'] != current['category']:
                current['category'] = values['category_id']
                current['account'] = current['account'] = current['rate'] = None
                lines.append(self._get_category_line(options, values, current))
            # Only append vehicle lines to the report if the 'vehicle_split' options is selected
            if options.get('vehicle_split'):
                if values['vehicle_id'] != current.get('vehicle'):
                    current['vehicle'] = values['vehicle_id']
                    current['account'] = current['rate'] = None
                    if self._need_to_unfold(current, options, parent=True):
                        lines.append(self._get_vehicle_line(options, values, current))
            if values['account_id'] != current.get('account'):
                current['account'] = values['account_id']
                current['rate'] = None
                if self._need_to_unfold(current, options, parent=True):
                    lines.append(self._get_vehicle_account_line(options, values, current))
            if options['multi_rate_in_period'] and values['rate'] != current.get('rate'):
                current['rate'] = values['rate']
                if self._need_to_unfold(current, options, parent=True):
                    lines.append(self._get_vehicle_rate_line(options, values, current, level=len(list(current.values()))))
            for id in ['_'.join(v) for v in accumulate(zip(*[iter(self._build_line_id(current).split('_'))]*2))]:
                totals[id][0] += values['balance']
                totals[id][1] += values['balance'] * values['rate'] / 100

    def _get_vehicle_line(self, options, values, current):
        return {**self._get_base_line(options, values, current), **{
            'name': values['vehicle_name'],
            'level': 2,
            'unfoldable': True,
            'caret_options': False,
        }}

    def _get_vehicle_account_line(self, options, values, current):
        return {**self._get_base_line(options, values, current), **{
            'name': '%s %s' % (values['account_code'], values['account_name']),
            'level': 3,
            'unfoldable': options['multi_rate_in_period'],
            'caret_options': False if options['multi_rate_in_period'] else 'account.account',
            'account_id': values['account_id'],
        }}

    def _get_vehicle_rate_line(self, options, values, current, level):
        return {**self._get_base_line(options, values, current), **{
            'name': '%s %s' % (values['account_code'], values['account_name']),
            'level': level,
            'unfoldable': False,
            'caret_options': 'account.account',
            'account_id': values['account_id'],
        }}

    def _get_base_line(self, options, values, current):
        res = super()._get_base_line(options, values, current)
        if values['vehicle_id']:
            res['columns'][1] = {
                'name': ('%s %%' % values['rate']) if not options['multi_rate_in_period'] or current.get('rate') is not None else '',
                'no_format': values['rate'],
            }
        return res

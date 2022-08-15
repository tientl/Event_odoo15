# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api, _, fields
from collections import OrderedDict
from datetime import timedelta

COLUMNS = (DEBIT, CREDIT, DEBITOR, CREDITOR, ACTIVE, PASSIVE, LOSS, GAIN) = (
    'debe', 'haber', 'deudor', 'acreedor', 'activo', 'pasivo', 'perdida', 'ganancia')


class CL8ColumnsReport(models.AbstractModel):
    _name = "account.eightcolumns.report.cl"
    _inherit = "account.report"
    _description = "Chilean Accounting eight columns report"

    filter_date = {'mode': 'range', 'filter': 'this_year'}
    filter_journals = True
    filter_all_entries = False
    filter_analytic = True
    filter_multi_company = None

    def _get_report_name(self):
        return _("Fiscal balance (8 columns)")

    def _get_columns_name(self, options):
        columns = [
            {'name': _("Accounts")},
            {'name': _("Debit"), 'class': 'number'},
            {'name': _("Credit"), 'class': 'number'},
            {'name': _("Debitor"), 'class': 'number'},
            {'name': _("Creditor"), 'class': 'number'},
            {'name': _("Active"), 'class': 'number'},
            {'name': _("Passive"), 'class': 'number'},
            {'name': _("Loss"), 'class': 'number'},
            {'name': _("Gain"), 'class': 'number'}
        ]
        return columns

    @api.model
    def _prepare_query(self, options):
        tables, where_clause, where_params = self._query_get(options)

        sql_query = """
            SELECT aa.id, aa.code, aa.name,
                   SUM(account_move_line.debit) AS debe,
                   SUM(account_move_line.credit) AS haber,
                   GREATEST(SUM(account_move_line.balance), 0) AS deudor,
                   GREATEST(SUM(-account_move_line.balance), 0) AS acreedor,
                   CASE WHEN aa.internal_group IN ('asset', 'liability', 'equity')
                      THEN GREATEST(SUM(account_move_line.balance), 0) ELSE 0 END AS activo,
                   CASE WHEN aa.internal_group IN ('asset', 'liability', 'equity')
                      THEN GREATEST(SUM(-account_move_line.balance), 0) ELSE 0 END AS pasivo,
                   CASE WHEN aa.internal_group IN ('expense', 'income')
                      THEN GREATEST(SUM(account_move_line.balance), 0) ELSE 0 END AS perdida,
                   CASE WHEN aa.internal_group IN ('expense', 'income')
                      THEN GREATEST(SUM(-account_move_line.balance), 0) ELSE 0 END AS ganancia
            FROM account_account AS aa, """ + tables + """
            WHERE """ + where_clause + """
            AND aa.id = account_move_line.account_id
            GROUP BY aa.id, aa.code, aa.name
            ORDER BY aa.code
        """
        return sql_query, where_params

    @api.model
    def _get_lines(self, options, line_id=None):
        lines = []
        sql_query, parameters = self._prepare_query(options)
        self.env.cr.execute(sql_query, parameters)
        results = self.env.cr.dictfetchall()
        for line in results:
            lines.append({
                'id': line['id'],
                'name': line['code'] + " " + line['name'],
                'level': 3,
                'unfoldable': False,
                'columns': [{'name': self.format_value(line[col])} for col in COLUMNS],
                'caret_options': 'account.account'
            })
        if lines:
            subtotals = self._calculate_subtotals(results)
            lines.append({
                'id': 'subtotals_line',
                'class': 'total',
                'name': _("Subtotal"),
                'level': 3,
                'columns': [{'name': self.format_value(subtotals[col])} for col in COLUMNS],
                'unfoldable': False,
                'unfolded': False
            })
            exercise_result = self._calculate_exercise_result(subtotals)
            lines.append({
                'id': 'exercise_result_line',
                'class': 'total',
                'name': _("Profit and Loss"),
                'level': 4,
                'columns': [{'name': '' if col in (DEBIT, CREDIT, DEBITOR, CREDITOR)
                             else self.format_value(exercise_result[col])} for col in COLUMNS],
                'unfoldable': False,
                'unfolded': False
            })
            previous_years_unallocated_earnings = self._calculate_previous_years_unallocated_earnings(options, subtotals, exercise_result)
            if previous_years_unallocated_earnings:
                lines.append({
                    'id': 'previous_years_line',
                    'class': 'total',
                    'name': _("Previous years unallocated earnings"),
                    'level': 4,
                    'columns': [{
                        'name': self.format_value(previous_years_unallocated_earnings[col]) if previous_years_unallocated_earnings[col] else ''
                    } for col in COLUMNS],
                    'unfoldable': False,
                    'unfolded': False
                })
            totals = self._calculate_totals(subtotals, exercise_result, previous_years_unallocated_earnings)
            lines.append({
                'id': 'totals_line',
                'class': 'total',
                'name': _("Total"),
                'level': 2,
                'columns': [{'name': self.format_value(totals[col])} for col in COLUMNS],
                'unfoldable': False,
                'unfolded': False
            })
        return lines

    def _calculate_subtotals(self, lines):
        return OrderedDict([(col, sum([line.get(col, 0) for line in lines])) for col in COLUMNS])

    def _calculate_exercise_result(self, subtotal_line):
        exercise_result = OrderedDict.fromkeys(COLUMNS, 0)
        if subtotal_line[GAIN] >= subtotal_line[LOSS]:
            exercise_result[LOSS] = subtotal_line[GAIN] - subtotal_line[LOSS]
            exercise_result[PASSIVE] = exercise_result[LOSS]
        else:
            exercise_result[GAIN] = subtotal_line[LOSS] - subtotal_line[GAIN]
            exercise_result[ACTIVE] = exercise_result[GAIN]
        return exercise_result

    def _calculate_unallocated_earnings_value(self, options):
        """
            Get all the unallocated earnings value from the previous fiscal years.
            The past moves that target Income and expense account (+ special type of expenses)
            are summed, and the allocated earnings are removed by summing the balances
            of the moves targeting the special account 'Undistributed Profits/Losses'.
        """
        new_options = options.copy()
        date_from_str = new_options.get('date', {}).get('date_from', '')
        date_from = fields.Date.from_string(date_from_str) or fields.Date.today()
        fiscal_dates = self.env.company.compute_fiscalyear_dates(date_from)
        new_options['date'] = self._get_dates_period(
            options,
            None,
            fiscal_dates['date_from'] - timedelta(days=1),
            'range',
            period_type='custom',
            strict_range=True)
        tables, where_clause, where_params = self._query_get(new_options)
        user_type_ids = [self.env.ref(xml_id).id for xml_id in (
            'account.data_unaffected_earnings',
            'account.data_account_type_revenue',
            'account.data_account_type_other_income',
            'account.data_account_type_direct_costs',
            'account.data_account_type_expenses',
            'account.data_account_type_depreciation'
        )]
        sql_query = f"""
            SELECT -SUM(account_move_line.balance) as unaffected_earnings
            FROM account_account AS aa, {tables}
            WHERE {where_clause}
            AND aa.id = account_move_line.account_id
            AND aa.user_type_id IN %s
        """.strip('\n')
        self.env.cr.execute(sql_query, where_params + [tuple(user_type_ids)])
        value = self.env.cr.fetchone()[0] or 0.0
        return self.env.company.currency_id.round(value)

    def _calculate_previous_years_unallocated_earnings(self, options, subtotals, exercise_result):
        earning = self._calculate_unallocated_earnings_value(options)
        if not earning:
            return None

        sum_col, sold_col, passive_sign = {
            True: (DEBIT, DEBITOR, -1),
            False: (CREDIT, CREDITOR, 1),
        }.get(earning < 0)

        abs_earning = abs(earning)
        row = OrderedDict.fromkeys(COLUMNS, 0)
        row[sum_col] = abs_earning
        row[sold_col] = abs_earning
        row[PASSIVE] = passive_sign * abs_earning
        return row

    def _calculate_totals(self, subtotal_line, exercise_result_line, previous_years_unallocated_earnings):
        parts = [subtotal_line, exercise_result_line]
        if previous_years_unallocated_earnings:
            parts.append(previous_years_unallocated_earnings)
        return OrderedDict([(col, sum([part.get(col, 0) for part in parts])) for col in COLUMNS])

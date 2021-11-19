# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api, _
from collections import OrderedDict


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
        return _("Balance Tributario (8 columnas)")

    def _get_columns_name(self, options):
        columns = [
            {'name': _("Cuenta")},
            {'name': _("Debe"), 'class': 'number'},
            {'name': _("Haber"), 'class': 'number'},
            {'name': _("Deudor"), 'class': 'number'},
            {'name': _("Acreedor"), 'class': 'number'},
            {'name': _("Activo"), 'class': 'number'},
            {'name': _("Pasivo"), 'class': 'number'},
            {'name': _("Perdida"), 'class': 'number'},
            {'name': _("Ganancia"), 'class': 'number'}
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
                'columns': [
                    {'name': values} for values in [
                        self.format_value(line['debe']),
                        self.format_value(line['haber']),
                        self.format_value(line['deudor']),
                        self.format_value(line['acreedor']),
                        self.format_value(line['activo']),
                        self.format_value(line['pasivo']),
                        self.format_value(line['perdida']),
                        self.format_value(line['ganancia'])
                    ]
                ],
                'caret_options': 'account.account'
            })
        if lines:
            subtotals = self._calculate_subtotals(results)
            lines.append({
                'id': 'subtotals_line',
                'class': 'total',
                'name': _("Subtotal"),
                'level': 3,
                'columns': [
                    {'name': self.format_value(subtotals[key])} for key in subtotals.keys()
                ],
                'unfoldable': False,
                'unfolded': False
            })
            exercise_result = self._calculate_exercise_result(subtotals)
            lines.append({
                'id': 'exercise_result_line',
                'class': 'total',
                'name': _("Resultado del Ejercicio"),
                'level': 3,
                'columns': [
                    {'name': values} for values in [
                        '', '', '', '', '',
                        self.format_value(exercise_result['pasivo']),
                        self.format_value(exercise_result['perdida']),
                        self.format_value(exercise_result['ganancia'])
                    ]
                ],
                'unfoldable': False,
                'unfolded': False
            })
            totals = self._calculate_totals(subtotals, exercise_result)
            lines.append({
                'id': 'totals_line',
                'class': 'total',
                'name': _("Total"),
                'level': 2,
                'columns': [
                    {'name': self.format_value(totals[key])} for key in totals.keys()
                ],
                'unfoldable': False,
                'unfolded': False
            })
        return lines

    def _calculate_subtotals(self, lines):
        subtotals = OrderedDict([
            ('debe', 0), ('haber', 0),
            ('deudor', 0), ('acreedor', 0),
            ('activo', 0), ('pasivo', 0),
            ('perdida', 0), ('ganancia', 0)
        ])
        for key in subtotals.keys():
            for line in lines:
                subtotals[key] += line[key]
        return subtotals

    def _calculate_exercise_result(self, subtotal_line):
        exercise_result = {'pasivo': 0, 'perdida': 0, 'ganancia': 0}
        if subtotal_line['ganancia'] >= subtotal_line['perdida']:
            exercise_result['ganancia'] = subtotal_line['ganancia'] - subtotal_line['perdida']
            exercise_result['pasivo'] = exercise_result['ganancia']
        else:
            exercise_result['perdida'] = subtotal_line['perdida'] - subtotal_line['ganancia']
            exercise_result['pasivo'] = exercise_result['perdida'] * (-1)
        return exercise_result

    def _calculate_totals(self, subtotal_line, exercise_result_line):
        totals = OrderedDict([
            ('debe', subtotal_line['debe']), ('haber', subtotal_line['haber']),
            ('deudor', subtotal_line['deudor']), ('acreedor', subtotal_line['acreedor']),
            ('activo', subtotal_line['activo']), ('pasivo', subtotal_line['pasivo'] + exercise_result_line['pasivo']),
            ('perdida', exercise_result_line['perdida']), ('ganancia', exercise_result_line['ganancia'])
        ])
        return totals

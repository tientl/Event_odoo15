# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields, _
from odoo.tools.misc import format_date

from dateutil.relativedelta import relativedelta
from itertools import chain


class ReportAccountAgedPartner(models.AbstractModel):
    _name = "account.aged.partner"
    _description = "Aged Partner Balances"
    _inherit = 'account.accounting.report'
    _order = "partner_name, report_date asc, move_name desc"

    filter_date = {'mode': 'single', 'filter': 'today'}
    filter_unfold_all = False
    filter_partner = True
    order_selected_column = {'default': 0}

    partner_id = fields.Many2one('res.partner')
    partner_name = fields.Char(group_operator='max')
    partner_trust = fields.Char(group_operator='max')
    payment_id = fields.Many2one('account.payment')
    report_date = fields.Date(group_operator='max', string='Due Date')
    expected_pay_date = fields.Date(string='Expected Date')
    move_type = fields.Char()
    move_name = fields.Char(group_operator='max')
    move_ref = fields.Char()
    account_name = fields.Char(group_operator='max')
    account_code = fields.Char(group_operator='max')
    report_currency_id = fields.Many2one('res.currency')
    period0 = fields.Monetary(string='As of: ')
    period1 = fields.Monetary(string='1 - 30')
    period2 = fields.Monetary(string='31 - 60')
    period3 = fields.Monetary(string='61 - 90')
    period4 = fields.Monetary(string='91 - 120')
    period5 = fields.Monetary(string='Older')
    amount_currency = fields.Monetary(currency_field='currency_id')

    @api.model
    def _get_templates(self):
        # OVERRIDE
        templates = super(ReportAccountAgedPartner, self)._get_templates()
        templates['main_template'] = 'account_reports.template_aged_partner_balance_report'
        return templates

    ####################################################
    # QUERIES
    ####################################################

    @api.model
    def _get_query_period_table(self, options):
        ''' Compute the periods to handle in the report.
        E.g. Suppose date = '2019-01-09', the computed periods will be:

        Name                | Start         | Stop
        --------------------------------------------
        As of 2019-01-09    | 2019-01-09    |
        1 - 30              | 2018-12-10    | 2019-01-08
        31 - 60             | 2018-11-10    | 2018-12-09
        61 - 90             | 2018-10-11    | 2018-11-09
        91 - 120            | 2018-09-11    | 2018-10-10
        Older               |               | 2018-09-10

        Then, return the values as an sql floating table to use it directly in queries.

        :return: A floating sql query representing the report's periods.
        '''
        def minus_days(date_obj, days):
            return fields.Date.to_string(date_obj - relativedelta(days=days))

        date_str = options['date']['date_to']
        date = fields.Date.from_string(date_str)
        period_values = [
            (False,                  date_str),
            (minus_days(date, 1),    minus_days(date, 30)),
            (minus_days(date, 31),   minus_days(date, 60)),
            (minus_days(date, 61),   minus_days(date, 90)),
            (minus_days(date, 91),   minus_days(date, 120)),
            (minus_days(date, 121),  False),
        ]

        period_table = ('(VALUES %s) AS period_table(date_start, date_stop, period_index)' %
                        ','.join("(%s, %s, %s)" for i, period in enumerate(period_values)))
        params = list(chain.from_iterable(
            (period[0] or None, period[1] or None, i)
            for i, period in enumerate(period_values)
        ))
        return self.env.cr.mogrify(period_table, params).decode(self.env.cr.connection.encoding)

    @api.model
    def _get_sql(self):
        options = self.env.context['report_options']
        query = ("""
            SELECT
                {move_line_fields},
                account_move_line.amount_currency as amount_currency,
                account_move_line.partner_id AS partner_id,
                partner.name AS partner_name,
                COALESCE(trust_property.value_text, 'normal') AS partner_trust,
                COALESCE(account_move_line.currency_id, journal.currency_id) AS report_currency_id,
                account_move_line.payment_id AS payment_id,
                COALESCE(account_move_line.date_maturity, account_move_line.date) AS report_date,
                account_move_line.expected_pay_date AS expected_pay_date,
                move.move_type AS move_type,
                move.name AS move_name,
                move.ref AS move_ref,
                account.code || ' ' || account.name AS account_name,
                account.code AS account_code,""" + ','.join([("""
                CASE WHEN period_table.period_index = {i}
                THEN %(sign)s * ROUND((
                    account_move_line.balance - COALESCE(SUM(part_debit.amount), 0) + COALESCE(SUM(part_credit.amount), 0)
                ) * currency_table.rate, currency_table.precision)
                ELSE 0 END AS period{i}""").format(i=i) for i in range(6)]) + """
            FROM account_move_line
            JOIN account_move move ON account_move_line.move_id = move.id
            JOIN account_journal journal ON journal.id = account_move_line.journal_id
            JOIN account_account account ON account.id = account_move_line.account_id
            LEFT JOIN res_partner partner ON partner.id = account_move_line.partner_id
            LEFT JOIN ir_property trust_property ON (
                trust_property.res_id = 'res.partner,'|| account_move_line.partner_id
                AND trust_property.name = 'trust'
                AND trust_property.company_id = account_move_line.company_id
            )
            JOIN {currency_table} ON currency_table.company_id = account_move_line.company_id
            LEFT JOIN LATERAL (
                SELECT part.amount, part.debit_move_id
                FROM account_partial_reconcile part
                WHERE part.max_date <= %(date)s
            ) part_debit ON part_debit.debit_move_id = account_move_line.id
            LEFT JOIN LATERAL (
                SELECT part.amount, part.credit_move_id
                FROM account_partial_reconcile part
                WHERE part.max_date <= %(date)s
            ) part_credit ON part_credit.credit_move_id = account_move_line.id
            JOIN {period_table} ON (
                period_table.date_start IS NULL
                OR COALESCE(account_move_line.date_maturity, account_move_line.date) <= DATE(period_table.date_start)
            )
            AND (
                period_table.date_stop IS NULL
                OR COALESCE(account_move_line.date_maturity, account_move_line.date) >= DATE(period_table.date_stop)
            )
            WHERE account.internal_type = %(account_type)s
            AND account.exclude_from_aged_reports IS NOT TRUE
            GROUP BY account_move_line.id, partner.id, trust_property.id, journal.id, move.id, account.id,
                     period_table.period_index, currency_table.rate, currency_table.precision
            HAVING ROUND(account_move_line.balance - COALESCE(SUM(part_debit.amount), 0) + COALESCE(SUM(part_credit.amount), 0), currency_table.precision) != 0
        """).format(
            move_line_fields=self._get_move_line_fields('account_move_line'),
            currency_table=self.env['res.currency']._get_query_currency_table(options),
            period_table=self._get_query_period_table(options),
        )
        params = {
            'account_type': options['filter_account_type'],
            'sign': 1 if options['filter_account_type'] == 'receivable' else -1,
            'date': options['date']['date_to'],
        }
        return self.env.cr.mogrify(query, params).decode(self.env.cr.connection.encoding)

    ####################################################
    # COLUMNS/LINES
    ####################################################
    @api.model
    def _get_column_details(self, options):
        columns = [
            self._header_column(),
            self._field_column('report_date'),

            self._field_column('account_name', name=_("Account"), ellipsis=True),
            self._field_column('expected_pay_date'),
            self._field_column('period0', name=_("As of: %s", format_date(self.env, options['date']['date_to']))),
            self._field_column('period1', sortable=True),
            self._field_column('period2', sortable=True),
            self._field_column('period3', sortable=True),
            self._field_column('period4', sortable=True),
            self._field_column('period5', sortable=True),
            self._custom_column(  # Avoid doing twice the sub-select in the view
                name=_('Total'),
                classes=['number'],
                formatter=self.format_value,
                getter=(lambda v: v['period0'] + v['period1'] + v['period2'] + v['period3'] + v['period4'] + v['period5']),
                sortable=True,
            ),
        ]

        if self.user_has_groups('base.group_multi_currency'):
            columns[2:2] = [
                self._field_column('amount_currency'),
                self._field_column('currency_id'),
            ]
        return columns

    def _get_hierarchy_details(self, options):
        return [
            self._hierarchy_level('partner_id', foldable=True, namespan=len(self._get_column_details(options)) - 7),
            self._hierarchy_level('id'),
        ]

    def _show_line(self, report_dict, value_dict, current, options):
        # Don't display an aml report line (except the header) with all zero amounts.
        all_zero = all(
            self.env.company.currency_id.is_zero(value_dict[f])
            for f in ['period0', 'period1', 'period2', 'period3', 'period4', 'period5']
        ) and not value_dict.get('__count')
        return super()._show_line(report_dict, value_dict, current, options) and not all_zero

    def _format_partner_id_line(self, res, value_dict, options):
        res['name'] = value_dict['partner_name'][:128] if value_dict['partner_name'] else _('Unknown Partner')
        res['trust'] = value_dict['partner_trust']

    def _format_id_line(self, res, value_dict, options):
        res['name'] = value_dict['move_name']
        res['title_hover'] = value_dict['move_ref']
        res['caret_options'] = 'account.payment' if value_dict.get('payment_id') else 'account.move'
        for col in res['columns']:
            if col.get('no_format') == 0:
                col['name'] = ''
        res['columns'][-1]['name'] = ''

    def _format_total_line(self, res, value_dict, options):
        res['name'] = _('Total')
        res['colspan'] = len(self._get_column_details(options)) - 7
        res['columns'] = res['columns'][res['colspan']-1:]


class ReportAccountAgedReceivable(models.Model):
    _name = "account.aged.receivable"
    _description = "Aged Receivable"
    _inherit = "account.aged.partner"
    _auto = False

    def _get_options(self, previous_options=None):
        # OVERRIDE
        options = super(ReportAccountAgedReceivable, self)._get_options(previous_options=previous_options)
        options['filter_account_type'] = 'receivable'
        return options

    @api.model
    def _get_report_name(self):
        return _("Aged Receivable")

    @api.model
    def _get_templates(self):
        # OVERRIDE
        templates = super(ReportAccountAgedReceivable, self)._get_templates()
        templates['line_template'] = 'account_reports.line_template_aged_receivable_report'
        return templates


class ReportAccountAgedPayable(models.Model):
    _name = "account.aged.payable"
    _description = "Aged Payable"
    _inherit = "account.aged.partner"
    _auto = False

    def _get_options(self, previous_options=None):
        # OVERRIDE
        options = super(ReportAccountAgedPayable, self)._get_options(previous_options=previous_options)
        options['filter_account_type'] = 'payable'
        return options

    @api.model
    def _get_report_name(self):
        return _("Aged Payable")

    @api.model
    def _get_templates(self):
        # OVERRIDE
        templates = super(ReportAccountAgedPayable, self)._get_templates()
        templates['line_template'] = 'account_reports.line_template_aged_payable_report'
        return templates

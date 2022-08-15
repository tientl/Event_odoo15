# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.tools import float_is_zero, classproperty

from itertools import chain


class MulticurrencyRevaluationReport(models.Model):
    """Manage Unrealized Gains/Losses.

    In multi-currencies environments, we need a way to control the risk related
    to currencies (in case some are higthly fluctuating) and, in some countries,
    some laws also require to create journal entries to record the provisionning
    of a probable future expense related to currencies. Hence, people need to
    create a journal entry at the beginning of a period, to make visible the
    probable expense in reports (and revert it at the end of the period, to
    recon the real gain/loss.
    """

    _inherit = 'account.accounting.report'
    _name = 'account.multicurrency.revaluation'
    _description = 'Multicurrency Revaluation Report'
    _auto = False

    _order = "report_include desc, currency_code desc, account_code asc, date desc, id desc"

    @classproperty
    def _depends(cls):
        ret = dict(super()._depends)
        ret.setdefault('account.partial.reconcile', []).extend([
            'amount',
            *(f'{side}_{field}' for side in ('debit', 'credit') for field in ('move_id', 'currency_id', 'amount_currency')),
        ])
        ret.setdefault('account.move.line', []).extend([
            'amount_residual',
            'amount_residual_currency'
        ])
        return ret

    filter_multi_company = None
    filter_date = {'filter': 'this_month', 'mode': 'single'}
    filter_all_entries = False
    total_line = False

    report_amount_currency = fields.Monetary(string='Balance in foreign currency')
    report_amount_currency_current = fields.Monetary(string='Balance at current rate')
    report_adjustment = fields.Monetary(string='Adjustment')
    report_balance = fields.Monetary(string='Balance at operation rate')
    report_currency_id = fields.Many2one('res.currency')
    report_include = fields.Boolean(group_operator='bool_and')
    account_code = fields.Char(group_operator="max")
    account_name = fields.Char(group_operator="max")
    currency_code = fields.Char(group_operator="max")
    move_ref = fields.Char(group_operator="max")
    move_name = fields.Char(group_operator="max")

    # TEMPLATING
    @api.model
    def _get_report_name(self):
        return _('Unrealized Currency Gains/Losses')

    @api.model
    def _get_templates(self):
        templates = super()._get_templates()
        templates['line_template'] = 'account_reports.line_template_multicurrency_report'
        templates['main_template'] = 'account_reports.template_multicurrency_report'
        return templates

    def _get_reports_buttons(self, options):
        r = super()._get_reports_buttons(options)
        r.append({'name': _('Adjustment Entry'), 'action': 'view_revaluation_wizard'})
        return r

    def _get_options(self, previous_options=None):
        options = super()._get_options(previous_options)
        rates = self.env['res.currency'].search([('active', '=', True)])._get_rates(self.env.company, options.get('date').get('date_to'))
        for key in rates.keys():  # normalize the rates to the company's currency
            rates[key] /= rates[self.env.company.currency_id.id]
        options['currency_rates'] = {
            str(currency_id.id): {
                'currency_id': currency_id.id,
                'currency_name': currency_id.name,
                'currency_main': self.env.company.currency_id.name,
                'rate': (rates[currency_id.id]
                         if not (previous_options or {}).get('currency_rates', {}).get(str(currency_id.id), {}).get('rate') else
                         float(previous_options['currency_rates'][str(currency_id.id)]['rate'])),
            } for currency_id in self.env['res.currency'].search([('active', '=', True)])
        }
        options['company_currency'] = options['currency_rates'].pop(str(self.env.company.currency_id.id))
        options['custom_rate'] = any(
            not float_is_zero(cr['rate'] - rates[cr['currency_id']], 6)
            for cr in options['currency_rates'].values()
        )
        options['warning_multicompany'] = len(self.env.companies) > 1
        return options

    def _get_column_details(self, options):
        columns_header = [
            self._header_column(),
            self._field_column('report_amount_currency'),
            self._field_column('report_balance'),
            self._field_column('report_amount_currency_current'),
            self._field_column('report_adjustment'),
        ]
        return columns_header

    def _get_hierarchy_details(self, options):
        return [
            self._hierarchy_level('report_include'),
            self._hierarchy_level('report_currency_id'),
            self._hierarchy_level('account_id', foldable=True),
            self._hierarchy_level('id'),
        ]

    # GET LINES VALUES
    def _get_sql(self):
        options = self.env.context['report_options']
        query = '(VALUES {}) AS custom_currency_table(currency_id, rate)'.format(
            ', '.join("(%s, %s)" for i in range(len(options['currency_rates'])))
        )
        params = list(chain.from_iterable((cur['currency_id'], cur['rate']) for cur in options['currency_rates'].values()))
        custom_currency_table = self.env.cr.mogrify(query, params).decode(self.env.cr.connection.encoding)

        return """
            SELECT {move_line_fields},
                   aml.amount_residual_currency                         AS report_amount_currency,
                   aml.amount_residual                                  AS report_balance,
                   aml.amount_residual_currency / custom_currency_table.rate                       AS report_amount_currency_current,
                   aml.amount_residual_currency / custom_currency_table.rate - aml.amount_residual AS report_adjustment,
                   aml.currency_id                                      AS report_currency_id,
                   account.code                                         AS account_code,
                   account.name                                         AS account_name,
                   currency.name                                        AS currency_code,
                   move.ref                                             AS move_ref,
                   move.name                                            AS move_name,
                   NOT EXISTS (
                       SELECT * FROM account_account_exclude_res_currency_provision WHERE account_account_id = account_id AND res_currency_id = aml.currency_id
                   )                                                    AS report_include
            FROM account_move_line aml
            JOIN account_move move ON move.id = aml.move_id
            JOIN account_account account ON aml.account_id = account.id
            JOIN res_currency currency ON currency.id = aml.currency_id
            JOIN {custom_currency_table} ON custom_currency_table.currency_id = currency.id
            WHERE (account.currency_id != aml.company_currency_id OR (account.internal_type IN ('receivable', 'payable') AND (aml.currency_id != aml.company_currency_id)))
              AND (aml.amount_residual != 0 OR aml.amount_residual_currency != 0)

            UNION ALL

            -- Add the lines without currency, i.e. payment in company currency for invoice in foreign currency
            SELECT {move_line_fields},
                   CASE WHEN aml.id = part.credit_move_id THEN -part.debit_amount_currency ELSE -part.credit_amount_currency
                   END                                                  AS report_amount_currency,
                   -part.amount                                         AS report_balance,
                   CASE WHEN aml.id = part.credit_move_id THEN -part.debit_amount_currency ELSE -part.credit_amount_currency
                   END / custom_currency_table.rate                               AS report_amount_currency_current,
                   CASE WHEN aml.id = part.credit_move_id THEN -part.debit_amount_currency ELSE -part.credit_amount_currency
                   END / custom_currency_table.rate - aml.balance                 AS report_adjustment,
                   CASE WHEN aml.id = part.credit_move_id THEN part.debit_currency_id ELSE part.credit_currency_id
                   END                                                  AS report_currency_id,
                   account.code                                         AS account_code,
                   account.name                                         AS account_name,
                   currency.name                                        AS currency_code,
                   move.ref                                             AS move_ref,
                   move.name                                            AS move_name,
                   NOT EXISTS (
                       SELECT * FROM account_account_exclude_res_currency_provision WHERE account_account_id = account_id AND res_currency_id = aml.currency_id
                   )                                                    AS report_include
            FROM account_move_line aml
            JOIN account_move move ON move.id = aml.move_id
            JOIN account_account account ON aml.account_id = account.id
            JOIN account_partial_reconcile part ON aml.id = part.credit_move_id OR aml.id = part.debit_move_id
            JOIN res_currency currency ON currency.id = (CASE WHEN aml.id = part.credit_move_id THEN part.debit_currency_id ELSE part.credit_currency_id END)
            JOIN {custom_currency_table} ON custom_currency_table.currency_id = currency.id
            WHERE (account.currency_id = aml.company_currency_id AND (account.internal_type IN ('receivable', 'payable') AND aml.currency_id = aml.company_currency_id))
        """.format(
            custom_currency_table=custom_currency_table,
            move_line_fields=self._get_move_line_fields('aml'),
        )

    def _format_all_line(self, res, value_dict, options):
        if value_dict.get('report_currency_id'):
            res['columns'][0] = {'name': self.format_value(value_dict['report_amount_currency'], self.env['res.currency'].browse(value_dict.get('report_currency_id')[0]))}
        res['included'] = value_dict.get('report_included')
        res['class'] = 'no_print' if not value_dict.get('report_include') else ''

    def _format_report_currency_id_line(self, res, value_dict, options):
        res['name'] = '{for_cur} (1 {comp_cur} = {rate:.6} {for_cur})'.format(
            for_cur=value_dict['currency_code'],
            comp_cur=self.env.company.currency_id.display_name,
            rate=float(options['currency_rates'][str(value_dict.get('report_currency_id')[0])]['rate']),
        )

    def _format_account_id_line(self, res, value_dict, options):
        res['name'] = '%s %s' % (value_dict['account_code'], value_dict['account_name'])

    def _format_id_line(self, res, value_dict, options):
        res['name'] = self._format_aml_name(value_dict['name'], value_dict['move_ref'], value_dict['move_name'])
        res['caret_options'] = 'account.move'

    def _format_report_include_line(self, res, value_dict, options):
        res['name'] = _('Accounts to adjust') if value_dict.get('report_include') else _('Excluded Accounts')
        res['columns'] = [{}, {}, {}, {}]

    # ACTIONS
    def toggle_provision(self, options, params):
        """Include/exclude an account from the provision."""
        account = self.env['account.account'].browse(int(params.get('account_id')))
        currency = self.env['res.currency'].browse(int(params.get('currency_id')))
        if currency in account.exclude_provision_currency_ids:
            account.exclude_provision_currency_ids -= currency
        else:
            account.exclude_provision_currency_ids += currency
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def view_revaluation_wizard(self, context):
        """Open the revaluation wizard."""
        form = self.env.ref('account_reports.view_account_multicurrency_revaluation_wizard', False)
        return {
            'name': _('Make Adjustment Entry'),
            'type': 'ir.actions.act_window',
            'res_model': "account.multicurrency.revaluation.wizard",
            'view_mode': "form",
            'view_id': form.id,
            'views': [(form.id, 'form')],
            'multi': "True",
            'target': "new",
            'context': context,
        }

    def view_currency(self, options, params=None):
        """Open the currency rate list."""
        id = params.get('id')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Currency Rates (%s)', self.env['res.currency'].browse(id).display_name),
            'views': [(False, 'list')],
            'res_model': 'res.currency.rate',
            'context': {**self.env.context, **{'default_currency_id': id}},
            'domain': [('currency_id', '=', id)],
        }

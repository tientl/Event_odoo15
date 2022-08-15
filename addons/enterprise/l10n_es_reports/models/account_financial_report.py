# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

from odoo.exceptions import UserError

from datetime import datetime


class AccountFinancialReportLine(models.Model):
    _inherit = 'account.financial.html.report.line'

    l10n_es_mod347_threshold = fields.Float("Mod.347 Partner Threshold", help="""
The threshold value, in EURO, to be applied on invoice journal items  grouped by partner in the Modelo 347 report.
Only the partners having a debit sum value strictly superior to the threshold over the fiscal year
will be taken into account in this report.
This feature is only supported/useful in spanish MOD347 report.""")

    def _parse_threshold_parameter(self, date):
        """ Parses the content of the l10n_es_mod347_threshold field, returning its
        value in company currency.
        """
        if self.l10n_es_mod347_threshold:
            threshold_currency = self.env["res.currency"].search([('name', '=', 'EUR')], limit=1)

            if not threshold_currency or not threshold_currency.active:
                raise UserError(_("Currency %s, used for a threshold in this report, is either nonexistent or inactive. Please create or activate it.", threshold_currency.name))

            company_currency = self.env.company.currency_id
            return threshold_currency._convert(self.l10n_es_mod347_threshold, company_currency, self.env.company, date)

    def _get_domain(self, options, financial_report):
        # OVERRIDE to filter out lines based on the threshold.
        domain = super()._get_domain(options, financial_report)
        if options.get('l10n_es_mod347_add_domain'):
            domain += options['l10n_es_mod347_add_domain']
        return domain

    def _get_options_with_threshold(self, options_list):
        ''' Helper used to filter out unfolded lines based on their total balance regarding the threshold computed
        on the fiscal year.
        :param options_list:    The report options list, first one being the current dates range, others being the
                                comparisons.
        :return:                A new options_list containing 'l10n_es_mod347_add_domain' to filter out the unfolded lines.
        '''
        new_options_list = []
        for i, options in enumerate(options_list):
            from_fy_dates = self.env.company.compute_fiscalyear_dates(fields.Date.from_string(options['date']['date_from']))
            to_fy_dates = self.env.company.compute_fiscalyear_dates(fields.Date.from_string(options['date']['date_to']))

            # Ignore the threshold if from and to dates belong to different fiscal years.
            if from_fy_dates != to_fy_dates:
                new_options_list.append(options)
                continue

            # Compute results for the fiscal year.
            fy_options = {**options, 'date': options['date'].copy()}
            fy_options['date'].update({
                'date_from': fields.Date.to_string(from_fy_dates['date_from']),
                'date_to': fields.Date.to_string(from_fy_dates['date_to']),
                'mode': 'range',
            })
            fy_results = super()._compute_amls_results([fy_options], self, sign=1)

            # Compute records to exclude per period.
            ids_to_exclude = []
            threshold = self._parse_threshold_parameter(from_fy_dates['date_to'])
            for groupby_key, display_name, formula_results in fy_results:
                balance = sum(formula_results.values())
                if abs(balance) <= threshold:
                    ids_to_exclude.append(groupby_key)

            if ids_to_exclude:
                new_options_list.append({**options, 'l10n_es_mod347_add_domain': [(self.groupby, 'not in', tuple(ids_to_exclude))]})
            else:
                new_options_list.append(options)
        return new_options_list

    def _compute_amls_results(self, options_list, calling_financial_report, sign=1, operator=None):
        # OVERRIDE to filter out lines that are under the threshold given by the 'l10n_es_mod347_threshold' field.
        if self.l10n_es_mod347_threshold:
            options_list = self._get_options_with_threshold(options_list)
        return super()._compute_amls_results(options_list, calling_financial_report, sign=sign, operator=operator)

    def _compute_sum(self, options_list, calling_financial_report):
        # OVERRIDE to filter out lines that are under the threshold given by the 'l10n_es_mod347_threshold' field.
        if self.l10n_es_mod347_threshold:
            options_list = self._get_options_with_threshold(options_list)
        return super()._compute_sum(options_list, calling_financial_report)

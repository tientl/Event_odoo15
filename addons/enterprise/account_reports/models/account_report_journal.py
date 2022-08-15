# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import api, fields, models
from odoo.tools.misc import get_lang


class AccountReportJournal(models.AbstractModel):
    _inherit = "report.account.report_journal"

    def _get_generic_tax_report_summary(self, data, journal_id):
        """
        Overridden to make use of the generic tax report computation
        Works by forcing the tax report to only work with the provided journal, then formatting the tax
        report lines to fit what we need in the template.
        The result is grouped by the country in which the tag exists in case of multivat environment.
        Returns a dictionary with the following structure:
        {
            Country : [
                {name, base_amount, tax_amount},
                {name, base_amount, tax_amount},
                {name, base_amount, tax_amount},
                ...
            ],
            Country : [
                {name, base_amount, tax_amount},
                {name, base_amount, tax_amount},
                {name, base_amount, tax_amount},
                ...
            ],
            ...
        }
        """
        if journal_id.type not in ('purchase', 'sale'):
            return False

        tax_report_options = self._get_generic_tax_report_options(journal_id, data)
        tax_report = self.env['account.generic.tax.report']
        tax_report_lines = tax_report.with_context(tax_report._set_context(tax_report_options))._get_lines(tax_report_options)

        tax_values = {}
        for tax_report_line in tax_report_lines:
            model, line_id = self.env['account.generic.tax.report']._parse_line_id(tax_report_line.get('id'))[-1][1:]
            if model == 'account.tax':
                tax_values[line_id] = {
                    'base_amount': tax_report_line['columns'][0]['no_format'],
                    'tax_amount': tax_report_line['columns'][1]['no_format'],
                }

        # Make the final data dict that will be used by the template, using the taxes information.
        taxes = self.env['account.tax'].browse(tax_values.keys())
        res = defaultdict(list)
        for tax in taxes:
            res[tax.country_id.name].append({
                'base_amount': tax_values[tax.id]['base_amount'],
                'tax_amount': tax_values[tax.id]['tax_amount'],
                'name': tax.name,
            })

        # Return the result, ordered by country name
        return dict(sorted(res.items()))

    def _get_tax_grids_summary(self, data, journal_id):
        """
        Fetches the details of all grids that have been used in the provided journal.
        The result is grouped by the country in which the tag exists in case of multivat environment.
        Returns a dictionary with the following structure:
        {
            Country : {
                tag_name: {+, -, impact},
                tag_name: {+, -, impact},
                tag_name: {+, -, impact},
                ...
            },
            Country : [
                tag_name: {+, -, impact},
                tag_name: {+, -, impact},
                tag_name: {+, -, impact},
                ...
            ],
            ...
        }
        """
        # We may want to display tax grids for cash basis journals, which are by default of type "general"
        if journal_id.type not in ('purchase', 'sale', 'general'):
            return False
        # Use the same option as we use to get the tax details, but this time to generate the query used to fetch the
        # grid information
        tax_report_options = self._get_generic_tax_report_options(journal_id, data)
        tables, where_clause, where_params = self.env['account.generic.tax.report']._query_get(tax_report_options)
        query = """
            WITH tag_info (country_name, tag_name, tag_sign, balance) as (
                SELECT
                    COALESCE(NULLIF(ir_translation.value, ''), country.name) country_name,
                    tag.name,
                    CASE WHEN tag.tax_negate IS TRUE THEN '-' ELSE '+' END,
                    SUM(COALESCE("account_move_line".balance, 0)
                        * CASE WHEN "account_move_line".tax_tag_invert THEN -1 ELSE 1 END
                        ) AS balance
                FROM account_account_tag tag
                JOIN account_account_tag_account_move_line_rel rel ON tag.id = rel.account_account_tag_id
                JOIN res_country country on country.id = tag.country_id
                LEFT JOIN ir_translation ON ir_translation.name = 'res.country,name' AND ir_translation.res_id = country.id AND ir_translation.type = 'model' AND ir_translation.lang = %s
                , """ + tables + """
                WHERE  """ + where_clause + """
                  AND applicability = 'taxes'
                  AND "account_move_line".id = rel.account_move_line_id
                GROUP BY country_name, tag.name, tag.tax_negate
            )
            SELECT
                country_name,
                REGEXP_REPLACE(tag_name, '^[+-]', '') AS name, -- Remove the sign from the grid name
                balance,
                tag_sign AS sign
            FROM tag_info
            ORDER BY country_name, name
        """
        lang = self.env.user.lang or get_lang(self.env).code
        self.env.cr.execute(query, [lang] + where_params)
        query_res = self.env.cr.fetchall()

        res = defaultdict(lambda: defaultdict(dict))
        for country_name, name, balance, sign in query_res:
            res[country_name][name][sign] = balance
            res[country_name][name]['impact'] = res[country_name][name].get('+', 0) - res[country_name][name].get('-', 0)

        return res

    @api.model
    def _get_report_values(self, docids, data=None):
        res = super()._get_report_values(docids, data)
        res['get_tax_grids'] = self._get_tax_grids_summary
        res['get_generic_tax_report_summary'] = self._get_generic_tax_report_summary
        return res

    def _get_generic_tax_report_options(self, journal_id, data):
        """
        Return an option dictionnary set to fetch the reports with the parameters needed for this journal.
        The important bits are the journals, date, and fetch the generic tax reports that contains all taxes.
        We also provide the information about wether to take all entries or only posted ones.
        """
        date_from = data['form'].get('date_from')
        date_to = data['form'].get('date_to')
        mode = 'range'
        if not date_to:
            date_to = fields.Date.context_today(self)
        if not date_from:
            mode = 'single'

        date_options = {
            'mode': mode,
            'strict_range': True,
            'date_from': date_from,
            'date_to': date_to
        }
        tax_report_options = self.env['account.generic.tax.report']._get_options()
        tax_report_options.update({
            'date': date_options,
            'journals': [{'id': journal_id.id, 'type': journal_id.type, 'selected': True}],
            'all_entries': False if data['form'].get('target_move', 'all') == 'posted' else True,
            'tax_report': 'generic',
            'fiscal_position': 'all',
            'multi_company': [{'id': journal_id.company_id.id, 'name': journal_id.company_id.name}],
        })
        return tax_report_options

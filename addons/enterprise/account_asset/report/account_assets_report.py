# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import format_date
from itertools import groupby
from collections import defaultdict

MAX_NAME_LENGTH = 50


class assets_report(models.AbstractModel):
    _inherit = 'account.report'
    _name = 'account.assets.report'
    _description = 'Account Assets Report'

    filter_date = {'mode': 'range', 'filter': 'this_year'}
    filter_all_entries = False
    filter_hierarchy = True
    filter_unfold_all = True

    def _get_report_name(self):
        return _('Depreciation Table Report')

    def _get_templates(self):
        templates = super(assets_report, self)._get_templates()
        templates['main_template'] = 'account_asset.main_template_asset_report'
        return templates

    def get_header(self, options):
        start_date = format_date(self.env, options['date']['date_from'])
        end_date = format_date(self.env, options['date']['date_to'])
        return [
            [
                {'name': ''},
                {'name': _('Characteristics'), 'colspan': 4},
                {'name': _('Assets'), 'colspan': 4},
                {'name': _('Depreciation'), 'colspan': 4},
                {'name': _('Book Value')},
            ],
            [
                {'name': ''},  # Description
                {'name': _('Acquisition Date'), 'class': 'text-center'},  # Characteristics
                {'name': _('First Depreciation'), 'class': 'text-center'},
                {'name': _('Method'), 'class': 'text-center'},
                {'name': _('Duration / Rate'), 'class': 'number', 'title': _('In percent.<br>For a linear method, the depreciation rate is computed per year.<br>For a declining method, it is the declining factor'), 'data-toggle': 'tooltip'},
                {'name': start_date, 'class': 'number'},  # Assets
                {'name': _('+'), 'class': 'number'},
                {'name': _('-'), 'class': 'number'},
                {'name': end_date, 'class': 'number'},
                {'name': start_date, 'class': 'number'},  # Depreciation
                {'name': _('+'), 'class': 'number'},
                {'name': _('-'), 'class': 'number'},
                {'name': end_date, 'class': 'number'},
                {'name': '', 'class': 'number'},  # Gross
            ],
        ]

    def _init_filter_hierarchy(self, options, previous_options=None):
        # overwrite because we don't depend on account.group
        if self.filter_hierarchy is not None:
            if previous_options and 'hierarchy' in previous_options:
                options['hierarchy'] = previous_options['hierarchy']
            else:
                options['hierarchy'] = self.filter_hierarchy

    def get_account_codes(self, account):
        return [(name, name) for name in self._get_account_group_with_company(account.code, account.company_id.id)[1:]]

    def _get_account_group(self, account_code, parent_group=None, group_dict=None):
        """ Get the list of parent groups for this account
        return: list containing the main group key, then the name of every group
                for this account, beginning by the more general, until the
                name of the account itself.
            This method is deprecated. Call instead _get_account_group_with_company
        """
        return self._get_account_group_with_company(account_code, self.env.company.id, parent_group, group_dict)

    def _with_context_company2code2account(self):
        if self.env.context.get('company2code2account') is not None:
            return self

        company2code2account = defaultdict(dict)
        for account in self.env['account.account'].search([]):
            company2code2account[account.company_id.id][account.code] = account

        return self.with_context(company2code2account=company2code2account)

    def _get_account_group_with_company(self, account_code, company_id, parent_group=None, group_dict=None):
        """ Get the list of parent groups for this account
        return: list containing the main group key, then the name of every group
                for this account, beginning by the more general, until the
                name of the account itself.
        """

        if not account_code:
            # This is used if there is no account_asset_id
            account_code = '##'
        group_dict = group_dict or self.env['account.report']._get_account_groups_for_asset_report()
        self = self._with_context_company2code2account()
        account_id = self.env.context['company2code2account'].get(company_id, {}).get(account_code)
        account_suffix = [] if parent_group else [account_id.display_name if account_id else _("No asset account")]
        for k, v in group_dict.items():
            key_split = k.split('-')
            account_code_short = account_code[:len(str(key_split[0]))]
            if not v.get('children') and account_code_short == k:
                return (parent_group or [k]) + [v['name']] + account_suffix
            elif v.get('children') and key_split[0] <= account_code_short <= key_split[1]:
                return self._get_account_group_with_company(
                    account_code_short,
                    company_id,
                    (parent_group or [k]) + [v['name']],
                    v['children']
                ) + account_suffix
        return (parent_group or [account_code[:2]]) + account_suffix

    def _get_rate_cached(self, from_currency, to_currency, company, date, cache):
        if from_currency == to_currency:
            return 1
        key = (from_currency, to_currency, company, date)
        if key not in cache:
            cache[key] = self.env['res.currency']._get_conversion_rate(*key)
        return cache[key]

    def _get_lines(self, options, line_id=None):
        self = self._with_context_company2code2account()
        options['self'] = self
        lines = []
        total = [0] * 9
        asset_lines = self._get_assets_lines(options)
        curr_cache = {}

        for company_id, company_asset_lines in groupby(asset_lines, key=lambda x: x['company_id']):
            parent_lines = []
            children_lines = defaultdict(list)
            company = self.env['res.company'].browse(company_id)
            company_currency = company.currency_id
            for al in company_asset_lines:
                if al['parent_id']:
                    children_lines[al['parent_id']] += [al]
                else:
                    parent_lines += [al]
            for al in parent_lines:
                if al['asset_method'] == 'linear' and al['asset_method_number']:  # some assets might have 0 depreciations because they dont lose value
                    total_months = int(al['asset_method_number']) * int(al['asset_method_period'])
                    months = total_months % 12
                    years = total_months // 12
                    asset_depreciation_rate = " ".join(part for part in [
                        years and _("%s y", years),
                        months and _("%s m", months),
                    ] if part)
                elif al['asset_method'] == 'linear':
                    asset_depreciation_rate = '0.00 %'
                else:
                    asset_depreciation_rate = ('{:.2f} %').format(float(al['asset_method_progress_factor']) * 100)

                al_currency = self.env['res.currency'].browse(al['asset_currency_id'])
                al_rate = self._get_rate_cached(al_currency, company_currency, company, al['asset_acquisition_date'], curr_cache)

                depreciation_opening = company_currency.round(al['depreciated_start'] * al_rate) - company_currency.round(al['depreciation'] * al_rate)
                depreciation_closing = company_currency.round(al['depreciated_end'] * al_rate)
                depreciation_minus = 0.0

                opening = (al['asset_acquisition_date'] or al['asset_date']) < fields.Date.to_date(options['date']['date_from'])
                asset_opening = company_currency.round(al['asset_original_value'] * al_rate) if opening else 0.0
                asset_add = 0.0 if opening else company_currency.round(al['asset_original_value'] * al_rate)
                asset_minus = 0.0

                if al['import_depreciated']:
                    asset_opening += asset_add
                    asset_add = 0
                    depreciation_opening += al['import_depreciated']
                    depreciation_closing += al['import_depreciated']

                for child in children_lines[al['asset_id']]:
                    child_currency = self.env['res.currency'].browse(child['asset_currency_id'])
                    child_rate = self._get_rate_cached(child_currency, company_currency, company, child['asset_acquisition_date'], curr_cache)

                    depreciation_opening += company_currency.round(child['depreciated_start'] * child_rate) - company_currency.round(child['depreciation'] * child_rate)
                    depreciation_closing += company_currency.round(child['depreciated_end'] * child_rate)

                    opening = (child['asset_acquisition_date'] or child['asset_date']) < fields.Date.to_date(options['date']['date_from'])
                    asset_opening += company_currency.round(child['asset_original_value'] * child_rate) if opening else 0.0
                    asset_add += 0.0 if opening else company_currency.round(child['asset_original_value'] * child_rate)

                depreciation_add = depreciation_closing - depreciation_opening
                asset_closing = asset_opening + asset_add

                if al['asset_state'] == 'close' and al['asset_disposal_date'] and al['asset_disposal_date'] <= fields.Date.to_date(options['date']['date_to']):
                    depreciation_minus = depreciation_closing
                    # depreciation_opening and depreciation_add are computed from first_move (assuming it is a depreciation move),
                    # but when previous condition is True and first_move and last_move are the same record, then first_move is not a
                    # depreciation move.
                    # In that case, depreciation_opening and depreciation_add must be corrected.
                    if al['first_move_id'] == al['last_move_id']:
                        depreciation_opening = depreciation_closing
                        depreciation_add = 0
                    depreciation_closing = 0.0
                    asset_minus = asset_closing
                    asset_closing = 0.0

                asset_gross = asset_closing - depreciation_closing

                total = [x + y for x, y in zip(total, [asset_opening, asset_add, asset_minus, asset_closing, depreciation_opening, depreciation_add, depreciation_minus, depreciation_closing, asset_gross])]

                asset_line_id = self._build_line_id([
                    (None, 'account.account', al['account_id']),
                    (None, 'account.asset', al['asset_id']),
                ])
                name = str(al['asset_name'])
                line = {
                    'id': asset_line_id,
                    'level': 1,
                    'name': name,
                    'account_code': al['account_code'],
                    'columns': [
                        {'name': al['asset_acquisition_date'] and format_date(self.env, al['asset_acquisition_date']) or '', 'no_format_name': ''},  # Characteristics
                        {'name': al['asset_date'] and format_date(self.env, al['asset_date']) or '', 'no_format_name': ''},
                        {'name': (al['asset_method'] == 'linear' and _('Linear')) or (al['asset_method'] == 'degressive' and _('Declining')) or _('Dec. then Straight'), 'no_format_name': ''},
                        {'name': asset_depreciation_rate, 'no_format_name': ''},
                        {'name': self.format_value(asset_opening), 'no_format_name': asset_opening},  # Assets
                        {'name': self.format_value(asset_add), 'no_format_name': asset_add},
                        {'name': self.format_value(asset_minus), 'no_format_name': asset_minus},
                        {'name': self.format_value(asset_closing), 'no_format_name': asset_closing},
                        {'name': self.format_value(depreciation_opening), 'no_format_name': depreciation_opening},  # Depreciation
                        {'name': self.format_value(depreciation_add), 'no_format_name': depreciation_add},
                        {'name': self.format_value(depreciation_minus), 'no_format_name': depreciation_minus},
                        {'name': self.format_value(depreciation_closing), 'no_format_name': depreciation_closing},
                        {'name': self.format_value(asset_gross), 'no_format_name': asset_gross},  # Gross
                    ],
                    'unfoldable': False,
                    'unfolded': False,
                    'caret_options': 'account.asset.line',
                    'account_id': al['account_id']
                }
                if len(name) >= MAX_NAME_LENGTH:
                    line.update({'title_hover': name})
                lines.append(line)
        lines.append({
            'id': 'total',
            'level': 0,
            'name': _('Total'),
            'columns': [
                {'name': ''},  # Characteristics
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': self.format_value(total[0])},  # Assets
                {'name': self.format_value(total[1])},
                {'name': self.format_value(total[2])},
                {'name': self.format_value(total[3])},
                {'name': self.format_value(total[4])},  # Depreciation
                {'name': self.format_value(total[5])},
                {'name': self.format_value(total[6])},
                {'name': self.format_value(total[7])},
                {'name': self.format_value(total[8])},  # Gross
            ],
            'unfoldable': False,
            'unfolded': False,
        })
        return lines

    def _get_assets_lines(self, options):
        "Get the data from the database"

        self.env['account.move.line'].check_access_rights('read')
        self.env['account.asset'].check_access_rights('read')

        where_account_move = " AND state != 'cancel'"
        if not options.get('all_entries'):
            where_account_move = " AND state = 'posted'"

        sql = """
                -- remove all the moves that have been reversed from the search
                CREATE TEMPORARY TABLE IF NOT EXISTS temp_account_move () INHERITS (account_move) ON COMMIT DROP;
                INSERT INTO temp_account_move SELECT move.*
                FROM ONLY account_move move
                LEFT JOIN ONLY account_move reversal ON reversal.reversed_entry_id = move.id
                WHERE reversal.id IS NULL AND move.asset_id IS NOT NULL AND move.company_id in %(company_ids)s;

                SELECT asset.id as asset_id,
                       asset.parent_id as parent_id,
                       asset.name as asset_name,
                       asset.original_value as asset_original_value,
                       asset.currency_id as asset_currency_id,
                       COALESCE(asset.first_depreciation_date_import, asset.first_depreciation_date) as asset_date,
                       asset.already_depreciated_amount_import as import_depreciated,
                       asset.disposal_date as asset_disposal_date,
                       asset.acquisition_date as asset_acquisition_date,
                       asset.method as asset_method,
                       (
                           COALESCE(account_move_count.count, 0)
                           + COALESCE(asset.depreciation_number_import, 0)
                           - CASE WHEN asset.prorata THEN 1 ELSE 0 END
                       ) as asset_method_number,
                       asset.method_period as asset_method_period,
                       asset.method_progress_factor as asset_method_progress_factor,
                       asset.state as asset_state,
                       account.code as account_code,
                       account.name as account_name,
                       account.id as account_id,
                       account.company_id as company_id,
                       COALESCE(first_move.asset_depreciated_value, move_before.asset_depreciated_value, 0.0) as depreciated_start,
                       COALESCE(first_move.asset_remaining_value, move_before.asset_remaining_value, 0.0) as remaining_start,
                       COALESCE(last_move.asset_depreciated_value, move_before.asset_depreciated_value, 0.0) as depreciated_end,
                       COALESCE(last_move.asset_remaining_value, move_before.asset_remaining_value, 0.0) as remaining_end,
                       COALESCE(first_move.amount_total, 0.0) as depreciation,
                       COALESCE(first_move.id, move_before.id) as first_move_id,
                       COALESCE(last_move.id, move_before.id) as last_move_id
                FROM account_asset as asset
                LEFT JOIN account_account as account ON asset.account_asset_id = account.id
                LEFT JOIN (
                    SELECT
                        COUNT(*) as count,
                        asset_id
                    FROM temp_account_move
                    WHERE asset_value_change != 't'
                    GROUP BY asset_id
                ) account_move_count ON asset.id = account_move_count.asset_id

                LEFT OUTER JOIN (
                    SELECT DISTINCT ON (asset_id)
                        id,
                        asset_depreciated_value,
                        asset_remaining_value,
                        amount_total,
                        asset_id
                    FROM temp_account_move m
                    WHERE date >= %(date_from)s AND date <= %(date_to)s {where_account_move}
                    ORDER BY asset_id, date, id DESC
                ) first_move ON first_move.asset_id = asset.id

                LEFT OUTER JOIN (
                    SELECT DISTINCT ON (asset_id)
                        id,
                        asset_depreciated_value,
                        asset_remaining_value,
                        amount_total,
                        asset_id
                    FROM temp_account_move m
                    WHERE date >= %(date_from)s AND date <= %(date_to)s {where_account_move}
                    ORDER BY asset_id, date DESC, id DESC
                ) last_move ON last_move.asset_id = asset.id

                LEFT OUTER JOIN (
                    SELECT DISTINCT ON (asset_id)
                        id,
                        asset_depreciated_value,
                        asset_remaining_value,
                        amount_total,
                        asset_id
                    FROM temp_account_move m
                    WHERE date <= %(date_from)s {where_account_move}
                    ORDER BY asset_id, date DESC, id DESC
                ) move_before ON move_before.asset_id = asset.id

                WHERE asset.company_id in %(company_ids)s
                AND asset.acquisition_date <= %(date_to)s
                AND (asset.disposal_date >= %(date_from)s OR asset.disposal_date IS NULL)
                AND asset.state not in ('model', 'draft')
                AND asset.asset_type = 'purchase'
                AND asset.active = 't'

                ORDER BY account.code, asset.acquisition_date;
            """.format(where_account_move=where_account_move)

        date_to = options['date']['date_to']
        date_from = options['date']['date_from']
        if options.get('multi_company', False):
            company_ids = tuple(self.env.companies.ids)
        else:
            company_ids = tuple(self.env.company.ids)

        self.flush()
        self.env.cr.execute(sql, {'date_to': date_to, 'date_from': date_from, 'company_ids': company_ids})
        results = self.env.cr.dictfetchall()
        self.env.cr.execute("DROP TABLE temp_account_move")  # Because tests are run in the same transaction, we need to clean here the SQL INHERITS
        return results

    def open_asset(self, options, params=None):
        model, active_id = self._get_model_info_from_id(params.get('id'))
        asset = self.env[model].browse(active_id)
        return asset.open_asset(['form'])

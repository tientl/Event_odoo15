# -*- coding: utf-8 -*-
from contextlib import contextmanager
from unittest.mock import patch
import copy

from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.misc import formatLang


class TestAccountReportsCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company_data_2['company'].currency_id = cls.currency_data['currency']
        cls.company_data_2['currency'] = cls.currency_data['currency']

    @classmethod
    def _init_options(cls, report, date_from, date_to, default_options=None):
        ''' Create new options at a certain date.
        :param report:          The report.
        :param filter:          One of the following values: ('today', 'custom', 'this_month', 'this_quarter', 'this_year', 'last_month', 'last_quarter', 'last_year').
        :param date_from:       A datetime object or False.
        :param date_to:         A datetime object.
        :return:                The newly created options.
        '''
        if not default_options:
            default_options = {}

        return report._get_options({
            'date': {
                'date_from': date_from.strftime(DEFAULT_SERVER_DATE_FORMAT),
                'date_to': date_to.strftime(DEFAULT_SERVER_DATE_FORMAT),
                'filter': 'custom',
                'mode': report.filter_date.get('mode', 'range'),
            },
            **default_options,
        })

    def _update_comparison_filter(self, options, report, comparison_type, number_period, date_from=None, date_to=None):
        ''' Modify the existing options to set a new filter_comparison.
        :param options:         The report options.
        :param report:          The report.
        :param comparison_type: One of the following values: ('no_comparison', 'custom', 'previous_period', 'previous_year').
        :param number_period:   The number of period to compare.
        :param date_from:       A datetime object for the 'custom' comparison_type.
        :param date_to:         A datetime object the 'custom' comparison_type.
        :return:                The newly created options.
        '''
        report._init_filter_comparison(options, {**options, 'comparison': {
            'date_from': date_from and date_from.strftime(DEFAULT_SERVER_DATE_FORMAT),
            'date_to': date_to and date_to.strftime(DEFAULT_SERVER_DATE_FORMAT),
            'filter': comparison_type,
            'number_period': number_period,
        }})
        return options

    def _update_multi_selector_filter(self, options, option_key, selected_ids):
        ''' Modify a selector in the options to select .
        :param options:         The report options.
        :param option_key:      The key to the option.
        :param selected_ids:    The ids to be selected.
        :return:                The newly created options.
        '''
        new_options = copy.deepcopy(options)
        for c in new_options[option_key]:
            c['selected'] = c['id'] in selected_ids
        return new_options

    @contextmanager
    def debug_mode(self, report):
        Report_user_has_groups = type(report).user_has_groups

        def user_has_groups(self, groups):
            if groups == 'base.group_no_one':
                return True
            return Report_user_has_groups(self, groups)

        with patch.object(type(report), 'user_has_groups', user_has_groups):
            yield

    def assertHeadersValues(self, headers, expected_headers):
        ''' Helper to compare the headers returned by the _get_table method
        with some expected results.
        An header is a row of columns. Then, headers is a list of list of dictionary.
        :param headers:             The headers to compare.
        :param expected_headers:    The expected headers.
        :return:
        '''
        # Check number of header lines.
        self.assertEqual(len(headers), len(expected_headers))

        for header, expected_header in zip(headers, expected_headers):
            # Check number of columns.
            self.assertEqual(len(header), len(expected_header))

            for i, column in enumerate(header):
                # Check name.
                self.assertEqual(column['name'], expected_header[i][0])
                # Check colspan.
                self.assertEqual(column.get('colspan', 1), expected_header[i][1])

    def assertLinesValues(self, lines, columns, expected_values, currency_map={}):
        ''' Helper to compare the lines returned by the _get_lines method
        with some expected results.
        :param lines:               See _get_lines.
        :param columns:             The columns index.
        :param expected_values:     A list of iterables.
        :param currency_map:        A map mapping each column_index to some extra options to test the lines:
            - currency:             The currency to be applied on the column.
            - currency_code_index:  The index of the column containing the currency code.
        '''

        # Compare the table length to see if any line is missing
        self.assertEqual(len(lines), len(expected_values))

        # Compare cell by cell the current value with the expected one.
        i = 0
        to_compare_list = []
        for line in lines:
            j = 0
            compared_values = [[], []]
            for index in columns:
                expected_value = expected_values[i][j]

                if index == 0:
                    current_value = line['name']
                else:
                    colspan = line.get('colspan', 1)
                    line_index = index - colspan
                    if line_index < 0:
                        current_value = ''
                    else:
                        current_value = line['columns'][line_index].get('name', '')

                currency_data = currency_map.get(index, {})
                used_currency = None
                if 'currency' in currency_data:
                    used_currency = currency_data['currency']
                elif 'currency_code_index' in currency_data:
                    currency_code = line['columns'][currency_data['currency_code_index'] - 1].get('name', '')
                    if currency_code:
                        used_currency = self.env['res.currency'].search([('name', '=', currency_code)], limit=1)
                        assert used_currency, "Currency having name=%s not found." % currency_code
                if not used_currency:
                    used_currency = self.env.company.currency_id

                if type(expected_value) in (int, float) and type(current_value) == str:
                    expected_value = formatLang(self.env, expected_value, currency_obj=used_currency)

                compared_values[0].append(current_value)
                compared_values[1].append(expected_value)

                j += 1
            to_compare_list.append(compared_values)
            i += 1

        errors = []
        for i, to_compare in enumerate(to_compare_list):
            if to_compare[0] != to_compare[1]:
                errors += [
                    "\n==== Differences at index %s ====" % str(i),
                    "Current Values:  %s" % str(to_compare[0]),
                    "Expected Values: %s" % str(to_compare[1]),
                ]
        if errors:
            self.fail('\n'.join(errors))

    @classmethod
    def _create_tax_report_line(cls, name, report, tag_name=None, parent_line=None, sequence=None, code=None, formula=None,
                                carry_over_condition=None, is_carryover_used_in_balance=False,
                                carry_over_destination_line_id=False, is_carryover_persistent=True):
        """ Creates a tax report line
        """
        create_vals = {
            'name': name,
            'report_id': report.id,
        }
        if tag_name:
            create_vals['tag_name'] = tag_name
        if parent_line:
            create_vals['parent_id'] = parent_line.id
        if sequence != None:
            create_vals['sequence'] = sequence
        if code:
            create_vals['code'] = code
        if formula:
            create_vals['formula'] = formula
        if carry_over_condition:
            create_vals['carry_over_condition_method'] = carry_over_condition
        if carry_over_destination_line_id:
            create_vals['carry_over_destination_line_id'] = carry_over_destination_line_id
        create_vals['is_carryover_used_in_balance'] = is_carryover_used_in_balance
        create_vals['is_carryover_persistent'] = is_carryover_persistent

        return cls.env['account.tax.report.line'].create(create_vals)

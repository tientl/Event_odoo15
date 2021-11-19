# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from odoo import fields, models, _
from odoo.tools.float_utils import float_compare, float_repr
from odoo.exceptions import UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta

class ReportAccountFinancialReport(models.Model):
    _inherit = "account.financial.html.report"

    def _get_reports_buttons(self, options):
        res = super()._get_reports_buttons(options)
        if self._get_report_country_code(options) == 'LU':
            res.append({'name': _('XML'), 'sequence': 3, 'action': 'l10n_lu_open_report_export_wizard'})
        return res

    def _get_lu_reports(self):
        return {
            self.env.ref("l10n_lu_reports.account_financial_report_l10n_lu_bs").id : 'CA_BILAN',
            self.env.ref("l10n_lu_reports.account_financial_report_l10n_lu_bs_abr").id : 'CA_BILANABR',
            self.env.ref("l10n_lu_reports.account_financial_report_l10n_lu_pl").id : 'CA_COMPP',
            self.env.ref("l10n_lu_reports.account_financial_report_l10n_lu_pl_abr").id : 'CA_COMPPABR'
        }

    def _is_lu_electronic_report(self, options):
        return self.id in self._get_lu_reports().keys()

    def _get_lu_electronic_report_values(self, options):

        def _format_amount(amount):
            return float_repr(amount, 2).replace('.', ',') if amount else '0,00'

        values = {}

        def _report_useful_fields(amount, field, parent_field, required):
            """Only reports fields containing values or that are required."""
            # All required fields are always reported; all others reported only if different from 0.00.
            if float_compare(amount, 0.0, 2) != 0 or required:
                values.update({field: {'value': _format_amount(amount), 'field_type': 'number'}})
                # The parent needs to be added even if at 0, if some child lines are filled in
                if parent_code and not values.get(parent_code):
                    values.update({parent_field: {'value': '0,00', 'field_type': 'number'}})

        lu_template_values = super()._get_lu_electronic_report_values(options)

        # Add comparison filter to get data from last year
        self._init_filter_comparison(options, {**options, 'comparison': {
            'filter': 'same_last_year',
            'number_period': 1,
        }})

        lines = self._get_table(options)[1]

        ReportLine = self.env['account.financial.html.report.line']
        date_from = fields.Date.from_string(options['date'].get('date_from'))
        date_to = fields.Date.from_string(options['date'].get('date_to'))
        values.update({
            '01': {'value': date_from.strftime("%d/%m/%Y"), 'field_type': 'char'},
            '02': {'value': date_to.strftime("%d/%m/%Y"), 'field_type': 'char'},
            '03': {'value': self.env.company.currency_id.name, 'field_type': 'char'}
        })

        # we only need `account.financial.html.report.line` record's IDs and line['id'] could hold account.account
        # record's IDs as well. Such can be identified by `financial_group_line_id` in line dictionary's key. So,
        # below first condition filters those lines and second one filters lines having ID such as `total_*`
        for line in filter(lambda l: 'financial_group_line_id' not in l and isinstance(l.get('id'), int), lines):
            # financial report's `code` would contain alpha-numeric string like `LU_BS_XXX/LU_BSABR_XXX`
            # where characters at last three positions will be digits, hence we split with `_`
            # and build dictionary having `code` as dictionary key
            split_line_code = (ReportLine.browse(line['id']).code or '').split('_') or []
            columns = line['columns']
            # since we have enabled comparison by default, `columns` element will atleast have two dictionary items.
            # First dict will be holding current year's balance and second one will be holding previous year's balance.
            if len(split_line_code) > 2:
                parent_code = None
                parent_id = ReportLine.browse(line['id']).parent_id
                if parent_id and parent_id.code:
                    parent_split_code = parent_id.code.split('_')
                    if len(parent_split_code) > 2:
                        parent_code = parent_split_code[2]

                required = line['level'] == 0  # Required fields all have level 0
                # current year balance
                _report_useful_fields(columns[0]['no_format'], split_line_code[2], parent_code, required)
                # previous year balance
                _report_useful_fields(columns[1]['no_format'], str(int(split_line_code[2]) + 1), parent_code and str(int(parent_code) + 1), required)

        lu_template_values.update({
            'forms': [{
                'declaration_type': self._get_lu_reports()[self.id],
                'year': date_from.year,
                'period': "1",
                'field_values': values
            }]
        })
        return lu_template_values

    def get_xml(self, options):
        if not self._is_lu_electronic_report(options):
            return super().get_xml(options)

        self._lu_validate_ecdf_prefix()

        lu_template_values = self._get_lu_electronic_report_values(options)

        rendered_content = self.env.ref('l10n_lu_reports.l10n_lu_electronic_report_template_2_0')._render(lu_template_values)
        content = "\n".join(re.split(r'\n\s*\n', rendered_content))
        self._lu_validate_xml_content(content)

        return "<?xml version='1.0' encoding='UTF-8'?>" + content

    def _get_lu_xml_2_0_report_values(self, options, references=False):
        """Returns the formatted report values for this financial report.
           (Balance sheet: https://ecdf-developer.b2g.etat.lu/ecdf/forms/popup/CA_BILAN_COMP/2020/en/2/preview),
            Profit&Loss: https://ecdf-developer.b2g.etat.lu/ecdf/forms/popup/CA_COMPP_COMP/2020/en/2/preview)
           Adds the possibility to add references to the report and the form model number to
           _get_lu_electronic_report_values.

           :param options: the report options
           :param references: whether the annotations on the financial report should be added to the report as references
           :returns: the formatted report values
        """
        def _get_references():
            """
            This returns the annotations on all financial reports, linked to the corresponding report reference field.
            These will be used as references in the report.
            """
            references = {}
            names = {}
            notes = self.env['account.report.manager'].search([
                ('company_id', '=', self.env.company.id),
                ('financial_report_id', '=', self.id)
            ]).footnotes_ids
            for note in notes:
                # for footnotes on accounts on financial reports, the line field will be:
                # 'financial_report_group_xxx_yyy', with xxx the line id and yyy the account id
                split = note.line.split('_')
                if len(split) > 1 and split[-2].isnumeric() and split[-1].isnumeric():
                    line = self.env['account.financial.html.report.line'].search([('id', '=', split[-2])], limit=1)
                    code = re.search(r'\d+', str(line.code))
                    if code:
                        # References in the eCDF report have codes equal to the report code of the referred account + 1000
                        code = str(int(code.group()) + 1000)
                        references[code] = {'value': note.text, 'field_type': 'char'}
                        names[code] = self.env['account.account'].search([("id", "=", split[-1])]).mapped('code')[0]
            return references, names

        lu_template_values = self._get_lu_electronic_report_values(options)
        for form in lu_template_values['forms']:
            if references:
                references, names = _get_references()
                # Only add those references on accounts with reported values (for the current or previous year);
                # the reference has an eCDF code equal to the report code of the referred account for the current year + 1000,
                # ot equal to the report code of the ref. account for the previous year + 999
                references = {r: references[r] for r in references
                              if str(int(r) - 1000) in form['field_values'] or str(int(r) - 999) in form['field_values']}
                names = {r: names[r] for r in references
                         if str(int(r) - 1000) in form['field_values'] or str(int(r) - 999) in form['field_values']}
                # Check the length of the references <= 10 (XML report limit)
                if any([len(r['value']) > 10 for r in references.values()]):
                    raise UserError(
                        _("Some references are not in the requested format (max. 10 characters):") + "\n    " +
                        "\n    ".join([names[i[0]] + ": " + i[1]['value'] for i in references.items() if len(i[1]['value']) > 10]) +
                        "\n" + _("Cannot export them.")
                    )
                for ref in references:
                    form['field_values'].update({ref: references[ref]})
            model = 2 if form['year'] == 2020 else 1
            form['model'] = model
        return lu_template_values['forms']

    def l10n_lu_open_report_export_wizard(self, options):
        """ Creates a new export wizard for this report."""
        new_context = self.env.context.copy()
        new_context['account_report_generation_options'] = options
        # When exporting from the balance sheet, the date_from must be adjusted
        if options['date']['mode'] == 'single':
            date_from = datetime.strptime(options['date']['date_to'], '%Y-%m-%d') + relativedelta(years=-1, days=1)
            new_context['account_report_generation_options']['date']['date_from'] = date_from.strftime('%Y-%m-%d')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Export'),
            'view_mode': 'form',
            'res_model': 'l10n_lu.generate.accounts.report',
            'target': 'new',
            'views': [[self.env.ref('l10n_lu_reports.view_l10n_lu_generate_accounts_report').id, 'form']],
            'context': new_context,
        }

# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare
from ...l10n_lu_reports.models.l10n_lu_tax_report_data import VAT_MANDATORY_FIELDS

class L10nLuGenerateTaxReport(models.TransientModel):
    _inherit = 'l10n_lu.generate.tax.report'
    _description = 'Generate Annual VAT Report'

    def _get_account_code(self, ln):
        model, active_id = self.env['account.report']._get_model_info_from_id(ln['id'])
        if model == 'account.account':
            account_code = self.env['account.account'].browse(active_id).code
            return account_code
        return False

    def _get_account_name(self, ln):
        model, active_id = self.env['account.report']._get_model_info_from_id(ln['id'])
        return self.env['account.account'].browse(active_id).name

    def _add_expenditures(self, data, lu_annual_report):
        expenditures = []
        for data_dict in data.get('detailed_lines', []):
            report_line = {
                'report_id': lu_annual_report.id,
                'report_section_411': data_dict['detail'],
                'report_section_412': data_dict['bus_base_amount'],
                'report_section_413': data_dict['bus_VAT'],
            }
            expenditures.append(report_line)
        return expenditures

    def _add_yearly_fields(self, data, form):
        form_fields = list(filter(lambda x: x.startswith('report_section'), data.fields_get().keys()))
        # add numeric fields
        for field in form_fields:
            code = field.split('_')[2]
            val = data[f"report_section_{code}"]
            if val or code in VAT_MANDATORY_FIELDS and isinstance(val, float):
                form['field_values'][code] = {'value': data[f"report_section_{code}"], 'field_type': 'float'}

        char_fields = {
            '206': ['007'],
            '229': ['100'],
            '264': ['265', '266', '267', '268'],
            '273': ['274', '275', '276', '277'],
            '278': ['279', '280', '281', '282'],
            '318': ['319', '320'],
            '321': ['322', '323'],
            '357': ['358', '359'],
            '387': ['388'],
        }
        for field in char_fields:
            if data[f"report_section_{field}"] and any(data[f"report_section_{related_fields}"] for related_fields in char_fields[field]):
                form['field_values'][field] = {'value': data[f"report_section_{field}"], 'field_type': 'char'}
            else:
                form['field_values'].pop(field, None)

        if data.report_section_389 and not data.report_section_010:
            raise ValidationError(_("The field 010 in 'Other Assimilated Supplies' is mandatory if you fill in the field 389 in 'Appendix B'. Field 010 must be equal to field 389"))
        if data.report_section_369 or data.report_section_368:
            if data.report_section_368 < data.report_section_369:
                raise ValidationError(_("The field 369 must be smaller than field 368 (Appendix B)."))
            elif not data.report_section_369 or not data.report_section_368:
                raise ValidationError(_("Both fields 369 and 368 must be either filled in or left empty (Appendix B)."))
        if data.report_section_388 and not data.report_section_387:
            raise ValidationError(_("The field 387 must be filled in if field 388 is filled in (Appendix B)."))
        if data.report_section_387 and not data.report_section_388:
            raise ValidationError(_("The field 388 must be filled in if field 387 is filled in (Appendix B)."))

        if data.report_section_163 and data.report_section_165 and not data.report_section_164:
            form['field_values']['164'] = {'value': data.report_section_163 - data.report_section_165, 'field_type': 'float'}
        elif data.report_section_163 and data.report_section_164 and not data.report_section_165:
            form['field_values']['165'] = {'value': data.report_section_163 - data.report_section_164, 'field_type': 'float'}
        elif data.report_section_163:
            raise ValidationError(_("Fields 164 and 165 are mandatory when 163 is filled in and must add up to field 163 (Appendix E)."))

        if '361' not in form['field_values']:
            form['field_values']['361'] = form['field_values']['414']
        if '362' not in form['field_values']:
            form['field_values']['362'] = form['field_values']['415']
        if float_compare(form['field_values']['361']['value'], 0.0, 2) == 0 and '192' not in form['field_values']:
            form['field_values']['192'] = form['field_values']['361']
        if float_compare(form['field_values']['362']['value'], 0.0, 2) == 0 and '193' not in form['field_values']:
            form['field_values']['193'] = form['field_values']['362']

        # Add appendix to operational expenditures
        expenditures_table = list()
        for appendix in data.appendix_ids:
            report_line = {}
            report_line['411'] = {'value': appendix.report_section_411, 'field_type': 'char'}
            report_line['412'] = {'value': appendix.report_section_412, 'field_type': 'float'}
            report_line['413'] = {'value': appendix.report_section_413, 'field_type': 'float'}
            expenditures_table.append(report_line)
        if expenditures_table:
            form['tables'] = [expenditures_table]

        return form

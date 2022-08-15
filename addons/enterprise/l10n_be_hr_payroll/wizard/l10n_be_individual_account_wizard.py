# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import logging
import io
import zipfile

from collections import OrderedDict
from odoo import api, fields, models, _
from odoo.fields import Datetime
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class L10nBeIndividualAccountWizard(models.TransientModel):
    _name = 'l10n_be.individual.account.wizard'
    _description = 'HR Individual Account Report By Employee'

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != "BE":
            raise UserError(_('You must be logged in a Belgian company to use this feature'))
        return super().default_get(field_list)

    def _get_selection(self):
        current_year = datetime.datetime.now().year
        return [(str(i), i) for i in range(1990, current_year + 1)]

    year = fields.Selection(
        selection='_get_selection', string='Year', required=True,
        default=lambda x: str(datetime.datetime.now().year - 1))

    @api.model
    def _payroll_documents_enabled(self):
        return False

    def _get_rendering_data(self, year, employee_ids):
        employees = self.env['hr.employee'].browse(employee_ids)

        payslips = self.env['hr.payslip'].search([
            ('employee_id', 'in', employees.ids),
            ('state', 'in', ['done', 'paid']),
            ('date_from', '>=', Datetime.now().replace(month=1, day=1, year=year)),
            ('date_from', '<=', Datetime.now().replace(month=12, day=31, year=year)),
            '|',
            ('struct_id.country_id', '=', False),
            ('struct_id.country_id.code', '=', "BE"),
        ])
        employees = payslips.employee_id
        lines = payslips.line_ids.filtered(lambda l: l.salary_rule_id.appears_on_payslip)
        payslip_rules = [(rule.code, rule.sequence) for rule in lines.salary_rule_id]
        payslip_rules = sorted(payslip_rules, key=lambda x: x[1])
        worked_days = payslips.worked_days_line_ids

        result = {
            employee: {
                'rules': OrderedDict(
                    (rule[0], {
                        'year': {'name': False, 'total': 0},
                        'month': {m: {'name': False, 'total': 0} for m in range(12)},
                        'quarter': {q: {'name': False, 'total': 0} for q in range(4)}
                    }) for rule in payslip_rules),
                'worked_days': {
                    code: {
                        'year': {'name': False, 'number_of_days': 0, 'number_of_hours': 0},
                        'month': {m: {'name': False, 'number_of_days': 0, 'number_of_hours': 0} for m in range(12)},
                        'quarter': {q: {'name': False, 'number_of_days': 0, 'number_of_hours': 0} for q in range(4)}
                    } for code in worked_days.mapped('code')
                }
            } for employee in employees
        }

        for line in lines:
            rule = result[line.employee_id]['rules'][line.salary_rule_id.code]
            month = line.slip_id.date_from.month - 1
            rule['month'][month]['name'] = line.name
            rule['month'][month]['total'] += line.total
            rule['quarter'][(month) // 3]['name'] = line.name
            rule['quarter'][(month) // 3]['total'] += line.total
            rule['year']['name'] = line.name
            rule['year']['total'] += line.total

            rule['month'][month]['total'] = round(rule['month'][month]['total'], 2)
            rule['quarter'][(month) // 3]['total'] = round(rule['quarter'][(month) // 3]['total'], 2)
            rule['year']['total'] = round(rule['year']['total'], 2)

        for worked_day in worked_days:
            work = result[worked_day.payslip_id.employee_id]['worked_days'][worked_day.code]
            month = worked_day.payslip_id.date_from.month - 1

            work['month'][month]['name'] = worked_day.name
            work['month'][month]['number_of_days'] += worked_day.number_of_days
            work['month'][month]['number_of_hours'] += worked_day.number_of_hours
            work['quarter'][(month) // 3]['name'] = worked_day.name
            work['quarter'][(month) // 3]['number_of_days'] += worked_day.number_of_days
            work['quarter'][(month) // 3]['number_of_hours'] += worked_day.number_of_hours
            work['year']['name'] = worked_day.name
            work['year']['number_of_days'] += worked_day.number_of_days
            work['year']['number_of_hours'] += worked_day.number_of_hours

        return result

    def print_report(self):
        self.ensure_one()
        return {
            'name': 'Export Individual Accounts',
            'type': 'ir.actions.act_url',
            'url': '/export/individual_accounts/%s/%s' % (self.id, self.env.company.id),
        }

    def _generate_files(self, company):
        self.ensure_one()
        employee_ids = self.env['hr.employee'].search([('company_id', '=', company.id)]).ids
        rendering_data = self._get_rendering_data(int(self.year), employee_ids)
        template_sudo = self.env.ref('l10n_be_hr_payroll.action_report_individual_account').sudo()

        pdf_files = []
        sheet_count = len(rendering_data)
        counter = 1
        for employee, employee_data in rendering_data.items():
            _logger.info('Printing Individual Account Sheet (%s/%s)', counter, sheet_count)
            counter += 1
            employee_lang = employee.sudo().address_home_id.lang
            # This actually has an impact, don't remove this line
            context = {'lang': employee_lang}
            sheet_filename = _('%s-individual-account-%s', employee.name, self.year)
            sheet_file, dummy = template_sudo.with_context(lang=employee_lang)._render_qweb_pdf(employee.id, data={
                'year': int(self.year),
                'employee_data': {employee: employee_data},
            })
            pdf_files.append((employee, sheet_filename, sheet_file))
        return pdf_files

    def _post_process_files(self, files):
        return

    def _process_files(self, files, default_filename='Individual Account', post_process=False):
        """Groups files into a single file
        :param files: list of tuple (employee, filename, data)
        :return: tuple filename, encoded data
        """
        if post_process:
            self._post_process_files(files)
            return False, False

        if len(files) == 1:
            dummy, filename, data = files[0]
            return filename, base64.encodebytes(data)

        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as doc_zip:
            for dummy, filename, data in files:
                doc_zip.writestr(filename, data, compress_type=zipfile.ZIP_DEFLATED)

        filename = default_filename
        return filename, stream.getvalue()

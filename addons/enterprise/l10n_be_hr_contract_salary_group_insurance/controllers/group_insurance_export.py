# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io

from odoo import http, fields
from odoo.http import request
from odoo.tools.misc import xlsxwriter


class L10nBeHrPayrollGrouInsuranceController(http.Controller):

    @http.route(["/export/group_insurance/<int:wizard_id>"], type='http', auth='user')
    def export_group_insurance(self, wizard_id):
        wizard = request.env['l10n.be.group.insurance.wizard'].browse(wizard_id)
        if not wizard.exists() or not request.env.user.has_group('hr_payroll.group_hr_payroll_user'):
            return request.render(
                'http_routing.http_error', {
                    'status_code': 'Oops',
                    'status_message': "Please contact an administrator..."})

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Worksheet')
        style_highlight = workbook.add_format({'bold': True, 'pattern': 1, 'bg_color': '#E0E0E0', 'align': 'center'})
        style_normal = workbook.add_format({'align': 'center'})
        row = 0

        headers = [
            "NISS",
            "Name",
            "Amount",
            "Birthdate",
        ]

        rows = []
        for line in wizard.line_ids:
            employee = line.employee_id
            employee_name = employee.name
            amount = round(line.amount, 2)
            birthdate = employee.birthday or fields.Date.today()

            rows.append((
                employee.niss.replace('.', '').replace('-', '') if employee.niss else '',
                employee_name,
                amount,
                '%s/%s/%s' % (birthdate.day, birthdate.month, birthdate.year),
            ))

        col = 0
        for header in headers:
            worksheet.write(row, col, header, style_highlight)
            worksheet.set_column(col, col, 15)
            col += 1

        row = 1
        for employee_row in rows:
            col = 0
            for employee_data in employee_row:
                worksheet.write(row, col, employee_data, style_normal)
                col += 1
            row += 1

        workbook.close()
        xlsx_data = output.getvalue()
        response = request.make_response(
            xlsx_data,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', 'attachment; filename=group_insurance.xlsx')],
        )
        return response

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import io

from odoo import http, fields
from odoo.http import request
from odoo.tools.misc import xlsxwriter


class L10nBeHrPayrollEcoVoucherController(http.Controller):

    @http.route(["/export/ecovouchers/<int:wizard_id>"], type='http', auth='user')
    def export_eco_vouchers(self, wizard_id):
        wizard = request.env['l10n.be.eco.vouchers.wizard'].browse(wizard_id)
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
            "Numéro de registre national (p.ex. 790227 183 12)",
            "Salarié nom (p.ex. dupont)",
            "Salarié prénom (p.ex. max)",
            "Votre numéro interne du salarié  (p.ex. 152d97)",
            "Nombre de chèques [a] (p.ex. 18)",
            "Valeur faciale du chèque [b] (p.ex. 5.5)",
            "Total [a] x [b] (p.ex. 99)",
            "Date de naissance du salarié (dd/mm/yyyy)",
            "Sexe du salarié (m/f)",
            "Langue du salarié (nl/fr/en)",
            "Centre de coûts (p.ex. cc1. maximum 10 caractères)",
            "Votre numéro d'entreprise  (p.ex. be 0834013324)",
            "Adresse de livraison rue (p.ex. av. des volontaires)",
            "Adresse de livraison numéro (p.ex. 19)",
            "Adresse de livraison boite (p.ex. a1)",
            "Adresse de livraison code postal (p.ex. 1160)",
            "Adresse de livraison ville (p.ex. auderghem)",
        ]

        rows = []
        for line in wizard.line_ids:
            employee = line.employee_id
            employee_name = re.sub(r"[\(].*?[\)]", "", employee.name)
            quantity = 1
            amount = round(line.amount, 2)
            birthdate = employee.birthday or fields.Date.today()
            lang = employee.sudo().address_home_id.lang
            if lang == 'fr_FR':
                lang = 'FR'
            elif lang == 'nl_NL':
                lang = 'NL'
            else:
                lang = 'EN'

            rows.append((
                employee.niss.replace('.', '').replace('-', '') if employee.niss else '',
                employee_name.split(' ')[0],
                ' '.join(employee_name.split(' ')[1:]),
                ' ',
                quantity,
                amount,
                quantity * amount,
                '%s/%s/%s' % (birthdate.day, birthdate.month, birthdate.year),
                'F' if employee.gender == 'female' else 'M',
                lang,
                ' ', ' ', ' ', ' ', ' ', ' ', ' '
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
                ('Content-Disposition', 'attachment; filename=orderfile.xlsx')],
        )
        return response

# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Belgium - Payroll - December Slip',
    'icon': '/l10n_be/static/description/icon.png',
    'category': 'Human Resources',
    'depends': ['l10n_be_hr_payroll'],
    'description': """
    """,
    'version': '1.0',
    'data': [
        'data/hr_payslip_input_type_data.xml',
        'data/hr_salary_rule_category_data.xml',
        'data/cp200/employee_salary_data.xml',
        'wizard/l10n_be_december_slip_wizard_views.xml',
        'views/hr_payslip_views.xml',
        'security/ir.model.access.csv',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}

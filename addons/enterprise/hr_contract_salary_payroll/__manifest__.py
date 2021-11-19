# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Salary Configurator - Payroll',
    'category': 'Human Resources',
    'summary': 'Adds a Gross to Net Salary Simulaton',
    'depends': [
        'hr_contract_salary',
        'hr_payroll',
    ],
    'description': """
    """,
    'data': [
        'data/hr_contract_salary_resume_data.xml',
        'views/menuitems.xml',
        'views/hr_contract_views.xml',
    ],
    'demo': [
    ],
    'license': 'OEEL-1',
    'auto_install': True,
    'assets': {
        'web.assets_frontend': [
            'hr_contract_salary_payroll/static/src/js/**/*',
        ],
    }
}

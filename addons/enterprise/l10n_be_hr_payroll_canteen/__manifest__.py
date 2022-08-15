# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Salary Configurator (Belgium) - Canteen Cost',
    'icon': '/l10n_be/static/description/icon.png',
    'category': 'Human Resources',
    'summary': 'Salary Package Configurator - Canteen Cost',
    'depends': [
        'l10n_be_hr_contract_salary',
    ],
    'description': """
    """,
    'data': [
        'views/hr_contract_views.xml',
        'wizard/generate_simulation_link_views.xml',
        'data/cp200/employee_salary_data.xml',
        'views/hr_contract_salary_templates.xml',
    ],
    'demo': [
    ],
    'assets': {
        'web.assets_frontend': [
            'l10n_be_hr_payroll_canteen/static/src/js/hr_contract_salary.js',
        ],
    },
    'license': 'OEEL-1',
    'auto_install': True,
}

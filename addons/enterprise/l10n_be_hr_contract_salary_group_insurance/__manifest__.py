# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Salary Configurator (Belgium) - Group Insurance',
    'icon': '/l10n_be/static/description/icon.png',
    'category': 'Human Resources',
    'summary': 'Salary Package Configurator - Group Insurance',
    'depends': [
        'l10n_be_hr_contract_salary',
    ],
    'description': """
    """,
    'data': [
        'views/hr_contract_views.xml',
        'views/hr_dmfa_templates.xml',
        'wizard/l10n_be_group_insurance_wizard_views.xml',
        'data/hr_contract_salary_advantage_data.xml',
        'data/hr_salary_rule_category_data.xml',
        'data/cp200/employee_salary_data.xml',
        'data/cp200/employee_termination_fees_data.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
    ],
    'assets': {
        'web.assets_frontend': [
            'l10n_be_hr_contract_salary_group_insurance/static/src/**/*',
        ],
    },
    'license': 'OEEL-1',
    'auto_install': True,
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Salary Configurator (Belgium)',
    'icon': '/l10n_be/static/description/icon.png',
    'category': 'Human Resources',
    'summary': 'Salary Package Configurator',
    'depends': [
        'hr_contract_salary_payroll',
        'l10n_be_hr_payroll_fleet',
    ],
    'description': """
    """,
    'data': [
        'data/hr_contract_salary_advantage_data.xml',
        'data/hr_contract_salary_resume_data.xml',
        'data/hr_contract_salary_personal_info_data.xml',
        'data/cp200/employee_termination_fees_data.xml',
        'report/hr_contract_history_report_views.xml',
        'wizard/generate_simulation_link_views.xml',
        'report/hr_contract_history_report_views.xml',
        'views/hr_contract_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'demo': [
        'data/l10n_be_hr_contract_salary_demo.xml',
    ],
    'license': 'OEEL-1',
    'auto_install': True,
    'assets': {
        'web.assets_frontend': [
            'l10n_be_hr_contract_salary/static/src/**/*',
        ],
    }
}

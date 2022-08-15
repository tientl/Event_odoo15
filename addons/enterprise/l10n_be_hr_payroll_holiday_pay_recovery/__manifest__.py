# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Belgian Payroll - Holiday Pay Recovery',
    'category': 'Human Resources',
    'summary': 'Adapt Holiday Pay Recovery',
    'depends': ['l10n_be_hr_payroll'],
    'description': """
    """,
    'data': [
        'views/hr_employee_views.xml',
        'data/cp200/employee_salary_data.xml',
    ],
    'demo': [],
    'auto_install': True,
    'license': 'OEEL-1',
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Project Payroll Accounting',
    'version': '1.0',
    'category': 'Services/payroll/account',
    'summary': 'Project payroll accounting',
    'description': 'Bridge created to add the number of contracts linked to an AA to a project form',
    'depends': ['project', 'hr_payroll_account'],
    'data': [
        'views/project_project_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}

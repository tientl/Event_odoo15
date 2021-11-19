# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Project Budget",
    'version': '1.0',
    'summary': "Project account budget",
    'description': "",
    'category': 'Services/Project',
    'depends': ['account_budget', 'project'],
    'data': [
        'views/project_views.xml',
    ],
    'application': False,
    'auto_install': True,
    'license': 'OEEL-1',
}

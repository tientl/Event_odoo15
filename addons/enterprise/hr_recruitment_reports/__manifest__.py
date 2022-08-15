# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Recruitment Reporting',
    'version': '1.0',
    'category': 'Human Resources/Recruitment',
    'description': """
Add a dynamic report about recruitment.
    """,
    'website': 'https://www.odoo.com/app/recruitment',
    'depends': ['hr_recruitment', 'web_dashboard'],
    'data': [
        'security/ir.model.access.csv',
        'security/hr_recruitment_reports_security.xml',
        'report/hr_recruitment_report_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}

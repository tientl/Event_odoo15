# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Project Sales Subscription',
    'version': '1.0',
    'category': 'Services/sales/subscriptions',
    'summary': 'Project sales subscriptions',
    'description': 'Bridge created to add the number of subscriptions linked to an AA to a project form',
    'depends': ['project', 'sale_subscription'],
    'data': [
        'views/project_project_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}

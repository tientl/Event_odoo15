# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Purchase Stock Enterprise",
    'version': "1.0",
    'category': "Inventory/Purchase",
    'summary': "Customized Dashboard for Purchase Stock",
    'description': "",
    'depends': ['purchase_enterprise', 'purchase_stock'],
    'data': [
        'report/purchase_report_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
    'license': 'OEEL-1',
}

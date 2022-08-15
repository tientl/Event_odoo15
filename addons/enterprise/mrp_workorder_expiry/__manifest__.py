# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'MRP II - Expiry',
    'version': '1.0',
    'category': 'Manufacturing/Manufacturing',
    'summary': 'MRP Workorder Expiry',
    'description': """
Technical module.
    """,
    'depends': ['mrp_workorder', 'product_expiry'],
    'data': [
        'views/mrp_workorder_views.xml',
        'wizard/confirm_expiry_view.xml',
    ],
    'installable': True,
    'auto_install': True,
    'application': False,
    'assets': {
        'web.assets_backend': [
            'mrp_workorder_expiry/static/**/*',
        ],
    },
    'license': 'OEEL-1',
}

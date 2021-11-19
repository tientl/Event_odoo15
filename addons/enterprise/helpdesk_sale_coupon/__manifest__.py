# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Helpdesk Sale Coupon',
    'category': 'Services/Helpdesk',
    'summary': 'Project, Tasks, Sale Coupon',
    'depends': ['helpdesk_sale', 'sale_coupon'],
    'auto_install': False,
    'description': """
Generate Coupons from Helpdesks tickets
    """,
    'data': [
        'security/ir.model.access.csv',
        'wizard/helpdesk_sale_coupon_generate_views.xml',
        'views/helpdesk_views.xml',
    ],
    'demo': ['data/helpdesk_sale_coupon_demo.xml'],
    'license': 'OEEL-1',
}

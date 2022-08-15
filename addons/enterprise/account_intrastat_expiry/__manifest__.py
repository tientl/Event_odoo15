# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Account Invoice Expiry',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'summary': 'This module adds an expiry feature to transaction account intrastat codes.',
    'depends': ['account_intrastat'],
    'data': [
        'data/account.intrastat.code.csv',
        'views/account_intrastat_code_view.xml',
        'views/account_invoice_view.xml',
        'views/product_views.xml',
        'views/report_financial.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}

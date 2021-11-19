# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Check Printing Accounting',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'summary': 'Check printing enterprise addons',
    'description': """
This module adds the possibility to filter by check number in the reconciliation
widget.
    """,
    'depends': ['account_accountant', 'account_check_printing'],
    'data': [
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}

# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Portugal - Accounting Reports',
    'icon': '/l10n_pt/static/description/icon.png',
    'version': '1.0',
    'description': """
Accounting reports for Portugal
================================

    """,
    'category': 'Accounting/Localizations/Reporting',
    'depends': ['l10n_pt', 'account_reports'],
    'data': [
        'data/balance_sheet.xml',
        'data/profit_loss.xml',
    ],
    'demo': [],
    'auto_install': True,
    'installable': True,
    'license': 'OEEL-1',
}

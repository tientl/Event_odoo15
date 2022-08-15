# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Hungary - Accounting Reports',
    'icon': '/l10n_hu/static/description/icon.png',
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'author': 'Odoo S.A.',
    'description': """ Base module for Hungary reports """,
    'depends': [
        'l10n_hu',
        'account_reports',
    ],
    'data': [
        'data/balance_sheet.xml',
        'data/profit_loss.xml',
    ],
    'auto_install': True,
    'installable': True,
    'license': 'OEEL-1',
}

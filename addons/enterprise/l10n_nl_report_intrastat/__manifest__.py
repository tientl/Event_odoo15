# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Netherlands Intrastat Declaration Reports',
    'icon': '/l10n_nl/static/description/icon.png',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Generates Netherlands Intrastat report for declaration based on invoices.
    """,
    'depends': ['l10n_nl_reports', 'account_intrastat'],
    'auto_install': True,
    'license': 'OEEL-1',
}

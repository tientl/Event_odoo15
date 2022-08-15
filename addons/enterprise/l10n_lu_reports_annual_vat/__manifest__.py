# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Luxembourg - Annual VAT Report',
    'icon': '/l10n_lu/static/description/icon.png',
    'version': '1.0',
    'description': """
Annual VAT report for Luxembourg
============================================
    """,
    'category': 'Accounting/Localizations/Reporting',
    'depends': ['l10n_lu_reports'],
    'data': [
        'views/l10n_lu_yearly_tax_report_manual_views.xml',
        'security/ir.model.access.csv',
        'security/l10n_lu_yearly_tax_report_manual_security.xml',
    ],
    'license': 'OEEL-1',
    'auto_install': True,
    'post_init_hook': '_post_init_hook',
    'assets': {
        'web.assets_backend': [
            'l10n_lu_reports_annual_vat/static/src/scss/tax_fields_views.scss',
        ],
    },
}

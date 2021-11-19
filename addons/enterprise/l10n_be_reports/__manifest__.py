# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Belgium - Accounting Reports',
    'icon': '/l10n_be/static/description/icon.png',
    'version': '1.1',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
        Accounting reports for Belgium
    """,
    'depends': [
        'l10n_be', 'account_reports'
    ],
    'data': [
        'wizard/l10n_be_281_50_wizard.xml',
        'views/l10n_be_vat_statement_views.xml',
        'views/l10n_be_wizard_xml_export_options_views.xml',
        'views/l10n_be_vendor_partner_views.xml',
        'views/report_views.xml',
        'views/res_partner_views.xml',
        'data/account_financial_html_report_data.xml',
        'data/account_tag_data.xml',
        'security/ir.model.access.csv',
        'report/l10n_be_281_50_pdf_templates.xml',
        'report/l10n_be_281_50_xml_templates.xml',
    ],
    'installable': True,
    'auto_install': True,
    'website': 'https://www.odoo.com/app/accounting',
    'license': 'OEEL-1',
}

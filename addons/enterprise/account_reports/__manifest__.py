# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Accounting Reports',
    'summary': 'View and create reports',
    'category': 'Accounting/Accounting',
    'description': """
Accounting Reports
==================
    """,
    'depends': ['account_accountant'],
    'data': [
        'security/ir.model.access.csv',
        'data/account_financial_report_data.xml',
        'data/mail_data.xml',
        'views/account_report_view.xml',
        'views/report_financial.xml',
        'views/res_company_views.xml',
        'views/search_template_view.xml',
        'views/partner_view.xml',
        'views/account_journal_dashboard_view.xml',
        'views/res_config_settings_views.xml',
        'wizard/multicurrency_revaluation.xml',
        'wizard/report_export_wizard.xml',
        'wizard/fiscal_year.xml',
        'views/account_activity.xml',
        'views/account_sales_report_view.xml',
        'views/account_account_views.xml',
        'views/res_company_views.xml',
        'views/account_tax_views.xml',
        'views/account_report_journal.xml',
    ],
    'auto_install': True,
    'installable': True,
    'license': 'OEEL-1',
    'post_init_hook': 'set_periodicity_journal_on_companies',
    'assets': {
        'account_reports.assets_financial_report': [
            ('include', 'web._assets_helpers'),
            'web/static/lib/bootstrap/scss/_variables.scss',
            ('include', 'web._assets_bootstrap'),
            'web/static/fonts/fonts.scss',
            'account_reports/static/src/scss/account_financial_report.scss',
            'account_reports/static/src/scss/account_report_print.scss',
        ],
        'web.assets_backend': [
            'account_reports/static/src/js/mail_activity.js',
            'account_reports/static/src/js/account_reports.js',
            'account_reports/static/src/js/action_manager_account_report_dl.js',
            'account_reports/static/src/scss/account_financial_report.scss',
        ],
        'web.qunit_suite_tests': [
            'account_reports/static/tests/action_manager_account_report_dl_tests.js',
            'account_reports/static/tests/account_reports_tests.js',
        ],
        'web.assets_tests': [
            'account_reports/static/tests/tours/**/*',
        ],
        'web.assets_qweb': [
            'account_reports/static/src/xml/**/*',
        ],
    }
}

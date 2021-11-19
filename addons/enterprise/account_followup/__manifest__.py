# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Payment Follow-up Management',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'description': """
Module to automate letters for unpaid invoices, with multi-level recalls.
=========================================================================

You can define your multiple levels of recall through the menu:
---------------------------------------------------------------
    Configuration / Follow-up / Follow-up Levels

Once it is defined, you can automatically print recalls every day through simply clicking on the menu:
------------------------------------------------------------------------------------------------------
    Payment Follow-Up / Send Email and letters

It will generate a PDF / send emails / set manual actions according to the different levels
of recall defined. You can define different policies for different companies.

""",
    'website': 'https://www.odoo.com/app/invoicing',
    'depends': ['account', 'mail', 'sms', 'account_reports'],
    'data': [
        'security/account_followup_security.xml',
        'security/ir.model.access.csv',
        'security/sms_security.xml',
        'data/account_followup_data.xml',
        'data/cron.xml',
        'views/account_followup_views.xml',
        'views/partner_view.xml',
        'views/report_followup.xml',
        'views/account_journal_dashboard_view.xml',
        ],
    'demo': [
        'demo/account_followup_demo.xml'
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'account_followup.assets_followup_report': [
            ('include', 'web._assets_helpers'),
            'web/static/lib/bootstrap/scss/_variables.scss',
            ('include', 'web._assets_bootstrap'),
            'web/static/fonts/fonts.scss',
            'account_followup/static/src/scss/account_followup_letter.scss',
        ],
        'web.assets_backend': [
            'account_followup/static/src/js/followup_form_view.js',
            'account_followup/static/src/js/followup_form_model.js',
            'account_followup/static/src/js/followup_form_renderer.js',
            'account_followup/static/src/js/followup_form_controller.js',
            'account_followup/static/src/scss/account_followup_report.scss',
        ],
        'web.assets_tests': [
            'account_followup/static/tests/tours/**/*',
        ],
        'web.assets_qweb': [
            'account_followup/static/src/xml/**/*',
        ],
    }
}

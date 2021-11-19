# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Account Batch Payment Reconciliation',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Allows using Reconciliation with the Batch Payment feature.',
    'depends': ['account_accountant', 'account_batch_payment'],
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'account_accountant_batch_payment/static/src/css/account_reconciliation.css',
            'account_accountant_batch_payment/static/src/js/account_batch_payment_reconciliation.js',
        ],
        'web.qunit_suite_tests': [
            ('after', 'web/static/tests/legacy/views/kanban_tests.js', 'account_accountant_batch_payment/static/src/css/account_reconciliation.css'),
            ('after', 'web/static/tests/legacy/views/kanban_tests.js', 'account_accountant_batch_payment/static/test/reconciliation_tests.js'),
        ],
        'web.assets_qweb': [
            'account_accountant_batch_payment/static/src/xml/**/*',
        ],
    }
}

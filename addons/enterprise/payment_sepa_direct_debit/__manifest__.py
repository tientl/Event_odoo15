# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Sepa Direct Debit Payment Acquirer",
    'version': '2.0',
    'category': 'Accounting/Accounting',
    'summary': "Payment Acquirer: Sepa Direct Debit",
    'description': """Sepa Direct Debit Payment Acquirer""",
    'depends': ['account_sepa_direct_debit', 'payment', 'sms'],
    'data': [
        'views/payment_views.xml',
        'views/payment_sepa_direct_debit_templates.xml',
        'data/mail_template_data.xml',
        'data/payment_acquirer_data.xml',
    ],
    'installable': True,
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_frontend': [
            'payment_sepa_direct_debit/static/src/scss/payment_form.scss',
            'payment_sepa_direct_debit/static/src/js/payment_form.js',
            'payment_sepa_direct_debit/static/src/js/signature_form.js',
        ],
    },
    'license': 'OEEL-1',
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Account Invoice Extract',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'summary': 'Extract data from invoice scans to fill them automatically',
    'depends': ['account', 'iap', 'mail_enterprise'],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'data/config_parameter_endpoint.xml',
        'data/extraction_status.xml',
        'data/res_config_settings_views.xml',
        'data/update_status_cron.xml',
        'views/account_move_views.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'account_invoice_extract/static/src/js/invoice_extract_box.js',
            'account_invoice_extract/static/src/js/invoice_extract_box_layer.js',
            'account_invoice_extract/static/src/js/invoice_extract_field.js',
            'account_invoice_extract/static/src/js/invoice_extract_field_button.js',
            'account_invoice_extract/static/src/js/invoice_extract_fields.js',
            'account_invoice_extract/static/src/js/invoice_extract_form_renderer.js',
            'account_invoice_extract/static/src/js/invoice_extract_form_view.js',
            'account_invoice_extract/static/src/scss/account_invoice_extract.scss',
            'account_invoice_extract/static/src/css/account_invoice_extract_box_layer.css',
        ],
        'web.qunit_suite_tests': [
            'account_invoice_extract/static/src/tests/helpers/invoice_extract_test_utils.js',
            'account_invoice_extract/static/src/tests/invoice_extract_box_tests.js',
            'account_invoice_extract/static/src/tests/invoice_extract_box_layer_tests.js',
            'account_invoice_extract/static/src/tests/invoice_extract_fields_and_box_layer_tests.js',
            'account_invoice_extract/static/src/tests/invoice_extract_field_tests.js',
            'account_invoice_extract/static/src/tests/invoice_extract_fields_tests.js',
            'account_invoice_extract/static/src/tests/invoice_extract_field_button_tests.js',
            'account_invoice_extract/static/src/tests/invoice_extract_form_view_tests.js',
        ],
        'web.assets_qweb': [
            'account_invoice_extract/static/src/xml/invoice_extract_box.xml',
            'account_invoice_extract/static/src/xml/invoice_extract_button.xml',
        ],
    }
}

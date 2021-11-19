# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Sign',
    'version': '1.0',
    'category': 'Sales/Sign',
    'sequence': 105,
    'summary': "Send documents to sign online and handle filled copies",
    'description': """
Sign and complete your documents easily. Customize your documents with text and signature fields and send them to your recipients.\n
Let your customers follow the signature process easily.
    """,
    'website': 'https://www.odoo.com/app/sign',
    'depends': ['mail', 'attachment_indexation', 'portal', 'sms'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sign_data.xml',
        'views/sign_template_views_mobile.xml',
        'wizard/sign_duplicate_template_with_pdf_views.xml',
        'wizard/sign_send_request_views.xml',
        'wizard/sign_template_share_views.xml',
        'wizard/sign_request_send_copy_views.xml',
        'views/sign_request_templates.xml',
        'views/sign_template_templates.xml',
        'views/sign_request_views.xml',
        'views/sign_template_views.xml',
        'views/sign_log_views.xml',
        'views/sign_portal_templates.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/res_partner_views.xml',
        'views/sign_pdf_iframe_templates.xml',
        'views/terms_views.xml',
        'report/sign_log_reports.xml',
    ],
    'demo': [
        'data/sign_demo.xml',
    ],
    'application': True,
    'installable': True,
    'license': 'OEEL-1',
    'assets': {
        'sign.assets_pdf_iframe': [
            'web/static/lib/fontawesome/css/font-awesome.css',
            'web/static/lib/jquery.ui/jquery-ui.css',
            'web/static/lib/select2/select2.css',
            'web/static/lib/bootstrap/scss/_functions.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            'web/static/lib/bootstrap/scss/mixins/_breakpoints.scss',
            'web/static/lib/bootstrap/scss/mixins/_grid-framework.scss',
            'web/static/lib/bootstrap/scss/mixins/_grid.scss',
            'web/static/lib/bootstrap/scss/utilities/_display.scss',
            'web/static/lib/bootstrap/scss/_grid.scss',
            'web/static/lib/bootstrap/scss/utilities/_flex.scss',
            'web/static/src/legacy/scss/bs_mixins_overrides.scss',
            'web/static/lib/bootstrap/scss/mixins/_deprecate.scss',
            'web/static/lib/bootstrap/scss/mixins/_size.scss',
            'web/static/src/legacy/scss/utils.scss',
            'web/static/src/legacy/scss/primary_variables.scss',
            'web_enterprise/static/src/legacy/scss/primary_variables.scss',
            'web_tour/static/src/scss/tip.scss',
            'sign/static/src/css/iframe.css',
            'web/static/src/legacy/scss/secondary_variables.scss',
            'sign/static/src/scss/iframe.scss',
        ],
        'web.assets_common': [
            'sign/static/src/js/sign_common.js',
            'sign/static/src/scss/sign_common.scss',
            'sign/static/src/js/multi_file_upload.js',
        ],
        'web.assets_backend': [
            'sign/static/src/js/sign_backend.js',
            'sign/static/src/js/tours/sign.js',
            'sign/static/src/js/activity.js',
            'sign/static/src/components/sign_request/sign_request.js',
            'sign/static/src/scss/sign_backend.scss',
        ],
        'web.assets_frontend': [
            'sign/static/src/scss/sign_frontend.scss',
        ],
        'web.assets_tests': [
            'sign/static/tests/tours/**/*',
        ],
        'web.qunit_suite_tests': [
            'sign/static/tests/document_backend_tests.js',
        ],
        'web.assets_qweb': [
            'sign/static/src/xml/*.xml',
            'sign/static/src/components/activity/activity.xml',
            'sign/static/src/components/sign_request/sign_request.xml',
        ],
    }
}

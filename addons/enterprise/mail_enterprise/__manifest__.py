# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Mail Enterprise',
    'category': 'Productivity/Discuss',
    'depends': ['mail', 'web_mobile'],
    'description': """
Bridge module for mail and enterprise
=====================================

Display a preview of the last chatter attachment in the form view for large
screen devices.
""",
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'mail.assets_discuss_public': [
            'web_enterprise/static/src/webclient/webclient.scss',
            'mail_enterprise/static/src/components/*/*',
            'mail_enterprise/static/src/models/*/*.js',
            'web_mobile/static/src/js/core/mixins.js',
            'web_mobile/static/src/js/core/session.js',
            'web_mobile/static/src/js/services/core.js',
        ],
        'web.assets_backend': [
            'mail_enterprise/static/src/components/*/*.js',
            'mail_enterprise/static/src/models/*/*.js',
            'mail_enterprise/static/src/js/attachment_viewer.js',
            'mail_enterprise/static/src/scss/mail_enterprise.scss',
            'mail_enterprise/static/src/components/*/*.scss',
            'mail_enterprise/static/src/scss/mail_enterprise_mobile.scss',
            'mail_enterprise/static/src/widgets/*/*.js',
            'mail_enterprise/static/src/widgets/*/*.scss',
        ],
        'web.assets_tests': [
            'mail_enterprise/static/tests/tours/**/*',
        ],
        'web.qunit_suite_tests': [
            'mail_enterprise/static/src/components/*/tests/*.js',
            'mail_enterprise/static/src/widgets/*/tests/*.js',
            'mail_enterprise/static/tests/attachment_preview_tests.js',
        ],
        'web.assets_qweb': [
            'mail_enterprise/static/src/components/*/*.xml',
            'mail_enterprise/static/src/xml/mail_enterprise.xml',
        ],
    }
}

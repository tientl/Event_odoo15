# -*- coding: utf-8 -*-
{
    'name': "web_dashboard",
    'category': 'Hidden',
    'version': '1.0',
    'description':
        """
Odoo Dashboard View.
========================

This module defines the Dashboard view, a new type of reporting view. This view
can embed graph and/or pivot views, and displays aggregate values.
        """,
    'depends': ['web'],
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'web_dashboard/static/src/**/*',
            ("remove", "web_dashboard/static/src/legacy/**/*"),
        ],
        "web.assets_backend_legacy_lazy": [
            "web_dashboard/static/src/legacy/**/*",
        ],
        'web.qunit_suite_tests': [
            'web_dashboard/static/tests/**/*.js',
        ],
        'web.assets_qweb': [
            'web_dashboard/static/src/**/*.xml',
        ],
    }
}

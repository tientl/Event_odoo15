# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Web Gantt',
    'category': 'Hidden',
    'description': """
Odoo Web Gantt chart view.
=============================

    """,
    'version': '2.0',
    'depends': ['web'],
    'assets': {
        'web.assets_qweb': [
            'web_gantt/static/src/xml/**/*',
        ],
        'web.assets_backend': [
            'web_gantt/static/src/**/*',
        ],
        'web.qunit_suite_tests': [
            'web_gantt/static/tests/**/*',
        ],
    },
    'auto_install': True,
    'license': 'OEEL-1',
}

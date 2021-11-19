# -*- coding: utf-8 -*-
{
    'name': "Grid View",

    'summary': "Basic 2D Grid view for odoo",
    'description': """
    """,
    'category': 'Hidden',
    'version': '0.1',
    'depends': ['web'],
    'assets': {
        'web.assets_qweb': [
            'web_grid/static/src/xml/**/*',
        ],
        'web.assets_backend': [
            'web_grid/static/src/**/*',
        ],
        'web.qunit_suite_tests': [
            'web_grid/static/tests/grid_tests.js',
            'web_grid/static/tests/mock_server.js',
        ],
        'web.qunit_mobile_suite_tests': [
            'web_grid/static/tests/grid_mobile_tests.js',
            'web_grid/static/tests/mock_server.js',
        ],
    },
    'auto_install': True,
    'license': 'OEEL-1',
}

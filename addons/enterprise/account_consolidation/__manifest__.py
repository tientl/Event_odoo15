# -*- coding: utf-8 -*-
{
    'name': "Consolidation",
    'category': 'Accounting/Accounting',
    'sequence': 205,
    'summary': """All you need to make financial consolidation""",
    'description': """All you need to make financial consolidation""",
    'author': "Odoo S.A.",
    'depends': ['account_reports','web_grid'],
    'data': [
        'security/account_consolidation_security.xml',
        'security/ir.model.access.csv',
        'report/trial_balance.xml',
        'views/account_account_views.xml',
        'views/account_move_views.xml',
        'views/consolidation_account_views.xml',
        'views/consolidation_journal_views.xml',
        'views/consolidation_period_views.xml',
        'views/consolidation_account_group_views.xml',
        'views/consolidation_chart_views.xml',
        'views/consolidation_rate_views.xml',
        'views/menuitems.xml',
        'views/onboarding_templates.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'account_consolidation/static/src/scss/consolidation_grid_view.scss',
            'account_consolidation/static/src/scss/consolidation_kanban.scss',
            'account_consolidation/static/src/js/trial_balance_grid/controller.js',
            'account_consolidation/static/src/js/trial_balance_grid/renderer.js',
            'account_consolidation/static/src/js/trial_balance_grid/view.js',
            'account_consolidation/static/src/js/move_line_list/renderer.js',
            'account_consolidation/static/src/js/move_line_list/view.js',
            'account_consolidation/static/src/js/json_field.js',
        ],
        'web.assets_qweb': [
            'account_consolidation/static/src/xml/**/*',
        ],
        'web.qunit_suite_tests': [
            'account_consolidation/static/tests/**/*'
        ]
    },
    'license': 'OEEL-1',
}

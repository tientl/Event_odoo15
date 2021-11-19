# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Planning",
    'summary': """Manage your employees' schedule""",
    'description': """
    Schedule your teams and employees with shift.
    """,
    'category': 'Human Resources/Planning',
    'sequence': 130,
    'version': '1.0',
    'depends': ['hr', 'web_gantt', 'digest', 'hr_gantt'],
    'data': [
        'security/planning_security.xml',
        'security/ir.model.access.csv',
        'data/digest_data.xml',
        'wizard/planning_send_views.xml',
        'wizard/slot_planning_select_send_views.xml',
        'views/hr_views.xml',
        'views/planning_template_views.xml',
        'views/resource_views.xml',
        'views/planning_views.xml',
        'views/planning_report_views.xml',
        'views/res_config_settings_views.xml',
        'views/planning_templates.xml',
        'data/planning_cron.xml',
        'data/mail_template_data.xml',
    ],
    'demo': [
        'data/planning_demo.xml',
    ],
    'application': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'planning/static/src/js/planning_mixins.js',
            'planning/static/src/js/planning_gantt_controller.js',
            'planning/static/src/js/planning_gantt_row.js',
            'planning/static/src/js/planning_gantt_renderer.js',
            'planning/static/src/js/planning_gantt_model.js',
            'planning/static/src/js/planning_gantt_view.js',
            'planning/static/src/js/planning_calendar.js',
            'planning/static/src/js/planning_send/*',
            'planning/static/src/js/widgets/*',
            'planning/static/src/scss/planning_gantt.scss',
            'planning/static/src/js/tours/planning.js',
        ],
        'web.assets_frontend': [
            'planning/static/src/scss/planning_calendar_report.scss',
            'web/static/src/legacy/scss/form_view.scss',
            'planning/static/src/js/planning_calendar_front.js',
        ],
        'web.qunit_suite_tests': [
            'planning/static/tests/**/*',
        ],
        'web.assets_qweb': [
            'planning/static/src/xml/**/*',
        ],
        'web.assets_tests': [
            'planning/static/tests/tours/*',
        ],
    }
}

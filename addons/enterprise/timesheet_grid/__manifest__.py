# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# YTI FIXME: This module should be named timesheet_enterprise
{
    'name': "Timesheets",
    'summary': "Track employee time on tasks",
    'description': """
* Timesheet submission and validation
* Activate grid view for timesheets
    """,
    'version': '1.0',
    'depends': ['project_enterprise', 'web_grid', 'hr_timesheet', 'timer'],
    'category': 'Services/Timesheets',
    'sequence': 65,
    'data': [
        'data/ir_cron_data.xml',
        'data/mail_template_data.xml',
        'data/timesheet_grid_data.xml',
        'security/timesheet_security.xml',
        'security/ir.model.access.csv',
        'views/hr_timesheet_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/timesheet_merge_wizard_views.xml',
    ],
    'demo': [
        'data/timesheet_grid_demo.xml',
    ],
    'website': ' https://www.odoo.com/app/timesheet',
    'auto_install': ['web_grid', 'hr_timesheet'],
    'application': True,
    'license': 'OEEL-1',
    'pre_init_hook': 'pre_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_backend': [
            'timesheet_grid/static/src/scss/timesheet_grid.scss',
            'timesheet_grid/static/src/scss/task_progress_gantt.scss',
            'timesheet_grid/static/src/js/timesheet_uom.js',
            'timesheet_grid/static/src/js/timesheet_uom_timer.js',
            'timesheet_grid/static/src/js/timesheet_config_mixin.js',
            'timesheet_grid/static/src/js/timesheet_gantt/task_progress_gantt_view.js',
            'timesheet_grid/static/src/js/timesheet_grid/timesheet_grid_model.js',
            'timesheet_grid/static/src/js/timesheet_grid/timesheet_grid_controller.js',
            'timesheet_grid/static/src/js/timesheet_grid/timesheet_grid_group_by_no_date_mixin.js',
            'timesheet_grid/static/src/js/timesheet_grid/timesheet_grid_renderer.js',
            'timesheet_grid/static/src/js/timesheet_grid/timesheet_grid_view.js',
            'timesheet_grid/static/src/js/timesheet_grid/timesheet_timer_grid_model.js',
            'timesheet_grid/static/src/js/timesheet_grid/timesheet_timer_grid_controller.js',
            'timesheet_grid/static/src/js/timesheet_grid/timesheet_timer_grid_renderer.js',
            'timesheet_grid/static/src/js/timesheet_grid/timesheet_timer_grid_view.js',
            'timesheet_grid/static/src/js/timesheet_grid/timer_m2o.js',
            'timesheet_grid/static/src/js/timesheet_grid/timer_header_component.js',
            'timesheet_grid/static/src/js/timesheet_grid/timer_start_component.js',
            'timesheet_grid/static/src/js/timesheet_kanban/timesheet_kanban_view.js',
            'timesheet_grid/static/src/js/timesheet_list/timesheet_list_view.js',
            'timesheet_grid/static/src/js/timesheet_pivot/timesheet_pivot_view.js',
            'timesheet_grid/static/src/js/tours/timesheet_grid.js',
            'timesheet_grid/static/src/js/widgets/timesheets_m2o_avatar_employee.js',
        ],
        "web.assets_backend_legacy_lazy": [
            'timesheet_grid/static/src/js/timesheet_pivot/timesheet_pivot_legacy.js',
        ],
        'web.assets_tests': [
            'timesheet_grid/static/tests/tours/timesheet_record_time.js',
        ],
        'web.qunit_suite_tests': [
            ('after', 'web_grid/static/tests/mock_server.js', 'timesheet_grid/static/tests/timesheet_uom_tests.js'),
            ('after', 'web_grid/static/tests/mock_server.js', 'timesheet_grid/static/tests/timesheet_grid_tests.js'),
            ('after', 'web_grid/static/tests/mock_server.js', 'timesheet_grid/static/tests/timesheet_timer_grid_tests.js'),
            ('after', 'web_grid/static/tests/mock_server.js', 'timesheet_grid/static/tests/task_progress_gantt_test.js'),
        ],
        'web.assets_qweb': [
            'timesheet_grid/static/src/xml/**/*',
        ],
    }
}

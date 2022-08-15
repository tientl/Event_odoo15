# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Project Enterprise",
    'summary': """Bridge module for project and enterprise""",
    'description': """
Bridge module for project and enterprise
    """,
    'category': 'Services/Project',
    'version': '1.0',
    'depends': ['project', 'web_map', 'web_gantt', 'web_enterprise'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/project_task_views.xml',
        'views/project_sharing_templates.xml',
    ],
    'demo': ['data/project_demo.xml'],
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'project_enterprise/static/src/js/**/*',
            'project_enterprise/static/src/scss/**/*',
            'project_enterprise/static/src/project_control_panel/**/*',
        ],
        'web.assets_qweb': [
            'project_enterprise/static/src/**/*.xml',
        ],
        'web.qunit_suite_tests': [
            'project_enterprise/static/tests/**/*',
        ],
        'project.webclient': [
            ('remove', 'web_enterprise/static/src/legacy/legacy_service_provider.js'),
            ('remove', 'web_enterprise/static/src/webclient/home_menu/*'),
            ('remove', 'project/static/src/project_sharing/main.js'),
            'project_enterprise/static/src/project_sharing/**/*',
        ],
    }
}

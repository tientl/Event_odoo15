# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Field Service",
    'summary': "Schedule and track onsite operations, time and material",
    'description': """
Field Services Management
=========================
This module adds the features needed for a modern Field service management.
It installs the following apps:
- Project
- Timesheet

Adds the following options:
- reports on tasks
- FSM app with custom view for onsite worker
- add products on tasks

    """,
    'category': 'Services/Field Service',
    'sequence': 170,
    'version': '1.0',
    'depends': ['project_enterprise', 'timesheet_grid', 'base_geolocalize'],
    'data': [
        'data/fsm_data.xml',
        'data/mail_template_data.xml',
        'security/fsm_security.xml',
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'report/project_report_views.xml',
        'views/hr_timesheet_views.xml',
        'views/fsm_views.xml',
        'views/project_task_views.xml',
        'views/project_sharing_views.xml',
    ],
    'application': True,
    'demo': ['data/fsm_demo.xml'],
    'post_init_hook': 'create_field_service_project',
    'assets': {
        'web.assets_backend': [
            'industry_fsm/static/src/**/*',
        ],
    },
    'license': 'OEEL-1',
}

# -*- coding: utf-8 -*-
{
    'name': 'Events Schedule',
    'version': '1.6',
    'category': 'Events',
    'description': """
Schedule of event.
""",
    'depends': ['website_event_meet'],
    'data': [
        'security/ir.model.access.csv',
        'views/event_schedule_views.xml',
        'views/event_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
        ],
        'web.assets_common': [
        ],
        'web.assets_qweb': [
        ],
        'web.report_assets_common': [
        ],
        'web.report_assets_pdf': [
        ],
    },
    'license': 'LGPL-3',
}

# -*- coding: utf-8 -*-
{
    'name': 'Events Schedule',
    'version': '1.6',
    'category': 'Events',
    'description': """
Schedule of event.
""",
    'depends': ['website_event_track'],
    'data': [
        'security/ir.model.access.csv',
        'views/event_schedule_views.xml',
        'views/event_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}

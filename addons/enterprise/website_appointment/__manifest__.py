# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Website Appointments',
    'version': '1.0',
    'category': 'Marketing/Online Appointment',
    'sequence': 215,
    'website': 'https://www.odoo.com/page/appointments',
    'description': """
Allow clients to Schedule Appointments through your Website
-------------------------------------------------------------

""",
    'depends': ['appointment', 'website_enterprise'],
    'data': [
        'data/calendar_data.xml',
        'data/website_data.xml',
        'views/calendar_appointment_type_views.xml',
        'views/calendar_menus.xml',
        'views/calendar_templates_appointments.xml',
        'views/calendar_templates_registration.xml',
        'views/calendar_templates_validation.xml',
        'views/website_templates.xml',
        'security/calendar_security.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
    'post_init_hook': '_post_init_website_appointment',
    'license': 'OEEL-1',
    'assets': {
        'website.assets_editor': [
            'website_appointment/static/src/js/website_appointment.editor.js',
        ],
        'web.assets_tests': [
            'website_appointment/static/tests/tours/*',
        ],
    }
}

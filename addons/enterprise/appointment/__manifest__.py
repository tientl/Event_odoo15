# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Appointments',
    'version': '1.0',
    'category': 'Marketing/Online Appointment',
    'sequence': 215,
    'summary': 'Allow people to book meetings in your agenda',
    'website': 'https://www.odoo.com/app/appointments',
    'description': """
        Allow clients to Schedule Appointments through the Portal
    """,
    'depends': ['calendar_sms', 'hr', 'portal'],
    'data': [
        'data/calendar_data.xml',
        'data/mail_data.xml',
        'data/mail_template_data.xml',
        'views/calendar_event_views.xml',
        'views/calendar_appointment_question_views.xml',
        'views/calendar_appointment_type_views.xml',
        'views/calendar_appointment_slot_views.xml',
        'views/calendar_menus.xml',
        'views/calendar_templates_appointments.xml',
        'views/calendar_templates_registration.xml',
        'views/calendar_templates_validation.xml',
        'views/portal_templates.xml',
        'wizard/calendar_appointment_share_views.xml',
        'security/calendar_security.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'data/calendar_appointment_demo.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'OEEL-1',
    'assets': {
        'web_editor.assets_wysiwyg': [
            'appointment/static/src/js/wysiwyg.js',
        ],
        'web.assets_frontend': [
            'appointment/static/src/scss/appointment.scss',
            'appointment/static/src/js/appointment_select_appointment_type.js',
            'appointment/static/src/js/appointment_select_appointment_slot.js',
            'appointment/static/src/js/appointment_form.js',
        ],
        'web.assets_backend': [
            'appointment/static/src/scss/calendar_appointment_type_views.scss',
            'appointment/static/src/scss/web_calendar.scss',
            'appointment/static/src/js/calendar_controller.js',
            'appointment/static/src/js/calendar_model.js',
            'appointment/static/src/js/calendar_renderer.js',
        ],
        'web.assets_qweb': [
            'appointment/static/src/xml/**/*',
        ],
        'web.qunit_suite_tests': [
            'appointment/static/tests/*',
        ],
    }
}

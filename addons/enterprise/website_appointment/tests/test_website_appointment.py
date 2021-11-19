# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests import common, tagged, users


@tagged('-at_install', 'post_install')
class WebsiteAppointmentTest(common.TransactionCase):
    @users('admin')
    def test_is_published_custom_appointment_type(self):
        custom_appointment = self.env['calendar.appointment.type'].create({
            'name': 'Custom Appointment',
            'category': 'custom',
        })
        self.assertTrue(custom_appointment.is_published, "A custom appointment type should be auto published at creation")
        appointment_copied = custom_appointment.copy()
        self.assertFalse(appointment_copied.is_published, "When we copy an appointment type, the new one should not be published")

        custom_appointment.write({'is_published': False})
        appointment_copied = custom_appointment.copy()
        self.assertFalse(appointment_copied.is_published)

    @users('admin')
    def test_is_published_website_appointment_type(self):
        website_appointment = self.env['calendar.appointment.type'].create({
            'name': 'Website Appointment',
            'category': 'website',
        })
        self.assertFalse(website_appointment.is_published, "A website appointment type should not be published at creation")
        appointment_copied = website_appointment.copy()
        self.assertFalse(appointment_copied.is_published, "When we copy an appointment type, the new one should not be published")

        website_appointment.write({'is_published': True})
        appointment_copied = website_appointment.copy()
        self.assertFalse(appointment_copied.is_published, "The appointment copied should still be unpublished even if the later was published")

    @users('admin')
    def test_is_published_work_hours_appointment_type(self):
        work_hours_appointment = self.env['calendar.appointment.type'].create({
            'name': 'Work Hours Appointment',
            'category': 'work_hours',
        })
        self.assertTrue(work_hours_appointment.is_published, "A custom appointment type should be published at creation")
        with self.assertRaises(ValidationError):
            # A maximum of 1 work_hours per employee is allowed
            work_hours_appointment.copy()

    @users('admin')
    def test_is_published_write_appointment_type_category(self):
        appointment = self.env['calendar.appointment.type'].create({
            'name': 'Website Appointment',
            'category': 'website',
        })
        self.assertFalse(appointment.is_published, "A website appointment type should not be published at creation")
        
        appointment.write({'category': 'custom'})
        self.assertTrue(appointment.is_published, "Modifying an appointment type category to custom auto-published it")

        appointment.write({'category': 'website'})
        self.assertFalse(appointment.is_published, "Modifying an appointment type category to website unpublished it")

        appointment.write({'category': 'work_hours'})
        self.assertTrue(appointment.is_published, "Modifying an appointment type category to work_hours auto-published it")

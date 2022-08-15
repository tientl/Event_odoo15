# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.appointment.tests.common import AppointmentCommon
from odoo.addons.website.tests.test_website_visitor import MockVisitor
from odoo.exceptions import ValidationError
from odoo.tests.common import new_test_user
from odoo.tests import users


class WebsiteAppointmentTest(AppointmentCommon, MockVisitor):

    def test_create_appointment_type_from_website(self):
        """ Test that when creating an appointment type from the website, we use
        the visitor's timezone as fallback for the user's timezone """
        user = new_test_user(self.env, "test_user_1", groups="appointment.group_calendar_manager", email="test_user_1@nowhere.com", password="P@ssw0rd!", tz="")
        visitor = self.env['website.visitor'].create({"name": 'Test Visitor', "partner_id": user.partner_id.id})
        AppointmentType = self.env['calendar.appointment.type']
        with self.mock_visitor_from_request(force_visitor=visitor):
            # Test appointment timezone when user and visitor both don't have timezone
            AppointmentType.with_user(user).create_and_get_website_url(**{'name': 'Appointment UTC Timezone'})
            self.assertEqual(
                AppointmentType.search([
                    ('name', '=', 'Appointment UTC Timezone')
                ]).appointment_tz, 'UTC'
            )

            # Test appointment timezone when user doesn't have timezone and visitor have timezone
            visitor.timezone = 'Europe/Brussels'
            AppointmentType.with_user(user).create_and_get_website_url(**{'name': 'Appointment Visitor Timezone'})
            self.assertEqual(
                AppointmentType.search([
                    ('name', '=', 'Appointment Visitor Timezone')
                ]).appointment_tz, visitor.timezone
            )

            # Test appointment timezone when user has timezone
            user.tz = 'Asia/Calcutta'
            AppointmentType.with_user(user).create_and_get_website_url(**{'name': 'Appointment User Timezone'})
            self.assertEqual(
                AppointmentType.search([
                    ('name', '=', 'Appointment User Timezone')
                ]).appointment_tz, user.tz
            )

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

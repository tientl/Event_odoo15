# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from datetime import datetime, timedelta

from odoo.addons.appointment.tests.common import AppointmentCommon
from odoo.tests import common, tagged, users
from odoo.tests.common import new_test_user


@tagged('appointment_ui', '-at_install', 'post_install')
class AppointmentTest(AppointmentCommon, common.HttpCase):

    @users('apt_manager')
    def test_route_create_custom_appointment(self):
        self.authenticate(self.env.user.login, self.env.user.login)
        now = datetime.now()
        unique_slots = [{
            'start': (now + timedelta(hours=1)).replace(microsecond=0).isoformat(' '),
            'end': (now + timedelta(hours=2)).replace(microsecond=0).isoformat(' '),
            'allday': False,
        }, {
            'start': (now + timedelta(days=2)).replace(microsecond=0).isoformat(' '),
            'end': (now + timedelta(days=3)).replace(microsecond=0).isoformat(' '),
            'allday': True,
        }]
        request = self.url_open(
            "/appointment/calendar_appointment_type/create_custom",
            data=json.dumps({
                'params': {
                    'slots': unique_slots,
                }
            }),
            headers={"Content-Type": "application/json"},
        ).json()
        result = request.get('result', False)
        self.assertTrue(result.get('id'), 'The request returns the id of the custom appointment type')
        appointment_type = self.env['calendar.appointment.type'].browse(result['id'])
        self.assertEqual(appointment_type.name, "%s - Let's meet" % self.env.user.name)
        self.assertEqual(appointment_type.category, 'custom')
        self.assertEqual(len(appointment_type.slot_ids), 2, "Two slots have been created")
        self.assertTrue(all(slot.slot_type == 'unique' for slot in appointment_type.slot_ids), "All slots are 'unique'")

    @users('apt_manager')
    def test_route_search_create_work_hours(self):
        self.authenticate(self.env.user.login, self.env.user.login)
        request = self.url_open(
            "/appointment/calendar_appointment_type/search_create_work_hours",
            data=json.dumps({}),
            headers={"Content-Type": "application/json"},
        ).json()
        result = request.get('result', False)
        self.assertTrue(result.get('id'), 'The request returns the id of the custom appointment type')
        appointment_type = self.env['calendar.appointment.type'].browse(result['id'])
        self.assertEqual(appointment_type.category, 'work_hours')
        self.assertEqual(len(appointment_type.slot_ids), 14, "Two slots have been created")
        self.assertTrue(all(slot.slot_type == 'recurring' for slot in appointment_type.slot_ids), "All slots are 'recurring'")


@tagged('-at_install', 'post_install')
class CalendarTest(common.HttpCase):

    def test_accept_meeting_unauthenticated(self):
        user = new_test_user(self.env, "test_user_1", email="test_user_1@nowhere.com", password="P@ssw0rd!", tz="UTC")
        event = (
            self.env["calendar.event"]
            .create(
                {
                    "name": "Doom's day",
                    "start": datetime(2019, 10, 25, 8, 0),
                    "stop": datetime(2019, 10, 27, 18, 0),
                    "partner_ids": [(4, user.partner_id.id)],
                }
            )
        )
        token = event.attendee_ids[0].access_token
        url = "/calendar/meeting/accept?token=%s&id=%d" % (token, event.id)
        res = self.url_open(url)

        self.assertEqual(res.status_code, 200, "Response should = OK")
        event.attendee_ids[0].invalidate_cache()
        self.assertEqual(event.attendee_ids[0].state, "accepted", "Attendee should have accepted")

    def test_accept_meeting_authenticated(self):
        user = new_test_user(self.env, "test_user_1", email="test_user_1@nowhere.com", password="P@ssw0rd!", tz="UTC")
        event = (
            self.env["calendar.event"]
            .create(
                {
                    "name": "Doom's day",
                    "start": datetime(2019, 10, 25, 8, 0),
                    "stop": datetime(2019, 10, 27, 18, 0),
                    "partner_ids": [(4, user.partner_id.id)],
                }
            )
        )
        token = event.attendee_ids[0].access_token
        url = "/calendar/meeting/accept?token=%s&id=%d" % (token, event.id)
        self.authenticate("test_user_1", "P@ssw0rd!")
        res = self.url_open(url)

        self.assertEqual(res.status_code, 200, "Response should = OK")
        event.attendee_ids[0].invalidate_cache()
        self.assertEqual(event.attendee_ids[0].state, "accepted", "Attendee should have accepted")

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import common, tagged, users
from odoo.tests.common import new_test_user


@tagged('-at_install', 'post_install')
class AppointmentTest(common.HttpCase):

    def setUp(self):
        super(AppointmentTest, self).setUp()

        # calendar events can mess up the availability of our employee later on.
        self.env['calendar.event'].search([]).unlink()

        self.company = self.env['res.company'].search([], limit=1)

        self.resource_calendar = self.env['resource.calendar'].create({
            'name': 'Small Day',
            'company_id': self.company.id
        })

        self.resource_calendar.write({'attendance_ids': [(5, False, False)]})  # Wipe out all attendances

        self.attendance = self.env['resource.calendar.attendance'].create({
            'name': 'monday morning',
            'dayofweek': '0',
            'hour_from': 8,
            'hour_to': 12,
            'calendar_id': self.resource_calendar.id
        })

        self.first_user_in_brussel = self.env['res.users'].create({'name': 'Grace Slick', 'login': 'grace'})
        self.first_user_in_brussel.write({'tz': 'Europe/Brussels'})

        self.second_user_in_australia = self.env['res.users'].create({'name': 'Australian guy', 'login': 'australian'})
        self.second_user_in_australia.write({'tz': 'Australia/West'})

        self.employee_in_brussel = self.env['hr.employee'].create({
            'name': 'Grace Slick',
            'user_id': self.first_user_in_brussel.id,
            'company_id': self.company.id,
            'resource_calendar_id': self.resource_calendar.id
        })

        self.employee_in_australia = self.env['hr.employee'].create({
            'name': 'Chris Fisher',
            'user_id': self.second_user_in_australia.id,
            'company_id': self.company.id,
            'resource_calendar_id': self.resource_calendar.id,
        })

        self.appointment_in_brussel = self.env['calendar.appointment.type'].create({
            'name': 'Go ask Alice',
            'appointment_duration': 1,
            'min_schedule_hours': 1,
            'max_schedule_days': 15,
            'min_cancellation_hours': 1,
            'appointment_tz': 'Europe/Brussels',
            'employee_ids': [(4, self.employee_in_brussel.id, False)],
            'slot_ids': [(0, False, {'weekday': '1', 'start_hour': 9, 'end_hour': 10})]  # Yes, monday has either 0 or 1 as weekday number depending on the object it's in
        })

    def test_extreme_timezone_delta(self):
        context_australia = {'uid': self.second_user_in_australia.id,
                             'tz': self.second_user_in_australia.tz,
                             'lang': 'en_US'}

        # As if the second user called the function
        appointment = self.appointment_in_brussel.with_context(context_australia)

        # Do what the controller actually does
        months = appointment.sudo()._get_appointment_slots('Europe/Brussels', None)

        # Verifying
        utc_now = datetime.utcnow()
        mondays_count = 0
        # If the appointment has slots in the next month (the appointment can be taken 15 days in advance)
        # We'll have the next month displayed, and if the last day of current month is not a sunday
        # the first week of current month will be in the next month's starting week
        # but greyed and therefore without slot (and we should have already checked that day anyway)
        already_checked = set()

        for month in months:
            for week in month['weeks']:
                for day in week:
                    # For the sake of this test NOT to break each monday,
                    # we only control those mondays that are *strictly* superior than today
                    if day['day'] > utc_now.date() and\
                        day['day'] < (utc_now + relativedelta(days=appointment.max_schedule_days)).date() and\
                        day['day'].weekday() == 0 and\
                        day['day'] not in already_checked:

                        mondays_count += 1
                        already_checked.add(day['day'])
                        self.assertEqual(len(day['slots']), 1, 'Each monday should have only one slot')
                        slot = day['slots'][0]
                        self.assertEqual(slot['employee_id'], self.employee_in_brussel.id, 'The right employee should be available on each slot')
                        self.assertEqual(slot['hours'], '09:00', 'Slots hours has to be 09:00')  # We asked to display the slots as Europe/Brussels

        # Ensuring that we've gone through the *crucial* asserts at least once
        # It might be more accurate to assert mondays_count >= 2, but we don't want this test to break when it pleases
        self.assertGreaterEqual(mondays_count, 1, 'There should be at least one monday in the time range')

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

    def test_generate_recurring_slots(self):
        slots = self.appointment_in_brussel._get_appointment_slots('UTC')
        now = fields.Date.context_today(self.appointment_in_brussel)
        for month in slots:
            for week in month['weeks']:
                for day in week:
                    if day['day'] > now and\
                        day['day'] < now + relativedelta(days=self.appointment_in_brussel.max_schedule_days) and\
                        day['day'].month == week[-1]['day'].month and\
                        day['day'].isoweekday() == 1:

                        self.assertEqual(len(day['slots']), 1, "There should be 1 slot each monday")
                    elif day['day'] < now:
                        self.assertEqual(len(day['slots']), 0, "There should be no slot in the past")

    @users('admin')
    def test_generate_unique_slots(self):
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
        custom_appointment_type = self.env['calendar.appointment.type'].create({
            'category': 'custom',
            'slot_ids': [(0, 0, {
                'start_datetime': fields.Datetime.from_string(slot.get('start')),
                'end_datetime': fields.Datetime.from_string(slot.get('end')),
                'allday': slot.get('allday'),
                'slot_type': 'unique',
            }) for slot in unique_slots],
        })
        self.assertEqual(custom_appointment_type.category, 'custom', "It should be a custom appointment type")
        self.assertEqual(len(custom_appointment_type.slot_ids), 2, "Two slots should have been assigned to the appointment type")

        slots = custom_appointment_type._get_appointment_slots('UTC')
        for week in slots[0]['weeks']:
            for day in week:
                slot = day['slots']
                if (now + timedelta(hours=1)).date() == day['day']:
                    # Check if the month we are is greater than the one we are in if there are mutltiple months
                    if (now + timedelta(hours=1)).date().month > week[0]['day'].month and len(slots) > 1:
                        # Take the slots of the day in the next month (happens when we are in the end of the month)
                        slot = next(d['slots'] for d in slots[1]['weeks'][0] if d["day"] == day['day'])

                    self.assertEqual(len(slot), 1, "There should be 1 slot for this date")
                elif (now + timedelta(days=2)).date() == day['day']:
                    # Check if the month we are is greater than the one we are in if there are mutltiple months
                    if (now + timedelta(days=2)).date().month != week[0]['day'].month and len(slots) > 1:
                        # Take the slots of the day in the next month (happens when we are in the end of the month)
                        slot = next(d['slots'] for d in slots[1]['weeks'][0] if d["day"] == day['day'])

                    self.assertEqual(len(slot), 1, "There should be 1 all day slot for this date")
                    self.assertEqual(slot[0]['hours'], 'All day')
                else:
                    self.assertEqual(len(slot), 0, "There should be no slot for this date")

    @users('admin')
    def test_create_custom_appointment(self):
        self.authenticate('admin', 'admin')
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
        self.assertEqual(appointment_type.category, 'custom')
        self.assertEqual(len(appointment_type.slot_ids), 2, "Two slots have been created")
        self.assertTrue(all(slot.slot_type == 'unique' for slot in appointment_type.slot_ids), "All slots are 'unique'")

    @users('admin')
    def test_create_custom_appointment_without_employee(self):
        # No Validation Error, the actual employee should be set by default
        self.env['calendar.appointment.type'].create({
            'name': 'Custom without employee',
            'category': 'custom',
        })

    @users('admin')
    def test_create_custom_appointment_multiple_employees(self):
        with self.assertRaises(ValidationError):
            self.env['calendar.appointment.type'].create({
                'name': 'Custom without employee',
                'category': 'custom',
                'employee_ids': [self.employee_in_brussel.id, self.employee_in_australia.id]
            })

    @users('admin')
    def test_create_work_hours_appointment_without_employee(self):
        # No Validation Error, the actual employee should be set by default
        self.env['calendar.appointment.type'].create({
            'name': 'Work hours without employee',
            'category': 'work_hours',
        })

    @users('admin')
    def test_create_work_hours_appointment_multiple_employees(self):
        with self.assertRaises(ValidationError):
            self.env['calendar.appointment.type'].create({
                'name': 'Work hours without employee',
                'category': 'work_hours',
                'employee_ids': [self.employee_in_brussel.id, self.employee_in_australia.id]
            })

    @users('admin')
    def test_search_create_work_hours(self):
        self.authenticate('admin', 'admin')
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

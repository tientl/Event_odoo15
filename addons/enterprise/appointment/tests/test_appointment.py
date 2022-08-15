# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta
from freezegun import freeze_time

from odoo.addons.appointment.tests.common import AppointmentCommon
from odoo.exceptions import ValidationError
from odoo.tests import tagged, users


@tagged('appointment_slots')
class AppointmentTest(AppointmentCommon):

    @users('apt_manager')
    def test_appointment_share(self):
        apt_types = self.env['calendar.appointment.type'].create([
            {
                'category': 'custom',
                'employee_ids': self.staff_employee_bxls,
                'name': 'Appointment 1',
            }, {
                'category': 'custom',
                'employee_ids': self.staff_employee_aust,
                'name': 'Appointment 2',
            },
        ])

        apt_share_wizard = self.env['calendar.appointment.share'].create({
            'appointment_type_ids' : apt_types[0],
        })
        self.assertEqual(apt_types[0].employee_ids, apt_share_wizard.employee_ids)

        apt_share_wizard.appointment_type_ids = apt_types[1]
        self.assertEqual(apt_types[1].employee_ids, apt_share_wizard.employee_ids)

    @users('apt_manager')
    def test_appointment_type_create(self):
        # Custom: current employee set as default, otherwise accepts only 1 employee
        apt_type = self.env['calendar.appointment.type'].create({
            'category': 'custom',
            'name': 'Custom without employee',
        })
        self.assertEqual(apt_type.employee_ids, self.apt_manager_employee)

        apt_type = self.env['calendar.appointment.type'].create({
            'category': 'custom',
            'employee_ids': [(4, self.staff_employees[0].id)],
            'name': 'Custom with employee',
        })
        self.assertEqual(apt_type.employee_ids, self.staff_employees[0])

        with self.assertRaises(ValidationError):
            self.env['calendar.appointment.type'].create({
                'category': 'custom',
                'employee_ids': self.staff_employees.ids,
                'name': 'Custom with employees',
            })

        # Work hours: only 1 / employee
        apt_type = self.env['calendar.appointment.type'].create({
            'category': 'work_hours',
            'name': 'Work hours on me',
        })
        self.assertEqual(apt_type.employee_ids, self.apt_manager_employee)

        with self.assertRaises(ValidationError):
            self.env['calendar.appointment.type'].create({
                'category': 'work_hours',
                'name': 'Work hours on me, duplicate',
            })

        with self.assertRaises(ValidationError):
            self.env['calendar.appointment.type'].create({
                'name': 'Work hours without employee',
                'category': 'work_hours',
                'employee_ids': [self.staff_employees.ids]
            })

    @users('apt_manager')
    def test_generate_slots_recurring(self):
        """ Generates recurring slots, check begin and end slot boundaries. """
        apt_type = self.apt_type_bxls_2days.with_user(self.env.user)

        with freeze_time(self.reference_now):
            slots = apt_type._get_appointment_slots('Europe/Brussels')

        global_slots_startdate = self.reference_now_monthweekstart
        global_slots_enddate = date(2022, 3, 6)  # last day of last week of February
        self.assertSlots(
            slots,
            [{'name_formated': 'February 2022',
              'month_date': datetime(2022, 2, 1),
              'weeks_count': 5,  # 31/01 -> 28/02 (06/03)
             }
            ],
            {'enddate': global_slots_enddate,
             'startdate': global_slots_startdate,
             'slots_start_hours': [8, 9, 10, 11, 13],  # based on appointment type start hours of slots but 12 is pause midi
             'slots_startdate': self.reference_monday.date(),  # first Monday after reference_now
             'slots_weekdays_nowork': range(2, 7)  # working hours only on Monday/Tuesday (0, 1)
            }
        )

    @users('apt_manager')
    def test_generate_slots_recurring_UTC(self):
        """ Generates recurring slots, check begin and end slot boundaries. Force
        UTC results event if everything is Europe/Brussels based. """
        apt_type = self.apt_type_bxls_2days.with_user(self.env.user)

        with freeze_time(self.reference_now):
            slots = apt_type._get_appointment_slots('UTC')

        global_slots_startdate = self.reference_now_monthweekstart
        global_slots_enddate = date(2022, 3, 6)  # last day of last week of February
        self.assertSlots(
            slots,
            [{'name_formated': 'February 2022',
              'month_date': datetime(2022, 2, 1),
              'weeks_count': 5,  # 31/01 -> 28/02 (06/03)
             }
            ],
            {'enddate': global_slots_enddate,
             'startdate': global_slots_startdate,
             'slots_start_hours': [7, 8, 9, 10, 12],  # based on appointment type start hours of slots but 12 is pause midi
             'slots_startdate': self.reference_monday.date(),  # first Monday after reference_now
             'slots_weekdays_nowork': range(2, 7)  # working hours only on Monday/Tuesday (0, 1)
            }
        )

    @users('apt_manager')
    def test_generate_slots_recurring_wleaves(self):
        """ Generates recurring slots, check begin and end slot boundaries
        with leaves involved. """
        apt_type = self.apt_type_bxls_2days.with_user(self.env.user)

        # create personal leaves
        _leaves = self._create_leaves(
            self.staff_user_bxls,
            [(self.reference_monday + timedelta(days=1),  # 2 hours first Tuesday
              self.reference_monday + timedelta(days=1, hours=2)),
             (self.reference_monday + timedelta(days=7), # next Monday: one hour
              self.reference_monday + timedelta(days=7, hours=1))
            ],
        )
        # add global leaves
        _leaves += self._create_leaves(
            self.env['res.users'],
            [(self.reference_monday + timedelta(days=8), # next Tuesday is bank holiday
              self.reference_monday + timedelta(days=8, hours=12))
            ],
            calendar=self.staff_user_bxls.resource_calendar_id,
        )

        with freeze_time(self.reference_now):
            slots = apt_type._get_appointment_slots('Europe/Brussels')

        global_slots_startdate = self.reference_now_monthweekstart
        global_slots_enddate = date(2022, 3, 6)  # last day of last week of February
        self.assertSlots(
            slots,
            [{'name_formated': 'February 2022',
              'month_date': datetime(2022, 2, 1),
              'weeks_count': 5,  # 31/01 -> 28/02 (06/03)
             }
            ],
            {'enddate': global_slots_enddate,
             'startdate': global_slots_startdate,
             'slots_day_specific': {
                (self.reference_monday + timedelta(days=1)).date(): [
                    {'end': 11, 'start': 10},
                    {'end': 12, 'start': 11},
                    {'end': 14, 'start': 13}
                ],  # leaves on 7-9 UTC
                (self.reference_monday + timedelta(days=7)).date(): [
                    {'end': 10, 'start': 9},
                    {'end': 11, 'start': 10},
                    {'end': 12, 'start': 11},
                    {'end': 14, 'start': 13}
                ],  # leaves on 7-8
                (self.reference_monday + timedelta(days=8)).date(): [],  # 12 hours long bank holiday
             },
             'slots_start_hours': [8, 9, 10, 11, 13],  # based on appointment type start hours of slots but 12 is pause midi
             'slots_startdate': self.reference_monday.date(),  # first Monday after reference_now
             'slots_weekdays_nowork': range(2, 7)  # working hours only on Monday/Tuesday (0, 1)
            }
        )

    @users('apt_manager')
    def test_generate_slots_recurring_wmeetings(self):
        """ Generates recurring slots, check begin and end slot boundaries
        with leaves involved. """
        apt_type = self.apt_type_bxls_2days.with_user(self.env.user)

        # create meetings
        _meetings = self._create_meetings(
            self.staff_user_bxls,
            [(self.reference_monday + timedelta(days=1),  # 3 hours first Tuesday
              self.reference_monday + timedelta(days=1, hours=3),
              False
             ),
             (self.reference_monday + timedelta(days=7), # next Monday: one full day
              self.reference_monday + timedelta(days=7, hours=1),
              True,
             ),
             (self.reference_monday + timedelta(days=8, hours=2), # 1 hour next Tuesday (9 UTC)
              self.reference_monday + timedelta(days=8, hours=3),
              False,
             ),
             (self.reference_monday + timedelta(days=8, hours=3), # 1 hour next Tuesday (10 UTC, declined)
              self.reference_monday + timedelta(days=8, hours=4),
              False,
             ),
             (self.reference_monday + timedelta(days=8, hours=5), # 2 hours next Tuesday (12 UTC)
              self.reference_monday + timedelta(days=8, hours=7),
              False,
             ),
            ]
        )
        attendee = _meetings[-2].attendee_ids.filtered(lambda att: att.partner_id == self.staff_user_bxls.partner_id)
        attendee.do_decline()

        with freeze_time(self.reference_now):
            slots = apt_type._get_appointment_slots('Europe/Brussels')

        global_slots_startdate = self.reference_now_monthweekstart
        global_slots_enddate = date(2022, 3, 6)  # last day of last week of February
        self.assertSlots(
            slots,
            [{'name_formated': 'February 2022',
              'month_date': datetime(2022, 2, 1),
              'weeks_count': 5,  # 31/01 -> 28/02 (06/03)
             }
            ],
            {'enddate': global_slots_enddate,
             'startdate': global_slots_startdate,
             'slots_day_specific': {
                (self.reference_monday + timedelta(days=1)).date(): [
                    {'end': 12, 'start': 11},
                    {'end': 14, 'start': 13},
                ],  # meetings on 7-10 UTC
                (self.reference_monday + timedelta(days=7)).date(): [],  # on meeting "allday"
                (self.reference_monday + timedelta(days=8)).date(): [
                    {'end': 9, 'start': 8},
                    {'end': 10, 'start': 9}, 
                    {'end': 12, 'start': 11},
                ],  # meetings 9-10 and 12-14
             },
             'slots_start_hours': [8, 9, 10, 11, 13],  # based on appointment type start hours of slots but 12 is pause midi
             'slots_startdate': self.reference_monday.date(),  # first Monday after reference_now
             'slots_weekdays_nowork': range(2, 7)  # working hours only on Monday/Tuesday (0, 1)
            }
        )

    @users('apt_manager')
    def test_generate_slots_unique(self):
        """ Check unique slots (note: custom appointment type does not check working
        hours). """
        unique_slots = [{
            'start_datetime': self.reference_monday.replace(microsecond=0),
            'end_datetime': (self.reference_monday + timedelta(hours=1)).replace(microsecond=0),
            'allday': False,
        }, {
            'start_datetime': (self.reference_monday + timedelta(days=1)).replace(microsecond=0),
            'end_datetime': (self.reference_monday + timedelta(days=2)).replace(microsecond=0),
            'allday': True,
        }]
        apt_type = self.env['calendar.appointment.type'].create({
            'category': 'custom',
            'name': 'Custom with unique slots',
            'slot_ids': [(5, 0)] + [
                (0, 0, {'allday': slot['allday'],
                        'end_datetime': slot['end_datetime'],
                        'slot_type': 'unique',
                        'start_datetime': slot['start_datetime'],
                       }
                ) for slot in unique_slots
            ],
        })
        self.assertEqual(apt_type.category, 'custom', "It should be a custom appointment type")
        self.assertEqual(apt_type.employee_ids, self.apt_manager_employee)
        self.assertEqual(len(apt_type.slot_ids), 2, "Two slots should have been assigned to the appointment type")

        with freeze_time(self.reference_now):
            slots = apt_type._get_appointment_slots('Europe/Brussels')

        global_slots_startdate = self.reference_now_monthweekstart
        global_slots_enddate = date(2022, 3, 6)  # last day of last week of February
        self.assertSlots(
            slots,
            [{'name_formated': 'February 2022',
              'month_date': datetime(2022, 2, 1),
              'weeks_count': 5,  # 31/01 -> 28/02 (06/03)
             }
            ],
            {'enddate': global_slots_enddate,
             'startdate': global_slots_startdate,
             'slots_day_specific': {
                self.reference_monday.date(): [{'end': 9, 'start': 8}],  # first unique 1 hour long
                (self.reference_monday + timedelta(days=1)).date(): [{'allday': True, 'end': False, 'start': 8}],  # second unique all day-based
             },
             'slots_start_hours': [],  # all slots in this tests are unique, other dates have no slots
             'slots_startdate': self.reference_monday.date(),  # first Monday after reference_now
             'slots_weekdays_nowork': range(2, 7)  # working hours only on Monday/Tuesday (0, 1)
            }
        )

    @users('staff_user_aust')
    def test_timezone_delta(self):
        """ Test timezone delta. Not sure what original test was really doing. """
        # As if the second user called the function
        apt_type = self.apt_type_bxls_2days.with_user(self.env.user).with_context(
            lang='en_US',
            tz=self.staff_user_aust.tz,
            uid=self.staff_user_aust.id,
        )

        # Do what the controller actually does, aka sudo
        with freeze_time(self.reference_now):
            slots = apt_type.sudo()._get_appointment_slots('Australia/West', employee=None)

        global_slots_startdate = self.reference_now_monthweekstart
        global_slots_enddate = date(2022, 4, 3)  # last day of last week of March
        self.assertSlots(
            slots,
            [{'name_formated': 'February 2022',
              'month_date': datetime(2022, 2, 1),
              'weeks_count': 5,  # 31/01 -> 28/02 (06/03)
             },
             {'name_formated': 'March 2022',
              'month_date': datetime(2022, 3, 1),
              'weeks_count': 5,  # 28/02 -> 28/03 (03/04)
             }
            ],
            {'enddate': global_slots_enddate,
             'startdate': global_slots_startdate,
             'slots_enddate': self.reference_now.date() + timedelta(days=15),  # maximum 2 weeks of slots
             'slots_start_hours': [15, 16, 17, 18, 20],  # based on appointment type start hours of slots but 12 is pause midi, set in UTC+8
             'slots_startdate': self.reference_monday.date(),  # first Monday after reference_now
             'slots_weekdays_nowork': range(2, 7)  # working hours only on Monday/Tuesday (0, 1)
            }
        )

    @users('apt_manager')
    def test_unique_slots_availabilities(self):
        """ Check that the availability of each unique slot is correct.
        First we test that the 2 unique slots of the custom appointment type
        are available. Then we check that there is now only 1 availability left
        after the creation of a meeting which encompasses a slot. """
        reference_monday = self.reference_monday.replace(microsecond=0)
        unique_slots = [{
            'allday': False,
            'end_datetime': reference_monday + timedelta(hours=1),
            'start_datetime': reference_monday,
        }, {
            'allday': False,
            'end_datetime': reference_monday + timedelta(hours=3),
            'start_datetime': reference_monday + timedelta(hours=2),
        }]
        apt_type = self.env['calendar.appointment.type'].create({
            'category': 'custom',
            'name': 'Custom with unique slots',
            'slot_ids': [(0, 0, {
                'allday': slot['allday'],
                'end_datetime': slot['end_datetime'],
                'slot_type': 'unique',
                'start_datetime': slot['start_datetime'],
                }) for slot in unique_slots
            ],
        })

        with freeze_time(self.reference_now):
            slots = apt_type._get_appointment_slots('UTC')
        # get all monday slots where apt_manager is available
        available_unique_slots = self._filter_appointment_slots(
            slots,
            filter_months=[(2, 2022)],
            filter_weekdays=[0],
            filter_employees=self.apt_manager_employee)
        self.assertEqual(len(available_unique_slots), 2)

        # Create a meeting encompassing the first unique slot
        self._create_meetings(self.apt_manager, [(
            unique_slots[0]['start_datetime'],
            unique_slots[0]['end_datetime'],
            False,
        )])

        with freeze_time(self.reference_now):
            slots = apt_type._get_appointment_slots('UTC')
        available_unique_slots = self._filter_appointment_slots(
            slots,
            filter_months=[(2, 2022)],
            filter_weekdays=[0],
            filter_employees=self.apt_manager_employee)
        self.assertEqual(len(available_unique_slots), 1)
        self.assertEqual(
            available_unique_slots[0]['datetime'],
            unique_slots[1]['start_datetime'].strftime('%Y-%m-%d %H:%M:%S'),
        )

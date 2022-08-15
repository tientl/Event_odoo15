# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random
import time

from datetime import date, timedelta
from freezegun import freeze_time
from logging import getLogger

from odoo.addons.appointment.tests.common import AppointmentCommon
from odoo.addons.website.tests.test_performance import UtilPerf
from odoo.tests import tagged, users
from odoo.tests.common import warmup

_logger = getLogger(__name__)


class AppointmentPerformanceCase(AppointmentCommon):

    @classmethod
    def setUpClass(cls):
        super(AppointmentPerformanceCase, cls).setUpClass()

        cls.test_calendar = cls.env['resource.calendar'].create({
            'company_id': cls.company_admin.id,
            'name': 'Test Calendar',
            'tz': 'Europe/Brussels',
        })

        cls.staff_users = cls.env['res.users'].with_context(cls._test_context).create([
            {'company_id': cls.company_admin.id,
             'company_ids': [(4, cls.company_admin.id)],
             'email': 'brussels.%s@test.example.com' % idx,
             'groups_id': [(4, cls.env.ref('base.group_user').id)],
             'name': 'Employee Brussels %s' % idx,
             'login': 'staff_users_bxl_%s' % idx,
             'notification_type': 'email',
             'tz': 'Europe/Brussels',
            } for idx in range(20)
        ])

        # User resources and employees
        cls.staff_users_resources = cls.env['resource.resource'].create([
            {'calendar_id': cls.test_calendar.id,
             'company_id': user.company_id.id,
             'name': user.name,
             'user_id': user.id,
             'tz': user.tz,
            } for user in cls.staff_users
        ])
        cls.staff_users_employees = cls.env['hr.employee'].create([
            {'company_id': user.company_id.id,
             'resource_calendar_id': cls.test_calendar.id,
             'resource_id': cls.staff_users_resources[user_idx].id,
            } for user_idx, user in enumerate(cls.staff_users)
        ])

        # Events and leaves
        cls.test_events = cls.env['calendar.event'].with_context(cls._test_context).create([
            {'attendee_ids': [(0, 0, {'partner_id': user.partner_id.id})],
             'name': 'Event for %s' % user.name,
             'partner_ids': [(4, user.partner_id.id)],
             'start': cls.reference_monday + timedelta(weeks=week_idx, days=day_idx, hours=(user_idx / 4)),
             'stop': cls.reference_monday + timedelta(weeks=week_idx, days=day_idx, hours=(user_idx / 4) + 1),
             'user_id': user.id,
            }
            for day_idx in range(5)
            for week_idx in range(5)
            for user_idx, user in enumerate(cls.staff_users)
        ])
        cls.test_leaves = cls.env['resource.calendar.leaves'].with_context(cls._test_context).create([
            {'calendar_id': user.resource_calendar_id.id,
             'company_id': user.company_id.id,
             'date_from': cls.reference_monday + timedelta(weeks=week_idx * 2, days=(user_idx / 4), hours=2),
             'date_to': cls.reference_monday + timedelta(weeks=week_idx * 2, days=(user_idx / 4), hours=8),
             'name': 'Leave for %s' % user.name,
             'resource_id': user.resource_ids[0].id,
             'time_type': 'leave',
            }
            for week_idx in range(5)  # one leave every 2 weeks
            for user_idx, user in enumerate(cls.staff_users)
        ])

        cls.test_apt_type = cls.env['calendar.appointment.type'].create({
            'appointment_tz': 'Europe/Brussels',
            'appointment_duration': 1,
            'assign_method': 'random',
            'category': 'website',
            'employee_ids': [(4, employee.id) for employee in cls.staff_users_employees],
            'max_schedule_days': 60,
            'min_cancellation_hours': 1,
            'min_schedule_hours': 1,
            'name': 'Test Appointment Type',
            'slot_ids': [
                (0, 0, {'end_hour': hour + 1,
                        'start_hour': hour,
                        'weekday': weekday,
                        })
                for weekday in ['1', '2', '3', '4', '5']
                for hour in range(8, 16)
            ],
        })

    def setUp(self):
        super(AppointmentPerformanceCase, self).setUp()
        # patch registry to simulate a ready environment
        self.patch(self.env.registry, 'ready', True)
        self._flush_tracking()


@tagged('appointment_performance', 'post_install', '-at_install')
class AppointmentTest(AppointmentPerformanceCase):

    def test_appointment_initial_values(self):
        """ Check initial values to ease understanding and reproducing tests. """
        self.assertEqual(len(self.test_calendar.attendance_ids), 10)
        self.assertEqual(len(self.test_apt_type.slot_ids), 40)
        self.assertTrue(all(employee.resource_id for employee in self.staff_users_employees))
        self.assertTrue(all(employee.resource_id.calendar_id for employee in self.staff_users_employees))
        self.assertTrue(all(employee.user_id for employee in self.staff_users_employees))

    @users('staff_user_bxls')
    def test_get_appointment_slots_custom(self):
        """ Custom type: mono user, unique slots, work hours check. """
        apt_type_custom_bxls = self.env['calendar.appointment.type'].sudo().create({
            'appointment_tz': 'Europe/Brussels',
            'appointment_duration': 1,
            'assign_method': 'random',
            'category': 'custom',
            'employee_ids': [(4, self.staff_users_employees[0].id)],
            'location': 'Bxls Office',
            'name': 'Bxls Appt Type',
            'min_cancellation_hours': 1,
            'min_schedule_hours': 1,
            'max_schedule_days': 30,
            'slot_ids': [
                (0, 0, {'end_datetime': self.reference_monday + timedelta(days=day, hours=hour + 1),
                        'start_datetime': self.reference_monday + timedelta(days=day, hours=hour),
                        'slot_type': 'unique',
                        'weekday': '1',  # not used actually
                       }
                )
                for day in range(30)
                for hour in range(8, 16)
            ],
        })
        apt_type_custom_bxls.flush()
        apt_type_custom_bxls = apt_type_custom_bxls.with_user(self.env.user)

        # with self.profile(collectors=['sql']) as profile:
        with self.mockAppointmentCalls(), \
             self.assertQueryCount(staff_user_bxls=41):  # apt only: 41
            t0 = time.time()
            res = apt_type_custom_bxls._get_appointment_slots('Europe/Brussels', reference_date=self.reference_now)
            t1 = time.time()

        _logger.info('Called _get_appointment_slots, time %.3f', t1 - t0)
        _logger.info('Called methods\nSearch calendar event called %s\n'
                     'Search count calendar event called %s\n'
                     'Partner calendar check called %s\n'
                     'Resource Calendar work intervals batch called %s',
                     self._mock_calevent_search.call_count,
                     self._mock_calevent_search_count.call_count,
                     self._mock_partner_calendar_check.call_count,
                     self._mock_cal_work_intervals.call_count)
        # Time before optimization: ~0.30
        # Method count before optimization: 263 - 262 - 262 - 1
        # After optimization: ~0.06, 1 - 0 - 0 - 0

        global_slots_startdate = self.reference_now_monthweekstart
        global_slots_enddate = date(2022, 4, 3)  # last day of last week of May
        self.assertSlots(
            res,
            [{'name_formated': 'February 2022',
              'weeks_count': 5,  # 31/01 -> 28/02 (06/03)
             },
             {'name_formated': 'March 2022',
              'weeks_count': 5,  # 28/02 -> 28/03 (03/04)
             }
            ],
            {'enddate': global_slots_enddate,
             'startdate': global_slots_startdate,
            }
        )

    @users('staff_user_bxls')
    def test_get_appointment_slots_website_whours(self):
        """ Website type: multi users (choose first available), with working hours
        involved. """
        random.seed(1871)  # fix shuffle in _slots_available
        apt_type = self.test_apt_type.with_user(self.env.user)

        # with self.profile(collectors=['sql']) as profile:
        with self.mockAppointmentCalls(), \
             self.assertQueryCount(staff_user_bxls=72):
            t0 = time.time()
            res = apt_type._get_appointment_slots('Europe/Brussels', reference_date=self.reference_now)
            t1 = time.time()

        _logger.info('Called _get_appointment_slots, time %.3f', t1 - t0)
        _logger.info('Called methods\nSearch calendar event called %s\n'
                     'Search count calendar event called %s\n'
                     'Partner calendar check called %s\n'
                     'Resource Calendar work intervals batch called %s',
                     self._mock_calevent_search.call_count,
                     self._mock_calevent_search_count.call_count,
                     self._mock_partner_calendar_check.call_count,
                     self._mock_cal_work_intervals.call_count)
        # Time before optimization: ~0.7
        # Method count before optimization: 358 - 355 - 355 - 20
        # After optimization: ~0.2, 1 - 0 - 0 - 1

        global_slots_startdate = self.reference_now_monthweekstart
        global_slots_enddate = date(2022, 5, 1)  # last day of last week of April
        self.assertSlots(
            res,
            [{'name_formated': 'February 2022',
              'weeks_count': 5,  # 31/01 -> 28/02 (06/03)
             },
             {'name_formated': 'March 2022',
              'weeks_count': 5,  # 28/02 -> 28/03 (03/04)
             },
             {'name_formated': 'April 2022',
              'weeks_count': 5,  # 28/02 -> 28/03 (03/04)
             }
            ],
            {'enddate': global_slots_enddate,
             'slots_duration': 1,
             'slots_hours': range(8, 16, 1),
             'slots_startdt': self.reference_monday,
             'startdate': global_slots_startdate,
            }
        )

    @users('staff_user_bxls')
    def test_get_appointment_slots_website_whours_short(self):
        """ Website type: multi users (choose first available), with working hours
        involved. """
        random.seed(1871)  # fix shuffle in _slots_available
        self.test_apt_type.write({'max_schedule_days': 10})
        self.test_apt_type.flush()
        apt_type = self.test_apt_type.with_user(self.env.user)

        # with self.profile(collectors=['sql']) as profile:
        with self.mockAppointmentCalls(), \
             self.assertQueryCount(staff_user_bxls=72):
            t0 = time.time()
            res = apt_type._get_appointment_slots('Europe/Brussels', reference_date=self.reference_now)
            t1 = time.time()

        _logger.info('Called _get_appointment_slots, time %.3f', t1 - t0)
        _logger.info('Called methods\nSearch calendar event called %s\n'
                     'Search count calendar event called %s\n'
                     'Partner calendar check called %s\n'
                     'Resource Calendar work intervals batch called %s',
                     self._mock_calevent_search.call_count,
                     self._mock_calevent_search_count.call_count,
                     self._mock_partner_calendar_check.call_count,
                     self._mock_cal_work_intervals.call_count)
        # Time before optimization: ~0.2
        # Method count before optimization: 74 - 71 - 71 - 20
        # After optimization: ~0.1, 1 - 0 - 0 - 1

        global_slots_startdate = self.reference_now_monthweekstart
        global_slots_enddate = date(2022, 3, 6)  # last day of last week of Feb
        self.assertSlots(
            res,
            [{'name_formated': 'February 2022',
              'weeks_count': 5,  # 31/01 -> 28/02 (06/03)
             }
            ],
            {'enddate': global_slots_enddate,
             'startdate': global_slots_startdate,
            }
        )

    @users('staff_user_bxls')
    def test_get_appointment_slots_work_hours(self):
        """ Work hours type: mono user, involved work hours check. """
        self.apt_type_bxls_2days.write({
            'category': 'work_hours',
            'employee_ids': [(5, 0), (4, self.staff_users_employees[0].id)],
            'max_schedule_days': 90,
            'slot_ids': [(5, 0)] + [  # while loop in _slots_generate generates the actual slots
                (0, 0, {'end_hour': 23.99,
                        'start_hour': hour * 0.5,
                        'weekday': str(day + 1),
                       }
                )
                for hour in range(2)
                for day in range(7)
            ],
            })
        self.apt_type_bxls_2days.flush()
        apt_type = self.apt_type_bxls_2days.with_user(self.env.user)

        # with self.profile(collectors=['sql']) as profile:
        with self.mockAppointmentCalls(), \
             self.assertQueryCount(staff_user_bxls=60):
            t0 = time.time()
            res = apt_type._get_appointment_slots('Europe/Brussels', reference_date=self.reference_now)
            t1 = time.time()

        _logger.info('Called _get_appointment_slots, time %.3f', t1 - t0)
        _logger.info('Called methods\nSearch calendar event called %s\n'
                     'Search count calendar event called %s\n'
                     'Partner calendar check called %s\n'
                     'Resource Calendar work intervals batch called %s',
                     self._mock_calevent_search.call_count,
                     self._mock_calevent_search_count.call_count,
                     self._mock_partner_calendar_check.call_count,
                     self._mock_cal_work_intervals.call_count)
        # Time before optimization: ~1.00
        # Method count before optimization: 863 - 862 - 862 - 1
        # After optimization: ~0.33, 1 - 0 - 0 - 1

        global_slots_startdate = self.reference_now_monthweekstart
        global_slots_enddate = date(2022, 6, 5)  # last day of last week of May
        self.assertSlots(
            res,
            [{'name_formated': 'February 2022',
              'weeks_count': 5,  # 31/01 -> 28/02 (06/03)
             },
             {'name_formated': 'March 2022',
              'weeks_count': 5,  # 28/02 -> 28/03 (03/04)
             },
             {'name_formated': 'April 2022',
              'weeks_count': 5,
             },
             {'name_formated': 'May 2022',
              'weeks_count': 6,
             },
            ],
            {'enddate': global_slots_enddate,
             'startdate': global_slots_startdate,
            }
        )

    @users('staff_user_bxls')
    def test_get_appointment_slots_work_hours_short(self):
        """ Work hours type: mono user, involved work hours check. """
        self.apt_type_bxls_2days.write({
            'category': 'work_hours',
            'employee_ids': [(5, 0), (4, self.staff_users_employees[0].id)],
            'max_schedule_days': 10,
            'slot_ids': [(5, 0)] + [  # while loop in _slots_generate generates the actual slots
                (0, 0, {'end_hour': 23.99,
                        'start_hour': hour * 0.5,
                        'weekday': str(day + 1),
                       }
                )
                for hour in range(2)
                for day in range(7)
            ],
        })
        self.apt_type_bxls_2days.flush()
        apt_type = self.apt_type_bxls_2days.with_user(self.env.user)

        # with self.profile(collectors=['sql']) as profile:
        with self.mockAppointmentCalls(), \
             self.assertQueryCount(staff_user_bxls=60):
            t0 = time.time()
            res = apt_type._get_appointment_slots('Europe/Brussels', reference_date=self.reference_now)
            t1 = time.time()

        _logger.info('Called _get_appointment_slots, time %.3f', t1 - t0)
        _logger.info('Called methods\nSearch calendar event called %s\n'
                     'Search count calendar event called %s\n'
                     'Partner calendar check called %s\n'
                     'Resource Calendar work intervals batch called %s',
                     self._mock_calevent_search.call_count,
                     self._mock_calevent_search_count.call_count,
                     self._mock_partner_calendar_check.call_count,
                     self._mock_cal_work_intervals.call_count)
        # Time before optimization: ~0.30
        # Method count before optimization: 103 - 102 - 102 - 1
        # After optimization: ~0.07, 1 - 0 - 0 - 1

        global_slots_startdate = self.reference_now_monthweekstart
        global_slots_enddate = date(2022, 3, 6)  # last day of last week of Feb
        self.assertSlots(
            res,
            [{'name_formated': 'February 2022',
              'weeks_count': 5,  # 31/01 -> 28/02 (06/03)
             }
            ],
            {'enddate': global_slots_enddate,
             'startdate': global_slots_startdate,
            }
        )


@tagged('appointment_performance', 'post_install', '-at_install')
class AppointmentUIPerformanceCase(AppointmentPerformanceCase, UtilPerf):

    @classmethod
    def setUpClass(cls):
        super(AppointmentUIPerformanceCase, cls).setUpClass()
        # if website_livechat is installed, disable it
        if 'website' in cls.env and 'channel_id' in cls.env['website']:
            cls.env['website'].search([]).channel_id = False

    def _test_url_open(self, url):
        url += ('?' not in url and '?' or '') + '&nocache'
        return self.url_open(url)


@tagged('appointment_performance', 'post_install', '-at_install')
class OnlineAppointmentPerformance(AppointmentUIPerformanceCase):

    @warmup
    def test_appointment_type_page_website_whours_user(self):
        random.seed(1871)  # fix shuffle in _slots_available

        t0 = time.time()
        with freeze_time(self.reference_now):
            self.authenticate('staff_user_bxls', 'staff_user_bxls')
            with self.assertQueryCount(default=46):  # apt only: 40 (website: 43)
                self._test_url_open('/calendar/%i' % self.test_apt_type.id)
        t1 = time.time()

        _logger.info('Browsed /calendar/%i, time %.3f', self.test_apt_type.id, t1 - t0)
        # Time before optimization: ~0.80 (but with boilerplate)
        # After optimization: ~0.35

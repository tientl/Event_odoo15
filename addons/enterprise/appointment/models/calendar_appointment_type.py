# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import calendar as cal
import random
import pytz
from datetime import datetime, timedelta, time
from dateutil import rrule
from dateutil.relativedelta import relativedelta
from babel.dates import format_datetime
from werkzeug.urls import url_join

from odoo import api, fields, models, _, Command
from odoo.exceptions import ValidationError
from odoo.tools.misc import get_lang
from odoo.addons.base.models.res_partner import _tz_get
from odoo.addons.http_routing.models.ir_http import slug
from odoo.osv.expression import AND


class CalendarAppointmentType(models.Model):
    _name = "calendar.appointment.type"
    _description = "Appointment Type"
    _inherit = ['mail.thread']
    _order = "sequence, id"

    @api.model
    def default_get(self, default_fields):
        result = super().default_get(default_fields)
        if 'category' not in default_fields or result.get('category') in ['custom', 'work_hours']:
            if not result.get('name'):
                result['name'] = _("%s - Let's meet", self.env.user.name)
            if (not default_fields or 'employee_ids' in default_fields) and not result.get('employee_ids'):
                if not self.env.user.employee_id:
                    raise ValueError(_("An employee should be set on the current user to create the appointment type"))
                result['employee_ids'] = [Command.set(self.env.user.employee_id.ids)]
        return result

    sequence = fields.Integer('Sequence', default=10)
    name = fields.Char('Appointment Type', required=True, translate=True)
    active = fields.Boolean(default=True)
    category = fields.Selection([
        ('website', 'Website'),
        ('custom', 'Custom'),
        ('work_hours', 'Work Hours')
        ], string="Category", default="website",
        help="""Used to define this appointment type's category.
        Can be one of:
            - Website: the default category, the people can access and shedule the appointment with employees from the website
            - Custom: the employee will create and share to an user a custom appointment type with hand-picked time slots
            - Work Hours: a special type of appointment type that is used by one employee and which takes the working hours of this
                employee as availabilities. This one uses recurring slot that englobe the entire week to display all possible slots
                based on its working hours and availabilities""")
    min_schedule_hours = fields.Float('Schedule before (hours)', required=True, default=1.0)
    max_schedule_days = fields.Integer('Schedule not after (days)', required=True, default=15)
    min_cancellation_hours = fields.Float('Cancel Before (hours)', required=True, default=1.0)
    appointment_duration = fields.Float('Appointment Duration', required=True, default=1.0)

    reminder_ids = fields.Many2many('calendar.alarm', string="Reminders")
    location = fields.Char('Location', help="Location of the appointments")
    message_confirmation = fields.Html('Confirmation Message', translate=True)
    message_intro = fields.Html('Introduction Message', translate=True)

    country_ids = fields.Many2many(
        'res.country', 'appointment_type_country_rel', string='Restrict Countries',
        help="Keep empty to allow visitors from any country, otherwise you only allow visitors from selected countries")
    question_ids = fields.One2many('calendar.appointment.question', 'appointment_type_id', string='Questions', copy=True)

    slot_ids = fields.One2many('calendar.appointment.slot', 'appointment_type_id', 'Availabilities', copy=True)
    appointment_tz = fields.Selection(
        _tz_get, string='Timezone', required=True, default=lambda self: self.env.user.tz,
        help="Timezone where appointment take place")
    employee_ids = fields.Many2many('hr.employee', 'appointment_type_employee_rel', domain=[('user_id', '!=', False)], string='Employees')
    assign_method = fields.Selection([
        ('random', 'Random'),
        ('chosen', 'Chosen by the Customer')], string='Assignment Method', default='random',
        help="How employees will be assigned to meetings customers book on your website.")
    appointment_count = fields.Integer('# Appointments', compute='_compute_appointment_count')

    def _compute_appointment_count(self):
        meeting_data = self.env['calendar.event'].read_group([('appointment_type_id', 'in', self.ids)], ['appointment_type_id'], ['appointment_type_id'])
        mapped_data = {m['appointment_type_id'][0]: m['appointment_type_id_count'] for m in meeting_data}
        for appointment_type in self:
            appointment_type.appointment_count = mapped_data.get(appointment_type.id, 0)

    @api.constrains('category', 'employee_ids')
    def _check_employee_configuration(self):
        for appointment_type in self:
            if appointment_type.category != 'website' and len(appointment_type.employee_ids) != 1:
                raise ValidationError(_("This category of appointment type should only have one employee but got %s employees", len(appointment_type.employee_ids)))
            if appointment_type.category == 'work_hours':
                appointment_domain = [('category', '=', 'work_hours'), ('employee_ids', 'in', appointment_type.employee_ids.ids)]
                if appointment_type.ids:
                    appointment_domain = AND([appointment_domain, [('id', 'not in', appointment_type.ids)]])
                if self.search_count(appointment_domain) > 0:
                    raise ValidationError(_("Only one work hours appointment type is allowed for a specific employee."))

    @api.model
    def create(self, values):
        """ We don't want the current user to be follower of all created types """
        return super(CalendarAppointmentType, self.with_context(mail_create_nosubscribe=True)).create(values)

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = default or {}
        default['name'] = self.name + _(' (copy)')
        return super(CalendarAppointmentType, self).copy(default=default)

    def action_calendar_meetings(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("calendar.action_calendar_event")
        appointments = self.env['calendar.event'].search([
            ('appointment_type_id', '=', self.id), ('start', '>=', datetime.today()
        )], order='start')
        nbr_appointments_week_later = self.env['calendar.event'].search_count([
            ('appointment_type_id', '=', self.id), ('start', '>=', datetime.today() + timedelta(weeks=1))
        ])

        action['context'] = {
            'default_appointment_type_id': self.id,
            'search_default_appointment_type_id': self.id,
            'default_mode': "month" if nbr_appointments_week_later else "week",
            'initial_date': appointments[0].start if appointments else datetime.today(),
        }
        return action

    def action_share(self):
        self.ensure_one()
        return {
            'name': _('Share Link'),
            'type': 'ir.actions.act_window',
            'res_model': 'calendar.appointment.share',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_appointment_type_ids': self.ids,
                'default_employee_ids': self.employee_ids.filtered(lambda employee: employee.user_id.id == self.env.user.id).ids,
            }
        }

    def action_customer_preview(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': url_join(self.get_base_url(), '/calendar/%s' % slug(self)),
            'target': 'self',
        }

    # --------------------------------------
    # Slots Generation
    # --------------------------------------

    def _slots_generate(self, first_day, last_day, timezone, reference_date=None):
        """ Generate all appointment slots (in naive UTC, appointment timezone, and given (visitors) timezone)
            between first_day and last_day (datetimes in appointment timezone)

            :return: [ {'slot': slot_record, <timezone>: (date_start, date_end), ...},
                      ... ]
        """
        if not reference_date:
            reference_date = datetime.utcnow()

        def append_slot(day, slot):
            local_start = appt_tz.localize(datetime.combine(day, time(hour=int(slot.start_hour), minute=int(round((slot.start_hour % 1) * 60)))))
            local_end = appt_tz.localize(
                datetime.combine(day, time(hour=int(slot.start_hour), minute=int(round((slot.start_hour % 1) * 60)))) + relativedelta(hours=self.appointment_duration))
            while (local_start.hour + local_start.minute / 60) <= slot.end_hour - self.appointment_duration:
                slots.append({
                    self.appointment_tz: (
                        local_start,
                        local_end,
                    ),
                    timezone: (
                        local_start.astimezone(requested_tz),
                        local_end.astimezone(requested_tz),
                    ),
                    'UTC': (
                        local_start.astimezone(pytz.UTC).replace(tzinfo=None),
                        local_end.astimezone(pytz.UTC).replace(tzinfo=None),
                    ),
                    'slot': slot,
                })
                local_start = local_end
                local_end += relativedelta(hours=self.appointment_duration)
        appt_tz = pytz.timezone(self.appointment_tz)
        requested_tz = pytz.timezone(timezone)

        slots = []
        # We use only the recurring slot if it's not a custom appointment type.
        if self.category != 'custom':
            # Regular recurring slots (not a custom appointment), generate necessary slots using configuration rules
            for slot in self.slot_ids.filtered(lambda x: int(x.weekday) == first_day.isoweekday()):
                if slot.end_hour > first_day.hour + first_day.minute / 60.0:
                    append_slot(first_day.date(), slot)
            slot_weekday = [int(weekday) - 1 for weekday in self.slot_ids.mapped('weekday')]
            for day in rrule.rrule(rrule.DAILY,
                                dtstart=first_day.date() + timedelta(days=1),
                                until=last_day.date(),
                                byweekday=slot_weekday):
                for slot in self.slot_ids.filtered(lambda x: int(x.weekday) == day.isoweekday()):
                    append_slot(day, slot)
        else:
            # Custom appointment type, we use "unique" slots here that have a defined start/end datetime
            unique_slots = self.slot_ids.filtered(lambda slot: slot.slot_type == 'unique' and slot.end_datetime > reference_date)

            for slot in unique_slots:
                start = slot.start_datetime.astimezone(tz=None)
                end = slot.end_datetime.astimezone(tz=None)
                startUTC = start.astimezone(pytz.UTC).replace(tzinfo=None)
                endUTC = end.astimezone(pytz.UTC).replace(tzinfo=None)
                slots.append({
                    self.appointment_tz: (
                        start.astimezone(appt_tz),
                        end.astimezone(appt_tz),
                    ),
                    timezone: (
                        start.astimezone(requested_tz),
                        end.astimezone(requested_tz),
                    ),
                    'UTC': (
                        startUTC,
                        endUTC,
                    ),
                    'slot': slot,
                })
        return slots

    def _slots_available(self, slots, start_dt, end_dt, employee=None):
        """ Fills the slot structure with an available employee

        :param list slots: slots (list of slot dict), as generated by ``_slots_generate``;
        :param datetime start_dt: beginning of appointment check boundary. Timezoned to UTC;
        :param datetime end_dt: end of appointment check boundary. Timezoned to UTC;
        :param <hr.employee> employee: if set, only consider this employee. Otherwise
          consider all employees assigned to this appointment type;

        :return: None but instead update ``slots`` adding ``employee_id`` key
          containing found available employee ID;
        """
        # With context will be used in resource.calendar to force the referential user
        # for work interval computing to the *user linked to the employee*
        available_employees = [emp.with_context(tz=emp.user_id.tz) for emp in (employee or self.employee_ids)]
        random.shuffle(available_employees)
        available_employees_tz = self.env['hr.employee'].concat(*available_employees)

        # fetch value used for availability in batch
        availability_values = self._slot_availability_prepare_values(
            available_employees_tz, start_dt, end_dt
        )

        for slot in slots:
            found_employee = next(
                (potential_employee for potential_employee in available_employees_tz
                 if self._slot_availability_is_employee_available(slot, potential_employee, availability_values)
                ), False
            )
            if found_employee:
                slot['employee_id'] = found_employee

    def _slot_availability_is_employee_available(self, slot, staff_employee, availability_values):
        """ This method verifies if the employee is available on the given slot.
        It checks whether the employee has calendar events clashing and if he
        is working during the slot based on working hours.

        Can be overridden to add custom checks.

        :param dict slot: a slot as generated by ``_slots_generate``;
        :param <hr.employee> staff_employee: employee to check against slot boundaries;
        :param dict availability_values: dict of data used for availability check.
          See ``_slot_availability_prepare_values()`` for more details;

        :return: boolean: is employee available for an appointment for given slot
        """
        is_available = True
        slot_start_dt_utc, slot_end_dt_utc = slot['UTC'][0], slot['UTC'][1]

        workhours = availability_values.get('work_schedules')
        if workhours and workhours.get(staff_employee.user_partner_id):
            is_available = self._slot_availability_is_employee_working(
                slot_start_dt_utc, slot_end_dt_utc,
                workhours[staff_employee.user_partner_id]
            )

        partner_to_events = availability_values.get('partner_to_events') or {}
        if is_available and partner_to_events.get(staff_employee.user_partner_id):
            for day_dt in rrule.rrule(freq=rrule.DAILY,
                                      dtstart=slot_start_dt_utc,
                                      until=slot_end_dt_utc,
                                      interval=1):
                day_events = partner_to_events[staff_employee.user_partner_id].get(day_dt.date()) or []
                if any(event.allday or (event.start < slot_end_dt_utc and event.stop > slot_start_dt_utc) for event in day_events):
                    is_available = False
                    break

        return is_available

    def _slot_availability_is_employee_working(self, start_dt, end_dt, intervals):
        """ Check if the slot is contained in the employee's work hours
        (defined by intervals).

        TDE NOTE: internal method ``is_work_available`` of ``_slots_available``
        made as explicit method in 15.0 but left untouched. To clean in 15.3+.

        :param datetime start_dt: beginning of slot boundary. Not timezoned UTC;
        :param datetime end_dt: end of slot boundary. Not timezoned UTC;
        :param intervals: list of tuples defining working hours boundaries. If no
          intervals are given we consider employee does not work during this slot.
          See ``Resource._work_intervals_batch`` for more details;

        :return bool: whether employee is available for this slot;
        """
        def find_start_index():
            """ find the highest index of intervals for which the start_date
            (element [0]) is before (or at) start_dt """
            def recursive_find_index(lower_bound, upper_bound):
                if upper_bound - lower_bound <= 1:
                    if intervals[upper_bound][0] <= start_dt:
                        return upper_bound
                    return lower_bound
                index = (upper_bound + lower_bound) // 2
                if intervals[index][0] <= start_dt:
                    return recursive_find_index(index, upper_bound)
                return recursive_find_index(lower_bound, index)

            if start_dt <= intervals[0][0] - tolerance:
                return -1
            if end_dt >= intervals[-1][1] + tolerance:
                return -1
            return recursive_find_index(0, len(intervals) - 1)

        if not intervals:
            return False

        tolerance = timedelta(minutes=1)
        start_index = find_start_index()
        if start_index != -1:
            for index in range(start_index, len(intervals)):
                if intervals[index][1] >= end_dt - tolerance:
                    return True
                if len(intervals) == index + 1 or intervals[index + 1][0] - intervals[index][1] > tolerance:
                    return False
        return False

    def _slot_availability_prepare_values(self, staff_employees, start_dt, end_dt):
        """ Hook method used to prepare useful values in the computation of slots
        availability. Purpose is to prepare values (event meeting, work schedule)
        in batch instead of doing it in a loop in ``_slots_available``.

        Can be overridden to add custom values preparation to be used in custom
        overrides of ``_slot_availability_is_employee_available()``.

        :param <hr.employee> staff_employees: prepare values to check availability
          of those employees against given appointment boundaries. At this point
          timezone should be correctly set in context of those employees;
        :param datetime start_dt: beginning of appointment check boundary. Timezoned to UTC;
        :param datetime end_dt: end of appointment check boundary. Timezoned to UTC;

        :return: dict containing main values for computation, formatted like
          {
            'partner_to_events': meetings (not declined), based on user_partner_id
              (see ``_slot_availability_prepare_values_meetings()``);
            'work_schedules': dict giving working hours based on user_partner_id
              (see ``_slot_availability_prepare_values_workhours()``);
          }
        }
        """
        result = self._slot_availability_prepare_values_workhours(staff_employees, start_dt, end_dt)
        result.update(self._slot_availability_prepare_values_meetings(staff_employees, start_dt, end_dt))
        return result

    def _slot_availability_prepare_values_meetings(self, staff_employees, start_dt, end_dt):
        """ This method computes meetings of employees between start_dt and end_dt
        of appointment check.

        :param <hr.employee> staff_employees: prepare values to check availability
          of those employees against given appointment boundaries. At this point
          timezone should be correctly set in context of those employees;
        :param datetime start_dt: beginning of appointment check boundary. Timezoned to UTC;
        :param datetime end_dt: end of appointment check boundary. Timezoned to UTC;

        :return: dict containing main values for computation, formatted like
          {
            'partner_to_events': meetings (not declined), formatted as a dict
              {
                'user_partner_id': dict of day-based meetings: {
                  'date in UTC': calendar events;
                  'date in UTC': calendar events;
                  ...
              },
              { ... }
          }
        """
        related_partners = staff_employees.user_partner_id

        # perform a search based on start / end being set to day min / day max
        # in order to include day-long events without having to include conditions
        # on start_date and allday
        all_events = self.env['calendar.event']
        if related_partners:
            all_events = self.env['calendar.event'].search(
                ['&',
                 ('partner_ids', 'in', related_partners.ids),
                 '&',
                 ('stop', '>', datetime.combine(start_dt, time.min)),
                 ('start', '<', datetime.combine(end_dt, time.max)),
                ],
                order='start asc',
            )

        partner_to_events = {}
        for event in all_events:
            for attendee in event.attendee_ids:
                if attendee.state == 'declined' or attendee.partner_id not in related_partners:
                    continue
                for day_dt in rrule.rrule(freq=rrule.DAILY,
                                          dtstart=event.start,
                                          until=event.stop,
                                          interval=1):
                    partner_events = partner_to_events.setdefault(attendee.partner_id, {})
                    date_date = day_dt.date()  # map per day, not per hour
                    if partner_events.get(date_date):
                        partner_events[date_date] += event
                    else:
                        partner_events[date_date] = event

        return {'partner_to_events': partner_to_events}

    def _slot_availability_prepare_values_workhours(self, staff_employees, start_dt, end_dt):
        """ This method computes the work intervals of employees between start_dt
        and end_dt of slot. This means they have an employee using working hours.

        :param <hr.employee> staff_employees: prepare values to check availability
          of those employees against given appointment boundaries. At this point
          timezone should be correctly set in context of those employees;
        :param datetime start_dt: beginning of appointment check boundary. Timezoned to UTC;
        :param datetime end_dt: end of appointment check boundary. Timezoned to UTC;

        :return: dict with unique key 'work_schedules' (to ease master compatibility)
          being a dict of working intervals based on employee partners:
          {
            'user_partner_id.id': [tuple(work interval), tuple(work_interval), ...],
            'user_partner_id.id': work_intervals,
            ...
          }
          Calendar field is required on resource and therefore on employee so each
          employee should be correctly taken into account;
        """
        if self.category == 'custom':
            return {'work_schedules': {}}

        calendar_to_employees = {}
        # compute work schedules for employees having a resource.calendar
        for staff_employee in staff_employees:
            calendar = staff_employee.resource_id.calendar_id
            if not calendar:
                continue
            if calendar not in calendar_to_employees:
                calendar_to_employees[calendar] = staff_employee
            else:
                calendar_to_employees[calendar] += staff_employee

        # Compute work schedules for users having employees
        work_schedules = {}
        for calendar, employees in calendar_to_employees.items():
            work_intervals = calendar.sudo()._work_intervals_batch(
                start_dt, end_dt,
                resources=employees.resource_id
            )
            work_schedules.update(dict(
                (employee.user_partner_id,
                 [(interval[0].astimezone(pytz.UTC).replace(tzinfo=None),
                   interval[1].astimezone(pytz.UTC).replace(tzinfo=None)
                  )
                  for interval in work_intervals[employee.resource_id.id]
                 ]
                )
                for employee in employees
            ))

        return {'work_schedules': work_schedules}

    def _get_appointment_slots(self, timezone, employee=None, reference_date=None):
        """ Fetch available slots to book an appointment.

        :param str timezone: timezone string e.g.: 'Europe/Brussels' or 'Etc/GMT+1'
        :param <hr.employee> employee: if set will only check available slots for
          this employee. Otherwise employee_ids fields is used to fetch availability;
        :param datetime reference_date: starting datetime to fetch slots. If not
          given now (in UTC) is used instead. Note that minimum schedule hours
          defined on appointment type is added to the beginning of slots;

        :returns: list of dicts (1 per month) containing available slots per week
          and per day for each week (see ``_slots_generate()``), like
          [
            {'id': 0,
             'month': 'February 2022' (formatted month name),
             'weeks': [
                [{'day': '']
                [{...}],
             ],
            },
            {'id': 1,
             'month': 'March 2022' (formatted month name),
             'weeks': [ (...) ],
            },
            {...}
          ]
        """
        self.ensure_one()
        if not reference_date:
            reference_date = datetime.utcnow()

        appt_tz = pytz.timezone(self.appointment_tz)
        requested_tz = pytz.timezone(timezone)
        first_day = requested_tz.fromutc(reference_date + relativedelta(hours=self.min_schedule_hours))
        appointment_duration_days = self.max_schedule_days
        unique_slots = self.slot_ids.filtered(lambda slot: slot.slot_type == 'unique')
        if self.category == 'custom' and unique_slots:
            appointment_duration_days = (unique_slots[-1].end_datetime.date() - reference_date.date()).days
        last_day = requested_tz.fromutc(reference_date + relativedelta(days=appointment_duration_days))

        # Compute available slots (ordered)
        slots = self._slots_generate(
            first_day.astimezone(appt_tz),
            last_day.astimezone(appt_tz),
            timezone,
            reference_date=reference_date
        )
        if not employee or employee in self.employee_ids:
            self._slots_available(slots, first_day.astimezone(pytz.UTC), last_day.astimezone(pytz.UTC), employee)

        # Compute calendar rendering and inject available slots
        today = requested_tz.fromutc(reference_date)
        start = today
        month_dates_calendar = cal.Calendar(0).monthdatescalendar
        months = []
        while (start.year, start.month) <= (last_day.year, last_day.month):
            dates = month_dates_calendar(start.year, start.month)
            for week_index, week in enumerate(dates):
                for day_index, day in enumerate(week):
                    mute_cls = weekend_cls = today_cls = None
                    today_slots = []
                    if day.weekday() in (cal.SUNDAY, cal.SATURDAY):
                        weekend_cls = 'o_weekend'
                    if day == today.date() and day.month == today.month:
                        today_cls = 'o_today'
                    if day.month != start.month:
                        mute_cls = 'text-muted o_mute_day'
                    else:
                        # slots are ordered, so check all unprocessed slots from until > day
                        while slots and (slots[0][timezone][0].date() <= day):
                            if (slots[0][timezone][0].date() == day) and ('employee_id' in slots[0]):
                                if slots[0]['slot'].allday:
                                    today_slots.append({
                                        'employee_id': slots[0]['employee_id'].id,
                                        'datetime': slots[0][timezone][0].strftime('%Y-%m-%d %H:%M:%S'),
                                        'hours': _("All day"),
                                        'duration': 24,
                                    })
                                else:
                                    start_hour = slots[0][timezone][0].strftime('%H:%M')
                                    end_hour = slots[0][timezone][1].strftime('%H:%M')
                                    today_slots.append({
                                        'employee_id': slots[0]['employee_id'].id,
                                        'datetime': slots[0][timezone][0].strftime('%Y-%m-%d %H:%M:%S'),
                                        'hours': "%s - %s" % (start_hour, end_hour) if self.category == 'custom' else start_hour,
                                        'duration': str((slots[0][timezone][1] - slots[0][timezone][0]).total_seconds() / 3600),
                                    })
                            slots.pop(0)
                    today_slots = sorted(today_slots, key=lambda d: d['hours'])
                    dates[week_index][day_index] = {
                        'day': day,
                        'slots': today_slots,
                        'mute_cls': mute_cls,
                        'weekend_cls': weekend_cls,
                        'today_cls': today_cls
                    }

            months.append({
                'id': len(months),
                'month': format_datetime(start, 'MMMM Y', locale=get_lang(self.env).code),
                'weeks': dates,
            })
            start = start + relativedelta(months=1)
        return months

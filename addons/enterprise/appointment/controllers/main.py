# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from babel.dates import format_datetime, format_date
from datetime import datetime
from dateutil.relativedelta import relativedelta
import json
import pytz

from werkzeug.exceptions import NotFound
from werkzeug.urls import url_encode

from odoo import http, _, fields
from odoo.http import request
from odoo.osv import expression
from odoo.tools import html2plaintext, is_html_empty, plaintext2html, DEFAULT_SERVER_DATETIME_FORMAT as dtf
from odoo.tools.misc import get_lang

from odoo.addons.base.models.ir_ui_view import keep_query
from odoo.addons.http_routing.models.ir_http import slug


class Appointment(http.Controller):

    #----------------------------------------------------------
    # Appointment HTTP Routes
    #----------------------------------------------------------

    @http.route([
        '/calendar',
        '/calendar/page/<int:page>',
    ], type='http', auth="public", website=True, sitemap=True)
    def calendar_appointments(self, page=1, **kwargs):
        """
        Display the appointments to choose (the display depends of a custom option called 'Card Design')

        :param page: the page number displayed when the appointments are organized by cards

        A param filter_appointment_type_ids can be passed to display a define selection of appointments types.
        This param is propagated through templates to allow people to go back with the initial appointment
        types filter selection
        """
        return request.render('appointment.appointments_list_layout', self._prepare_appointments_list_data(**kwargs))

    @http.route([
        '/calendar/<model("calendar.appointment.type"):appointment_type>',
    ], type='http', auth="public", website=True, sitemap=True)
    def calendar_appointment_type(self, appointment_type, filter_employee_ids=None, timezone=None, state=False, **kwargs):
        """
        Render the appointment information alongside the calendar for the slot selection

        :param appointment_type: the appointment type we are currently on
        :param filter_employee_ids: the employees that will be displayed for the appointment registration, if not given
            all employees set for the appointment type are used
        :param timezone: the timezone used to display the available slots
        :param state: the type of message that will be displayed in case of an error/info. Possible values:
            - cancel: Info message to confirm that an appointment has been canceled
            - failed-employee: Error message displayed when the slot has been taken while doing the registration
            - failed-partner: Info message displayed when the partner has already an event in the time slot selected
        """
        appointment_type = appointment_type.sudo()
        request.session['timezone'] = timezone or appointment_type.appointment_tz
        try:
            filter_employee_ids = json.loads(filter_employee_ids) if filter_employee_ids else []
        except json.decoder.JSONDecodeError:
            raise ValueError()

        if appointment_type.assign_method == 'chosen' and not filter_employee_ids:
            suggested_employees = appointment_type.employee_ids
        else:
            suggested_employees = appointment_type.employee_ids.filtered(lambda emp: emp.id in filter_employee_ids)

        # Keep retrocompatibility with the the old personnal link ?employee_id=
        employee_id = kwargs.get('employee_id')
        if not suggested_employees and employee_id and int(employee_id) in appointment_type.employee_ids.ids:
            suggested_employees = request.env['hr.employee'].sudo().browse(int(employee_id))

        default_employee = suggested_employees[0] if suggested_employees else request.env['hr.employee']
        slots = appointment_type._get_appointment_slots(request.session['timezone'], default_employee)
        formated_days = [format_date(fields.Date.from_string('2021-03-0%s' % str(day + 1)), "EEE", get_lang(request.env).code) for day in range(7)]

        return request.render("appointment.appointment_info", {
            'appointment_type': appointment_type,
            'suggested_employees': suggested_employees,
            'main_object': appointment_type,
            'timezone': request.session['timezone'],
            'slots': slots,
            'state': state,
            'filter_appointment_type_ids': kwargs.get('filter_appointment_type_ids'),
            'formated_days': formated_days,
        })

    @http.route([
        '/calendar/<model("calendar.appointment.type"):appointment_type>/appointment',
    ], type='http', auth='public', website=True, sitemap=True)
    def calendar_appointment(self, appointment_type, filter_employee_ids=None, timezone=None, failed=False, **kwargs):
        return request.redirect('/calendar/%s?%s' % (slug(appointment_type), keep_query('*')))

    @http.route(['/calendar/<model("calendar.appointment.type"):appointment_type>/info'], type='http', auth="public", website=True, sitemap=True)
    def calendar_appointment_form(self, appointment_type, employee_id, date_time, duration, **kwargs):
        """
        Render the form to get information about the user for the appointment

        :param appointment_type: the appointment type related
        :param employee_id: the employee selected for the appointment
        :param date_time: the slot datetime selected for the appointment
        :param fitler_appointment_type_ids: see ``Appointment.calendar_appointments()`` route
        """
        partner = self._get_customer_partner()
        partner_data = partner.read(fields=['name', 'mobile', 'email'])[0] if partner else {}
        day_name = format_datetime(datetime.strptime(date_time, dtf), 'EEE', locale=get_lang(request.env).code)
        date_formated = format_datetime(datetime.strptime(date_time, dtf), locale=get_lang(request.env).code)
        return request.render("appointment.appointment_form", {
            'partner_data': partner_data,
            'appointment_type': appointment_type,
            'main_object': appointment_type,
            'datetime': date_time,
            'datetime_locale': day_name + ' ' + date_formated,
            'datetime_str': date_time,
            'duration_str': duration,
            'employee_id': employee_id,
        })

    @http.route(['/calendar/<model("calendar.appointment.type"):appointment_type>/submit'], type='http', auth="public", website=True, methods=["POST"])
    def calendar_appointment_submit(self, appointment_type, datetime_str, duration_str, employee_id, name, phone, email, **kwargs):
        """
        Create the event for the appointment and redirect on the validation page with a summary of the appointment.

        :param appointment_type: the appointment type related
        :param datetime_str: the string representing the datetime
        :param employee_id: the employee selected for the appointment
        :param name: the name of the user sets in the form
        :param phone: the phone of the user sets in the form
        :param email: the email of the user sets in the form
        """
        timezone = request.session['timezone'] or appointment_type.appointment_tz
        tz_session = pytz.timezone(timezone)
        date_start = tz_session.localize(fields.Datetime.from_string(datetime_str)).astimezone(pytz.utc)
        duration = float(duration_str)
        date_end = date_start + relativedelta(hours=duration)

        # check availability of the employee again (in case someone else booked while the client was entering the form)
        employee = request.env['hr.employee'].sudo().browse(int(employee_id)).exists()
        if employee not in appointment_type.sudo().employee_ids:
            raise NotFound()
        if employee.user_id and employee.user_id.partner_id:
            if not employee.user_id.partner_id.calendar_verify_availability(date_start, date_end):
                return request.redirect('/calendar/%s/appointment?state=failed-employee' % slug(appointment_type))

        Partner = self._get_customer_partner() or request.env['res.partner'].sudo().search([('email', '=like', email)], limit=1)
        if Partner:
            if not Partner.calendar_verify_availability(date_start, date_end):
                return request.redirect('/calendar/%s/appointment?state=failed-partner' % appointment_type.id)
            if not Partner.mobile:
                Partner.write({'mobile': phone})
            if not Partner.email:
                Partner.write({'email': email})
        else:
            Partner = Partner.create({
                'name': name,
                'mobile': Partner._phone_format(phone, country=self._get_customer_country()),
                'email': email,
            })

        description_bits = []
        description = ''

        if phone:
            description_bits.append(_('Mobile: %s', phone))
        if email:
            description_bits.append(_('Email: %s', email))

        for question in appointment_type.question_ids:
            key = 'question_' + str(question.id)
            if question.question_type == 'checkbox':
                answers = question.answer_ids.filtered(lambda x: (key + '_answer_' + str(x.id)) in kwargs)
                if answers:
                    description_bits.append('%s: %s' % (question.name, ', '.join(answers.mapped('name'))))
            elif question.question_type == 'text' and kwargs.get(key):
                answers = [line for line in kwargs[key].split('\n') if line.strip()]
                description_bits.append('%s:<br/>%s' % (question.name, plaintext2html(kwargs.get(key).strip())))
            elif kwargs.get(key):
                description_bits.append('%s: %s' % (question.name, kwargs.get(key).strip()))
        if description_bits:
            description = '<ul>' + ''.join(['<li>%s</li>' % bit for bit in description_bits]) + '</ul>'

        # FIXME AWA/TDE double check this and/or write some tests to ensure behavior
        # The 'mail_notify_author' is only placed here and not in 'calendar.attendee#_send_mail_to_attendees'
        # Because we only want to notify the author in the context of Online Appointments
        # When creating a meeting from your own calendar in the backend, there is no need to notify yourself
        event = request.env['calendar.event'].with_context(
            mail_notify_author=True,
            allowed_company_ids=employee.user_id.company_ids.ids,
        ).sudo().create(
                self._prepare_calendar_values(appointment_type, date_start, date_end, duration, description, name, employee, Partner)
            )
        event.attendee_ids.write({'state': 'accepted'})
        return request.redirect('/calendar/view/%s?partner_id=%s&%s' % (event.access_token, Partner.id, keep_query('*', state='new')))
     
    def _prepare_calendar_values(self, appointment_type, date_start, date_end, duration, description, name, employee, partner):
        """
        prepares all values needed to create a new calendar.event
        """
        categ_id = request.env.ref('appointment.calendar_event_type_data_online_appointment')
        alarm_ids = appointment_type.reminder_ids and [(6, 0, appointment_type.reminder_ids.ids)] or []
        partner_ids = list(set([employee.user_id.partner_id.id] + [partner.id]))
        return {
            'name': _('%s with %s', appointment_type.name, name),
            'start': date_start.strftime(dtf),
            # FIXME master
            # we override here start_date(time) value because they are not properly
            # recomputed due to ugly overrides in event.calendar (reccurrencies suck!)
            #     (fixing them in stable is a pita as it requires a good rewrite of the
            #      calendar engine)
            'start_date': date_start.strftime(dtf),
            'stop': date_end.strftime(dtf),
            'allday': False,
            'duration': duration,
            'description': description,
            'alarm_ids': alarm_ids,
            'location': appointment_type.location,
            'partner_ids': [(4, pid, False) for pid in partner_ids],
            'categ_ids': [(4, categ_id.id, False)],
            'appointment_type_id': appointment_type.id,
            'user_id': employee.user_id.id,
        }        

    @http.route(['/calendar/view/<string:access_token>'], type='http', auth="public", website=True)
    def calendar_appointment_view(self, access_token, partner_id, state=False, **kwargs):
        """
        Render the validation of an appointment and display a summary of it

        :param access_token: the access_token of the event linked to the appointment
        :param state: allow to display an info message, possible values:
            - new: Info message displayed when the appointment has been correctly created
            - no-cancel: Info message displayed when an appointment can no longer be canceled
        """
        event = request.env['calendar.event'].sudo().search([('access_token', '=', access_token)], limit=1)
        if not event:
            return request.not_found()
        timezone = request.session.get('timezone')
        if not timezone:
            timezone = request.env.context.get('tz') or event.appointment_type_id.appointment_tz or event.partner_ids and event.partner_ids[0].tz or event.user_id.tz or 'UTC'
            request.session['timezone'] = timezone
        tz_session = pytz.timezone(timezone)

        date_start_suffix = ""
        format_func = format_datetime
        if not event.allday:
            url_date_start = fields.Datetime.from_string(event.start).strftime('%Y%m%dT%H%M%SZ')
            url_date_stop = fields.Datetime.from_string(event.stop).strftime('%Y%m%dT%H%M%SZ')
            date_start = fields.Datetime.from_string(event.start).replace(tzinfo=pytz.utc).astimezone(tz_session)
        else:
            url_date_start = url_date_stop = fields.Date.from_string(event.start_date).strftime('%Y%m%d')
            date_start = fields.Date.from_string(event.start_date)
            format_func = format_date
            date_start_suffix = _(', All Day')

        locale = get_lang(request.env).code
        day_name = format_func(date_start, 'EEE', locale=locale)
        date_start = day_name + ' ' + format_func(date_start, locale=locale) + date_start_suffix
        # convert_online_event_desc_to_text method for correct data formatting in external calendars
        details = event.appointment_type_id and event.appointment_type_id.message_confirmation or event.convert_online_event_desc_to_text(event.description) or ''
        params = {
            'action': 'TEMPLATE',
            'text': event.name,
            'dates': url_date_start + '/' + url_date_stop,
            'details': html2plaintext(details.encode('utf-8'))
        }
        if event.location:
            params.update(location=event.location.replace('\n', ' '))
        encoded_params = url_encode(params)
        google_url = 'https://www.google.com/calendar/render?' + encoded_params

        return request.render("appointment.appointment_validated", {
            'event': event,
            'datetime_start': date_start,
            'google_url': google_url,
            'state': state,
            'partner_id': partner_id,
            'is_html_empty': is_html_empty,
        })

    @http.route([
        '/calendar/cancel/<string:access_token>',
        '/calendar/<string:access_token>/cancel'
    ], type='http', auth="public", website=True)
    def calendar_appointment_cancel(self, access_token, partner_id, **kwargs):
        """
            Route to cancel an appointment event, this route is linked to a button in the validation page
        """
        event = request.env['calendar.event'].sudo().search([('access_token', '=', access_token)], limit=1)
        appointment_type = event.appointment_type_id
        if not event:
            return request.not_found()
        if fields.Datetime.from_string(event.allday and event.start_date or event.start) < datetime.now() + relativedelta(hours=event.appointment_type_id.min_cancellation_hours):
            return request.redirect('/calendar/view/' + access_token + '?state=no-cancel&partner_id=%s' % partner_id)
        event.sudo().action_cancel_meeting([int(partner_id)])
        return request.redirect('/calendar/%s/appointment?state=cancel' % slug(appointment_type))

    @http.route(['/calendar/ics/<string:access_token>.ics'], type='http', auth="public", website=True)
    def calendar_appointment_ics(self, access_token, **kwargs):
        """
            Route to add the appointment event in a iCal/Outlook calendar
        """
        event = request.env['calendar.event'].sudo().search([('access_token', '=', access_token)], limit=1)
        if not event or not event.attendee_ids:
            return request.not_found()
        files = event._get_ics_file()
        content = files[event.id]
        return request.make_response(content, [
            ('Content-Type', 'application/octet-stream'),
            ('Content-Length', len(content)),
            ('Content-Disposition', 'attachment; filename=Appoinment.ics')
        ])

    #----------------------------------------------------------
    # Appointment JSON Routes
    #----------------------------------------------------------

    @http.route(['/calendar/<int:appointment_type_id>/get_message_intro'], type="json", auth="public", methods=['POST'], website=True)
    def get_appointment_message_intro(self, appointment_type_id, **kwargs):
        appointment_type = request.env['calendar.appointment.type'].browse(int(appointment_type_id)).exists()
        if not appointment_type:
            raise NotFound()

        return appointment_type.message_intro or ''

    @http.route(['/calendar/<int:appointment_type_id>/update_available_slots'], type="json", auth="public", website=True)
    def calendar_appointment_update_available_slots(self, appointment_type_id, employee_id=None, timezone=None, **kwargs):
        """
            Route called when the employee or the timezone is modified to adapt the possible slots accordingly
        """
        appointment_type = request.env['calendar.appointment.type'].browse(int(appointment_type_id))

        request.session['timezone'] = timezone or appointment_type.appointment_tz
        employee = request.env['hr.employee'].sudo().browse(int(employee_id)) if employee_id else None
        slots = appointment_type.sudo()._get_appointment_slots(request.session['timezone'], employee)

        return request.env.ref('appointment.appointment_calendar')._render({
            'appointment_type': appointment_type,
            'slots': slots,
        })

    #----------------------------------------------------------
    # Utility Methods
    #----------------------------------------------------------

    def _appointments_base_domain(self, filter_appointment_type_ids):
        domain = [('category', '=', 'website')]

        if filter_appointment_type_ids:
            domain = expression.AND([domain, [('id', 'in', json.loads(filter_appointment_type_ids))]])
        else:
            country = self._get_customer_country()
            if country:
                country_domain = ['|', ('country_ids', '=', False), ('country_ids', 'in', [country.id])]
                domain = expression.AND([domain, country_domain])

        return domain

    def _prepare_appointments_list_data(self, **kwargs):
        """
            Compute specific data for the list layout.
        """
        domain = self._appointments_base_domain(kwargs.get('filter_appointment_type_ids'))

        appointment_types = request.env['calendar.appointment.type'].search(domain)
        return {
            'appointment_types': appointment_types,
        }

    def _get_customer_partner(self):
        partner = request.env['res.partner']
        if not request.env.user._is_public():
            partner = request.env.user.partner_id
        return partner

    def _get_customer_country(self):
        """
            Find the country from the geoip lib or fallback on the user or the visitor
        """
        country_code = request.session.geoip and request.session.geoip.get('country_code')
        country = request.env['res.country']
        if country_code:
            country = country.search([('code', '=', country_code)])
        if not country:
            country = request.env.user.country_id if not request.env.user._is_public() else country
        return country

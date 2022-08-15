# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid
from odoo import api, fields, models


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    def _default_access_token(self):
        return str(uuid.uuid4())

    access_token = fields.Char('Access Token', default=_default_access_token, readonly=True)
    appointment_type_id = fields.Many2one('calendar.appointment.type', 'Online Appointment', readonly=True, tracking=True)

    def _get_public_fields(self):
        return super()._get_public_fields() | {'appointment_type_id'}

    def _compute_is_highlighted(self):
        super(CalendarEvent, self)._compute_is_highlighted()
        if self.env.context.get('active_model') == 'calendar.appointment.type':
            appointment_type_id = self.env.context.get('active_id')
            for event in self:
                if event.appointment_type_id.id == appointment_type_id:
                    event.is_highlighted = True

    def _init_column(self, column_name):
        """ Initialize the value of the given column for existing rows.
            Overridden here because we skip generating unique access tokens
            for potentially tons of existing event, should they be needed,
            they will be generated on the fly.
        """
        if column_name != 'access_token':
            super(CalendarEvent, self)._init_column(column_name)

    def _generate_access_token(self):
        for event in self:
            event.access_token = self._default_access_token()

    def action_cancel_meeting(self, partner_ids):
        """ In case there are more than two attendees (responsible + another attendee),
            we do not want to archive the calendar.event.
            We'll just remove the attendee that made the cancellation request
        """
        self.ensure_one()
        attendees = self.env['calendar.attendee'].search([('event_id', '=', self.id), ('partner_id', 'in', partner_ids)])
        if attendees:
            if len(self.attendee_ids - attendees) >= 2:
                self.partner_ids -= attendees.partner_id
            else:
                self.action_archive()

    def _get_mail_tz(self):
        self.ensure_one()
        if not self.event_tz and self.appointment_type_id.appointment_tz:
            return self.appointment_type_id.appointment_tz
        return super()._get_mail_tz()

    def _track_template(self, changes):
        res = super(CalendarEvent, self)._track_template(changes)
        if 'appointment_type_id' in changes:
            booked_template = self.env.ref('appointment.appointment_booked_mail_template').sudo()
            res['appointment_type_id'] = (booked_template, {
                'auto_delete_message': True,
                'subtype_id': self.env['ir.model.data']._xmlid_to_res_id('appointment.mt_calendar_event_booked'),
                'email_layout_xmlid': 'mail.mail_notification_light'
            })
        if 'active' in changes and not self.active and self.appointment_type_id and self.start > fields.Datetime.now():
            canceled_template = self.env.ref('appointment.appointment_canceled_mail_template').sudo()
            res['active'] = (canceled_template, {
                'auto_delete_message': True,
                'subtype_id': self.env['ir.model.data']._xmlid_to_res_id('appointment.mt_calendar_event_canceled'),
                'email_layout_xmlid': 'mail.mail_notification_light'
            })
        return res

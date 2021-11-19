# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CalendarAppointmentSlot(models.Model):
    _name = "calendar.appointment.slot"
    _description = "Online Appointment : Time Slot"
    _rec_name = "weekday"
    _order = "weekday, start_hour, start_datetime, end_datetime"

    appointment_type_id = fields.Many2one('calendar.appointment.type', 'Appointment Type', ondelete='cascade')
    slot_type = fields.Selection([('recurring', 'Recurring'), ('unique', 'One Shot')],
        string='Slot type', default='recurring', required=True, compute="_compute_slot_type", store=True,
        help="""Defines the type of slot. The recurring slot is the default type which is used for
        appointment type that are used recurringly in type like medical appointment.
        The one shot type is only used when an user create a custom appointment type for a client by
        defining non-recurring time slot (e.g. 10th of April 2021 from 10 to 11 am) from its calendar.""")
    allday = fields.Boolean('All day',
        help="Determine if the slot englobe the whole day, mainly used for unique slot type")
    # Recurring slot
    weekday = fields.Selection([
        ('1', 'Monday'),
        ('2', 'Tuesday'),
        ('3', 'Wednesday'),
        ('4', 'Thursday'),
        ('5', 'Friday'),
        ('6', 'Saturday'),
        ('7', 'Sunday'),
    ], string='Week Day', required=True, default='1')
    start_hour = fields.Float('Starting Hour', required=True, default=8.0)
    end_hour = fields.Float('Ending Hour', required=True, default=17.0)
    # Real time slot
    start_datetime = fields.Datetime('From', help="Start datetime for unique slot type management")
    end_datetime = fields.Datetime('To', help="End datetime for unique slot type management")
    duration = fields.Float('Duration', compute='_compute_duration')

    @api.depends('start_datetime', 'end_datetime')
    def _compute_duration(self):
        for slot in self:
            if slot.start_datetime and slot.end_datetime:
                duration = (slot.end_datetime - slot.start_datetime).total_seconds() / 3600
                slot.duration = round(duration, 2)
            else:
                slot.duration = 0

    @api.depends('appointment_type_id')
    def _compute_slot_type(self):
        for slot in self:
            slot.slot_type = 'unique' if slot.appointment_type_id.category == 'custom' else 'recurring'

    @api.constrains('start_hour')
    def _check_hour(self):
        if any(slot.start_hour < 0.00 or slot.start_hour >= 24.00 for slot in self):
            raise ValidationError(_("Please enter a valid hour between 0:00 and 24:00 for your slots."))

    @api.constrains('start_hour', 'end_hour')
    def _check_delta_hours(self):
        if any(self.filtered(lambda slot: slot.start_hour >= slot.end_hour and slot.slot_type != 'unique')):
            raise ValidationError(_(
                "Atleast one slot duration from start to end is invalid: a slot should end after start"
            ))
        if any(self.filtered(lambda slot: slot.start_hour + slot.appointment_type_id.appointment_duration > slot.end_hour and slot.slot_type != 'unique')):
            raise ValidationError(_(
                "Atleast one slot duration is not enough to create a slot with the duration set in the appointment type"
            ))

    @api.constrains('slot_type', 'start_datetime', 'end_datetime')
    def _check_unique_slot_has_datetime(self):
        if any(self.filtered(lambda slot: slot.slot_type == "unique" and not (slot.start_datetime and slot.end_datetime))):
            raise ValidationError(_("An unique type slot should have a start and end datetime"))

    def name_get(self):
        result = []
        weekdays = dict(self._fields['weekday'].selection)
        for slot in self:
            if slot.slot_type == 'recurring':
                result.append((
                    slot.id,
                    "%s, %02d:%02d - %02d:%02d" % (weekdays.get(slot.weekday), int(slot.start_hour), int(round((slot.start_hour % 1) * 60)), int(slot.end_hour), int(round((slot.end_hour % 1) * 60)))
                ))
            else:
                result.append((slot.id, "%s - %s" % (slot.start_datetime, slot.end_datetime)))
        return result

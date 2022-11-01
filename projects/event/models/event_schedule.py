# -*- coding: utf-8 -*-
# Part of Tienlt. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class EventSchedule(models.Model):
    _name = 'event.schedule'

    name = fields.Char(string='Job name', required=True)
    time_schedule = fields.Date(string='Time Schedule', required=True)
    detail = fields.Text(string='Detail Schedule')
    room_id = fields.Many2one('event.meeting.room', string='Room')
    speaker_id = fields.Many2one('res.partner', string='Speaker')
    hour_start = fields.Float(string='Hour Start')
    hour_end = fields.Float(string='Hour End')
    total_hour = fields.Float(
        string='Total Hour',
        compute='_compute_total_hour'
    )
    event_id = fields.Many2one(comodel_name='event.event', string='Event')

    @api.depends('hour_start', 'hour_end')
    def _compute_total_hour(self):
        for schedule in self:
            hour = 0
            if schedule.hour_start and schedule.hour_end:
                hour = schedule.hour_end - schedule.hour_start
            schedule.total_hour = hour

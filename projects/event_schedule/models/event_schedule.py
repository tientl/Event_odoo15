# -*- coding: utf-8 -*-
# Part of Tienlt. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from odoo import api, models, fields


class EventSchedule(models.Model):
    _name = 'event.schedule'
    _description = 'Schedule of event'
    _order = 'time_schedule ASC'

    name = fields.Char(string='Job name', required=True)
    time_schedule = fields.Date(string='Time Schedule', required=True)
    detail = fields.Text(string='Detail Schedule')
    event_id = fields.Many2one(comodel_name='event.event', string='Event')
    schedule_detail_ids = fields.One2many(
        'event.schedule.detail',
        'event_schedule_id',
        string='Schedule Detail'
    )
    day = fields.Char(string='Day', compute='_compute_time')
    month = fields.Char(string='Month', compute='_compute_time')
    year = fields.Char(string='Year', compute='_compute_time')
    count_schedule_detail = fields.Integer(
        string='Count Schedule',
        compute='_compute_count_schedule_detail')
    event_rating_ids = fields.One2many(
        comodel_name='event.rating',
        inverse_name='schedule_id',
        string='Event Rating')

    @api.depends('schedule_detail_ids')
    def _compute_count_schedule_detail(self):
        for schedule in self:
            schedule.count_schedule_detail = len(schedule.schedule_detail_ids)

    @api.depends('hour_start', 'hour_end')
    def _compute_total_hour(self):
        for schedule in self:
            hour = 0
            if schedule.hour_start and schedule.hour_end:
                hour = schedule.hour_end - schedule.hour_start
            schedule.total_hour = hour

    @api.depends('time_schedule')
    def _compute_time(self):
        for date in self:
            time_schedule = date.time_schedule
            if time_schedule:
                date.day = time_schedule.strftime('%d') or False
                date.month = 'T' + time_schedule.strftime('%m') or False
                date.year = time_schedule.strftime('%Y') or False

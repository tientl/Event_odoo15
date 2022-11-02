# -*- coding: utf-8 -*-
# Part of Tienlt. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo import api, models, fields


class EventScheduleDetail(models.Model):
    _name = 'event.schedule.detail'
    _description = 'Detail Schedule of event'

    name = fields.Char(string='Job name', required=True)
    sequence = fields.Integer(string='Sequence')
    detail = fields.Text(string='Detail Schedule')
    room_id = fields.Many2one('event.meeting.room', string='Room')
    speaker_id = fields.Many2one(
        related='event_track_id.partner_id', string='Speaker')
    hour_start = fields.Float(string='Hour Start')
    hour_end = fields.Float(string='Hour End')
    total_hour = fields.Float(
        string='Total Hour',
        compute='_compute_total_hour'
    )
    event_schedule_id = fields.Many2one(
        comodel_name='event.schedule', string='Event Schedule')
    event_track_id = fields.Many2one(
        comodel_name='event.track', string='Event Track')

    @api.depends('hour_start', 'hour_end')
    def _compute_total_hour(self):
        for schedule in self:
            hour = 0
            if schedule.hour_start and schedule.hour_end:
                hour = schedule.hour_end - schedule.hour_start
            schedule.total_hour = hour

    @api.onchange('hour_start', 'hour_end')
    def _check_hour(self):
        for schedule in self:
            if schedule.hour_start > schedule.hour_end:
                raise UserError(
                    f'{schedule.name} Giờ bắt đầu đang lớn hơn giờ kết thúc Event!!')
            if 0 > schedule.hour_start >= 24 and 0 > schedule.hour_end >= 24:
                raise UserError(f'{schedule.name}: Vui lòng nhập lại giờ!!')

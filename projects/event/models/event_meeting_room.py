# -*- coding: utf-8 -*-
# Part of TienLT. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class EventMeetingRoom(models.Model):
    _name = 'event.meeting.room'
    _description = 'Event Room'

    name = fields.Char(string='Phòng')
    event_id = fields.Many2one(comodel_name='event.event', string='Sự kiện')
    location = fields.Char(string='Địa chỉ phòng')
    capacity = fields.Integer(string='Sức chức')

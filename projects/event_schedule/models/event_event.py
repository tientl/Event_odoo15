# -*- coding: utf-8 -*-
# Part of Tienlt. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class EventEvent(models.Model):
    _inherit = 'event.event'

    event_schedule_ids = fields.One2many(
        'event.schedule',
        'event_id',
        string='Event Schedule'
    )
    count_schedule = fields.Integer(
        string='Count Schedule',
        compute='_compute_event_schedule')

    @api.depends('event_schedule_ids')
    def _compute_event_schedule(self):
        for event in self:
            event.count_schedule = len(event.event_schedule_ids)

# -*- coding: utf-8 -*-
# Part of TienLT. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class EventRating(models.Model):
    _inherit = 'event.rating'

    schedule_detail_id = fields.Many2one(
        'event.schedule.detail', 'Lịch trình')
    schedule_id = fields.Many2one(
        related="schedule_detail_id.event_schedule_id")


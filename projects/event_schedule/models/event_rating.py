# -*- coding: utf-8 -*-
# Part of TienLT. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class EventRating(models.Model):
    _inherit = 'event.rating'

    schedule_id = fields.Many2one('event.schedule')
    schedule_detail_id = fields.Many2one(
        'event.schedule.detail', 'Lịch trình')

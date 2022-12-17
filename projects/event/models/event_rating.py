# -*- coding: utf-8 -*-
# Part of TienLT. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class EventRating(models.Model):
    _name = 'event.rating'
    _description = 'Event rating for registration'

    event_id = fields.Many2one(comodel_name='event.event')
    sub_schedule_id = fields.Many2one(comodel_name='event.schedule.detail')
    partner_id = fields.Many2one('res.partner', string='Registration')

    rating = fields.Integer(string='Rating')
    evaluate = fields.Text(string='Evaluate')
    is_event = fields.Boolean(string='Is Event')
    is_schedule = fields.Boolean(string='Is Schedule')

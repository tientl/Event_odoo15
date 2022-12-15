# -*- coding: utf-8 -*-
# Part of TienLT. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class EventRating(models.Model):
    _name = 'event.rating'
    _description = 'Event rating for registration'

    rating = fields.Integer(string='Rating')
    event_id = fields.Many2one(comodel_name='event.event')
    evaluate = fields.Text(string='Evaluate')
    is_event = fields.Boolean(string='Is Event')
    is_schedule = fields.Boolean(string='Is Schedule')
    partner_id = fields.Many2one('res.partner', string='Registration')

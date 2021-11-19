# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import math

from datetime import datetime, timedelta, time, date
from odoo import api, fields, models, _
from odoo.tools import format_time
from odoo.addons.resource.models.resource import float_to_time


class PlanningTemplate(models.Model):
    _name = 'planning.slot.template'
    _description = "Shift Template"
    _order = "sequence"

    active = fields.Boolean('Active', default=True)
    name = fields.Char('Hours', compute="_compute_name")
    sequence = fields.Integer('Sequence', index=True)
    role_id = fields.Many2one('planning.role', string="Role")
    start_time = fields.Float('Start Hour', default=0, group_operator=None)
    duration = fields.Float('Duration (Hours)', default=0, group_operator=None)

    _sql_constraints = [
        ('check_start_time_lower_than_24', 'CHECK(start_time <= 24)', 'You cannot have a start hour greater than 24'),
        ('check_start_time_positive', 'CHECK(start_time >= 0)', 'Start hour must be a positive number'),
        ('check_duration_positive', 'CHECK(duration >= 0)', 'You cannot have a negative duration')
    ]

    @api.depends('start_time', 'duration')
    def _compute_name(self):
        for shift_template in self:
            start_time = time(hour=int(shift_template.start_time), minute=round(math.modf(shift_template.start_time)[0] / (1 / 60.0)))
            duration = timedelta(hours=int(shift_template.duration), minutes=round(math.modf(shift_template.duration)[0] / (1 / 60.0)))
            end_time = datetime.combine(date.today(), start_time) + duration
            shift_template.name = '%s - %s %s' % (
                format_time(shift_template.env, start_time, time_format='short').replace(':00 ', ' '),
                format_time(shift_template.env, end_time.time(), time_format='short').replace(':00 ', ' '),
                _('(%s days span)') % (duration.days + 1) if duration.days > 0 else ''
            )

    def name_get(self):
        result = []
        for shift_template in self:
            name = '%s %s' % (
                shift_template.name,
                shift_template.role_id.name if shift_template.role_id.name is not False else ''
            )
            result.append([shift_template.id, name])
        return result

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = []
        for data in super(PlanningTemplate, self).read_group(domain, fields, groupby, offset, limit, orderby, lazy):
            if 'start_time' in data:
                data['start_time'] = float_to_time(data['start_time']).strftime('%H:%M')
            res.append(data)

        return res

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class CalendarAppointmentType(models.Model):
    _inherit = "calendar.appointment.type"

    lead_create = fields.Boolean(string="Create Opportunities",
        help="For each scheduled appointment, create a new opportunity and assign it to the responsible employee.")

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HelpdeskTicketReport(models.Model):
    _inherit = 'helpdesk.ticket.report.analysis'

    total_hours_spent = fields.Float("Hours Spent", group_operator="avg", readonly=True)

    def _select(self):
        select_str = super()._select()
        select_str += ", NULLIF(T.total_hours_spent, 0) as total_hours_spent"
        return select_str

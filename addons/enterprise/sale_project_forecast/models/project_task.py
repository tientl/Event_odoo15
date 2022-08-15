# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.osv import expression

class Task(models.Model):
    _inherit = 'project.task'

    # -------------------------------------------
    # Utils method
    # -------------------------------------------

    @api.model
    def _get_domain_compute_forecast_hours(self):
        return expression.AND([
            super()._get_domain_compute_forecast_hours(),
            [('start_datetime', '!=', False)]
        ])

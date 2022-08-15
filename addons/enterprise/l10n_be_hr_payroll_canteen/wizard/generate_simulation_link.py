# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class GenerateSimulationLink(models.TransientModel):
    _inherit = 'generate.simulation.link'

    l10n_be_canteen_cost = fields.Float(string="Canteen Cost")

    def _get_url_triggers(self):
        res = super()._get_url_triggers()
        return res + ['l10n_be_canteen_cost']

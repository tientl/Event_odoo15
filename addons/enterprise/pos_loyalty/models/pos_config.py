# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _default_loyalty_program(self):
        return self.env['loyalty.program'].search([], limit=1)

    module_pos_loyalty = fields.Boolean(default=True)
    loyalty_id = fields.Many2one('loyalty.program', string='Pos Loyalty Program', help='The loyalty program used by this point of sale.', default=_default_loyalty_program)

    @api.onchange('module_pos_loyalty')
    def _onchange_module_pos_loyalty(self):
        if self.module_pos_loyalty:
            self.loyalty_id = self._default_loyalty_program()
        else:
            self.loyalty_id = False

    @api.model
    def set_loyalty_program_to_main_config(self):
        main_config = self.env.ref('point_of_sale.pos_config_main')
        default_loyalty_program = self._default_loyalty_program()
        main_config.write({'module_pos_loyalty': bool(default_loyalty_program), 'loyalty_id': default_loyalty_program.id})

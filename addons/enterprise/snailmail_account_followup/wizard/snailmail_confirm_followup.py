# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SnailmailConfirmFollowup(models.TransientModel):
    _name = 'snailmail.confirm.followup'
    _inherit = ['snailmail.confirm']
    _description = 'Snailmail Confirm Followup'

    followup_id = fields.Many2one('followup.send')

    def _confirm(self):
        self.ensure_one()
        self.followup_id._snailmail_send()

    def _continue(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window_close'}

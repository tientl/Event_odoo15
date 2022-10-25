# -*- coding: utf-8 -*-
# Part of TienLT. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
import random


class Users(models.Model):
    _inherit = 'res.partner'

    user_name = fields.Char(string='User name')
    password = fields.Char(string='Password')

    @api.onchange('email')
    def _onchange_user_pasword(self):
        if self.email:
            self.user_name = self.email
            self.password = random.randrange(1000, 9999)

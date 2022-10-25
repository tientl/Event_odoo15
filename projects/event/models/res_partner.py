# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random
from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    user_name = fields.Char(string='User name')
    password = fields.Char(string='Password')
    is_show_password = fields.Boolean(
        string='Show password',
        default=False,
        store=False
    )

    @api.onchange('email')
    def _onchange_user_pasword(self):
        if self.email:
            self.user_name = self.email
            self.password = random.randrange(1000, 9999)

    event_count = fields.Integer(
        '# Events', compute='_compute_event_count', groups='event.group_event_registration_desk',
        help='Number of events the partner has participated.')

    def _compute_event_count(self):
        self.event_count = 0
        for partner in self:
            partner.event_count = self.env['event.event'].search_count(
                [('registration_ids.partner_id', 'child_of', partner.ids)])

    def action_event_view(self):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "event.action_event_view")
        action['context'] = {}
        action['domain'] = [
            ('registration_ids.partner_id', 'child_of', self.ids)]
        return action

    def action_show_password(self):
        for res in self:
            res.is_show_password = True

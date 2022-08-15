# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    helpdesk_target_closed = fields.Float(string='Target Tickets to Close', default=1)
    helpdesk_target_rating = fields.Float(string='Target Customer Rating', default=100)
    helpdesk_target_success = fields.Float(string='Target Success Rate', default=100)

    _sql_constraints = [
        ('target_closed_not_zero', 'CHECK(helpdesk_target_closed > 0)', 'You cannot have negative targets'),
        ('target_rating_not_zero', 'CHECK(helpdesk_target_rating > 0)', 'You cannot have negative targets'),
        ('target_success_not_zero', 'CHECK(helpdesk_target_success > 0)', 'You cannot have negative targets'),
    ]

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            'helpdesk_target_closed',
            'helpdesk_target_rating',
            'helpdesk_target_success',
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + [
            'helpdesk_target_closed',
            'helpdesk_target_rating',
            'helpdesk_target_success',
        ]

    def write(self, vals):
        if 'active' in vals and not vals.get('active'):
            teams = self.env['helpdesk.team'].search([('visibility_member_ids', 'in', self.ids)])
            for team in teams:
                unlinks = [Command.unlink(user.id) for user in teams.member_ids if user in self]
                team.write({'visibility_member_ids': unlinks})
        return super().write(vals)

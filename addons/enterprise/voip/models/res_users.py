# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields

# Add 'sip_password' field to the private fields.
# Only users who can modify the res_user (incl. the user himself) see the private fields real content
from odoo.addons.base.models import res_users
res_users.USER_PRIVATE_FIELDS.append('sip_password')

VOIP_FIELDS = [
    'sip_login',
    'sip_password',
    'sip_external_phone',
    'sip_always_transfer',
    'sip_ignore_incoming',
    'mobile_call_method',
]


class ResUsers(models.Model):
    _inherit = 'res.users'

    mobile_call_method = fields.Selection(
        [('ask', 'Ask'), ('voip', 'Voip'), ('phone', 'Phone')],
        string="Mobile call",
        groups="base.group_user",
        default='ask',
        required=True,
        help="""Method to use to made a call on mobile:
        * VoIP: Always used as a softphone
        * Phone: Always use the device's phone
        * Ask: Always prompt""")
    sip_login = fields.Char("SIP Login / Browser's Extension", groups="base.group_user")
    sip_password = fields.Char('SIP Password', groups="base.group_user")
    sip_external_phone = fields.Char("Handset Extension", groups="base.group_user")
    sip_always_transfer = fields.Boolean("Always Redirect to Handset", default=False,
                                         groups="base.group_user")
    sip_ignore_incoming = fields.Boolean("Reject All Incoming Calls", default=False,
                                         groups="base.group_user")

    last_seen_phone_call = fields.Many2one('voip.phonecall')

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + VOIP_FIELDS

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + VOIP_FIELDS

    @api.model
    def reset_last_seen_phone_call(self):
        domain = [
            ('user_id', '=', self.env.user.id),
            ('call_date', '!=', False),
            ('in_queue', '=', True),
        ]
        last_call = self.env['voip.phonecall'].search(domain, order='call_date desc', limit=1)
        self.env.user.last_seen_phone_call = last_call.id

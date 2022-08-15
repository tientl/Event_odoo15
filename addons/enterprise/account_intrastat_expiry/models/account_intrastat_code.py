# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class AccountIntrastatCode(models.Model):
    _inherit = ['account.intrastat.code']

    expiry_date = fields.Date(
        string='Expiry Date',
        help='Date at which a code must not be used anymore.',
    )
    start_date = fields.Date(
        string='Usage start date',
        help='Date from which a code may be used.',
    )

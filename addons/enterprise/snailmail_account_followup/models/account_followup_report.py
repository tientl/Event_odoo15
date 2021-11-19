# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class AccountFollowupReport(models.AbstractModel):
    _inherit = "account.followup.report"

    def _get_line_info(self, followup_line):
        res = super(AccountFollowupReport , self)._get_line_info(followup_line)
        res.update(send_letter=followup_line.send_letter)
        return res

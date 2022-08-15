# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    def _execute_followup_partner(self):
        for partner in self:
            if partner.followup_status == 'in_need_of_action':
                followup_line = partner.followup_level
                if followup_line.send_letter:
                    letter = self.env['snailmail.letter'].create({
                        'state': 'pending',
                        'partner_id': partner.id,
                        'model': 'res.partner',
                        'res_id': partner.id,
                        'user_id': self.env.user.id,
                        'report_template': self.env.ref('account_followup.action_report_followup').id,
                        # we will only process partners that are linked to the user current company
                        # TO BE CHECKED
                        'company_id': self.env.company.id,
                    })
                    letter._snailmail_print()
        return super(ResPartner, self)._execute_followup_partner()

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    def _action_done(self, feedback=False, attachment_ids=None):
        leave_to_defer_activity_type = self.env.ref('hr_payroll_holidays.mail_activity_data_hr_leave_to_defer')
        res_ids = self.filtered(lambda a: a.activity_type_id == leave_to_defer_activity_type).mapped('res_id')
        self.env['hr.leave'].browse(res_ids).write({'payslip_state': 'done'}) #done or normal??? to check
        return super()._action_done(feedback=feedback, attachment_ids=attachment_ids)

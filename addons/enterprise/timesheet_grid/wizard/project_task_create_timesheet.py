# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ProjectTaskCreateTimesheet(models.TransientModel):
    _inherit = 'project.task.create.timesheet'

    def save_timesheet(self):
        # Not calling super as def deprecated in hr_timesheet.
        # The wizard has to be moved to timesheet_grid in master.
        values = {
            'task_id': self.task_id.id,
            'project_id': self.task_id.project_id.id,
            'date': fields.Date.context_today(self),
            'name': self.description,
            'user_id': self.env.uid,
            'unit_amount': self.task_id._get_rounded_hours(self.time_spent * 60),
        }
        self.task_id.user_timer_id.unlink()
        return self.env['account.analytic.line'].create(values)

    def action_delete_timesheet(self):
        self.task_id.user_timer_id.unlink()

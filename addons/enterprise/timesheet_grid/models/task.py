# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _


class Task(models.Model):
    _name = "project.task"
    _inherit = ["project.task", "timer.mixin"]

    display_timesheet_timer = fields.Boolean("Display Timesheet Time", compute='_compute_display_timesheet_timer')

    display_timer_start_secondary = fields.Boolean(compute='_compute_display_timer_buttons')

    @api.depends_context('uid')
    @api.depends('display_timesheet_timer', 'timer_start', 'timer_pause', 'total_hours_spent')
    def _compute_display_timer_buttons(self):
        user_has_employee_or_only_one = None
        for task in self:
            if not task.display_timesheet_timer:
                task.update({
                    'display_timer_start_primary': False,
                    'display_timer_start_secondary': False,
                    'display_timer_stop': False,
                    'display_timer_pause': False,
                    'display_timer_resume': False,
                })
            else:
                super(Task, task)._compute_display_timer_buttons()
                task.display_timer_start_secondary = task.display_timer_start_primary
                if not task.timer_start:
                    task.update({
                        'display_timer_stop': False,
                        'display_timer_pause': False,
                        'display_timer_resume': False,
                    })
                    if user_has_employee_or_only_one is None:
                        user_has_employee_or_only_one = bool(self.env.user.employee_id)\
                                                     or self.env['hr.employee'].sudo().search_count([('user_id', '=', self.env.uid)]) == 1
                    if not user_has_employee_or_only_one:
                        task.display_timer_start_primary = False
                        task.display_timer_start_secondary = False
                    elif not task.total_hours_spent:
                        task.display_timer_start_secondary = False
                    else:
                        task.display_timer_start_primary = False

    @api.depends('allow_timesheets', 'analytic_account_active')
    def _compute_display_timesheet_timer(self):
        for task in self:
            task.display_timesheet_timer = task.allow_timesheets and task.analytic_account_active

    def action_timer_start(self):
        if not self.user_timer_id.timer_start and self.display_timesheet_timer:
            super(Task, self).action_timer_start()

    def action_timer_stop(self):
        # timer was either running or paused
        if self.user_timer_id.timer_start and self.display_timesheet_timer:
            rounded_hours = self._get_rounded_hours(self.user_timer_id._get_minutes_spent())
            return self._action_open_new_timesheet(rounded_hours)
        return False

    def _get_rounded_hours(self, minutes):
        minimum_duration = int(self.env['ir.config_parameter'].sudo().get_param('timesheet_grid.timesheet_min_duration', 0))
        rounding = int(self.env['ir.config_parameter'].sudo().get_param('timesheet_grid.timesheet_rounding', 0))
        rounded_minutes = self._timer_rounding(minutes, minimum_duration, rounding)
        return rounded_minutes / 60

    def _action_open_new_timesheet(self, time_spent):
        return {
            "name": _("Confirm Time Spent"),
            "type": 'ir.actions.act_window',
            "res_model": 'project.task.create.timesheet',
            "views": [[False, "form"]],
            "target": 'new',
            "context": {
                **self.env.context,
                'active_id': self.id,
                'active_model': self._name,
                'default_time_spent': time_spent,
            },
        }

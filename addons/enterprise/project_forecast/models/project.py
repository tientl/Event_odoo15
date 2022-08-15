# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import datetime
import json

from odoo import api, fields, models, _, _lt
from odoo.exceptions import UserError
from odoo.osv import expression


class Project(models.Model):
    _inherit = 'project.project'

    allow_forecast = fields.Boolean("Planning", default=True, help="Enable planning tasks on the project.")
    total_forecast_time = fields.Integer(compute='_compute_total_forecast_time',
                                         help="Total number of forecast hours in the project rounded to the unit.")

    def _compute_total_forecast_time(self):
        shifts_read_group = self.env['planning.slot'].read_group(
            [('start_datetime', '!=', False), ('end_datetime', '!=', False), ('project_id', 'in', self.ids)],
            ['project_id', 'allocated_hours'],
            ['project_id'],
        )
        shifts_per_project = {res['project_id'][0]: int(round(res['allocated_hours'])) for res in shifts_read_group}
        for project in self:
            project.total_forecast_time = shifts_per_project.get(project.id, 0)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_contains_plannings(self):
        if self.env['planning.slot'].sudo().search_count([('project_id', 'in', self.ids)]) > 0:
            raise UserError(_('You cannot delete a project containing plannings. You can either delete all the project\'s forecasts and then delete the project or simply deactivate the project.'))

    @api.depends('is_fsm')
    def _compute_allow_forecast(self):
        for project in self:
            if not project._origin:
                project.allow_forecast = not project.is_fsm

    def action_project_forecast_from_project(self):
        action = self.env["ir.actions.actions"]._for_xml_id("project_forecast.project_forecast_action_from_project")
        first_slot = self.env['planning.slot'].search([('start_datetime', '>=', datetime.datetime.now()), ('project_id', '=', self.id)], limit=1, order="start_datetime")
        action['context'] = {
            'default_project_id': self.id,
            'search_default_project_id': [self.id],
            **ast.literal_eval(action['context'])
        }
        if first_slot:
            action['context'].update({'initialDate': first_slot.start_datetime})
        elif self.date_start and self.date_start >= datetime.date.today():
            action['context'].update({'initialDate': self.date_start})
        return action

    # ----------------------------
    #  Project Updates
    # ----------------------------

    def _get_stat_buttons(self):
        buttons = super(Project, self)._get_stat_buttons()
        buttons.append({
            'icon': 'tasks',
            'text': _lt('Forecast'),
            'number': '%s Hours' % (self.total_forecast_time),
            'action_type': 'object',
            'action': 'action_project_forecast_from_project',
            'additional_context': json.dumps({
                'active_id': self.id,
            }),
            'show': self.allow_forecast,
            'sequence': 6,
        })
        return buttons

class Task(models.Model):
    _inherit = 'project.task'

    allow_forecast = fields.Boolean('Allow Planning', readonly=True, related='project_id.allow_forecast', store=False)
    forecast_hours = fields.Integer('Forecast Hours', compute='_compute_forecast_hours', help="Number of hours forecast for this task (and its sub-tasks), rounded to the unit.")

    def _compute_forecast_hours(self):
        domain = expression.AND([
            self._get_domain_compute_forecast_hours(),
            [('task_id', 'in', self.ids + self._get_all_subtasks().ids)]
        ])
        forecast_data = self.env['planning.slot'].read_group(domain, ['allocated_hours', 'task_id'], ['task_id'])
        mapped_data = dict([(f['task_id'][0], f['allocated_hours']) for f in forecast_data])
        for task in self:
            hours = mapped_data.get(task.id, 0) + sum(mapped_data.get(child_task.id, 0) for child_task in task._get_all_subtasks())
            task.forecast_hours = int(round(hours))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_contains_plannings(self):
        if self.env['planning.slot'].sudo().search_count([('task_id', 'in', self.ids)]) > 0:
            raise UserError(_('You cannot delete a task containing plannings. You can either delete all the task\'s plannings and then delete the task or simply deactivate the task.'))

    def action_get_project_forecast_by_user(self):
        allowed_tasks = (self | self._get_all_subtasks() | self.depend_on_ids)
        action = self.env["ir.actions.actions"]._for_xml_id("project_forecast.project_forecast_action_schedule_by_employee")
        first_slot = self.env['planning.slot'].search([('start_datetime', '>=', datetime.datetime.now()), ('task_id', 'in', allowed_tasks.ids)], limit=1, order="start_datetime")
        action_context = {
            'group_by': ['task_id', 'resource_id'],
        }
        if first_slot:
            action_context.update({'initialDate': first_slot.start_datetime})
        else:
            planned_tasks = allowed_tasks.filtered('planned_date_begin')
            min_date = min(planned_tasks.mapped('planned_date_begin')) if planned_tasks else False
            if min_date and min_date > datetime.datetime.now():
                action_context.update({'initialDate': min_date})
        action['context'] = action_context
        action['domain'] = [('task_id', 'in', allowed_tasks.ids)]
        return action

    # -------------------------------------------
    # Utils method
    # -------------------------------------------

    @api.model
    def _get_domain_compute_forecast_hours(self):
        return []

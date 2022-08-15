# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta
import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression


_logger = logging.getLogger(__name__)


class PlanningShift(models.Model):
    _inherit = 'planning.slot'

    @api.model
    def default_get(self, fields):
        result = super(PlanningShift, self).default_get(fields)
        if 'project_id' in fields and 'task_id' in result and 'project_id' not in result:
            task_id = self.env['project.task'].browse(result['task_id'])
            result['project_id'] = task_id.project_id.id
        return result

    project_id = fields.Many2one(
        'project.project', string="Project", compute='_compute_project_id', store=True,
        readonly=False, copy=True, check_company=True, group_expand='_read_group_project_id',
        domain="[('company_id', '=', company_id), ('allow_forecast', '=', True)]")
    task_id = fields.Many2one(
        'project.task', string="Task", compute='_compute_task_id', store=True, readonly=False,
        copy=True, check_company=True, group_expand='_read_group_task_id',
        domain="[('company_id', '=', company_id), ('project_id', '=?', project_id), ('allow_forecast', '=', True)]")
    planned_hours = fields.Float("Initially Planned Hours", related="task_id.planned_hours")
    allow_forecast = fields.Boolean(related="project_id.allow_forecast")
    forecast_hours = fields.Float("Forecast Hours", compute='_compute_forecast_hours', help="Number of hours already forecast for this task (and its sub-tasks).")
    parent_id = fields.Many2one('project.task', related='task_id.parent_id', store=True)  # store for group by
    resource_id = fields.Many2one(compute='_compute_resource_id', store=True, readonly=False)

    _sql_constraints = [
        ('project_required_if_task', "CHECK( (task_id IS NOT NULL AND project_id IS NOT NULL) OR (task_id IS NULL) )", "If the planning is linked to a task, the project must be set too."),
    ]

    @api.depends('task_id', 'allocated_hours', 'project_id')
    def _compute_forecast_hours(self):
        for slot in self:
            # Compare with _origin because the number of hours of the task is not yet modified.
            # use sudo to compute for private project's tasks
            task_sudo = slot.sudo().task_id
            if not task_sudo:
                slot.forecast_hours = 0
            elif slot._origin.allocated_hours != slot.allocated_hours:
                if slot._origin.task_id == task_sudo:
                    slot.forecast_hours = task_sudo.forecast_hours - slot._origin.allocated_hours + slot.allocated_hours
                else:
                    slot.forecast_hours = task_sudo.forecast_hours + slot.allocated_hours
            else:
                slot.forecast_hours = task_sudo.forecast_hours

    @api.depends('task_id.project_id', 'template_id.project_id')
    def _compute_project_id(self):
        for slot in self:
            if slot.task_id:
                slot.project_id = slot.task_id.project_id

            if slot.template_id:
                slot.previous_template_id = slot.template_id
                if slot.template_id.project_id:
                    slot.project_id = slot.template_id.project_id
            elif slot.previous_template_id and not slot.template_id and slot.previous_template_id.project_id == slot.project_id:
                slot.project_id = False

    @api.depends('project_id', 'template_id.project_id')
    def _compute_task_id(self):
        for slot in self:
            if slot.project_id != slot.task_id.project_id:
                slot.task_id = False
            if slot.template_id:
                slot.previous_template_id = slot.template_id
                if slot.template_id.task_id:
                    slot.task_id = slot.template_id.task_id
            elif slot.previous_template_id and not slot.template_id and slot.previous_template_id.task_id == slot.task_id:
                slot.task_id = False

    @api.constrains('task_id', 'project_id')
    def _check_task_in_project(self):
        for forecast in self:
            if forecast.task_id and (forecast.task_id not in forecast.project_id.with_context(active_test=False).tasks):
                raise ValidationError(_("Your task is not in the selected project."))

    def _read_group_project_id(self, projects, domain, order):
        dom_tuples = [(dom[0], dom[1]) for dom in domain if isinstance(dom, list) and len(dom) == 3]
        if self._context.get('planning_expand_project') and ('start_datetime', '<=') in dom_tuples and ('end_datetime', '>=') in dom_tuples:
            if ('project_id', '=') in dom_tuples or ('project_id', 'ilike') in dom_tuples:
                filter_domain = self._expand_domain_m2o_groupby(domain, 'project_id')
                return self.env['project.project'].search(filter_domain, order=order)
            filters = expression.AND([[('project_id.active', '=', True)], self._expand_domain_dates(domain)])
            return self.env['planning.slot'].search(filters).mapped('project_id')
        return projects

    def _read_group_task_id(self, tasks, domain, order):
        if 'show_tasks_without_slot' in self.env.context and 'active_ids' in self.env.context:
            return self.env['project.task'].browse(self.env.context.get('active_ids'))
        dom_tuples = [(dom[0], dom[1]) for dom in domain if isinstance(dom, list) and len(dom) == 3]
        if self._context.get('planning_expand_task') and ('start_datetime', '<=') in dom_tuples and ('end_datetime', '>=') in dom_tuples:
            if ('task_id', '=') in dom_tuples or ('task_id', 'ilike') in dom_tuples:
                filter_domain = self._expand_domain_m2o_groupby(domain, 'task_id')
                return self.env['project.task'].search(filter_domain, order=order)
            filters = expression.AND([[('task_id.active', '=', True)], self._expand_domain_dates(domain)])
            return self.env['planning.slot'].search(filters).mapped('task_id')
        return tasks

    def _get_fields_breaking_publication(self):
        """ Fields list triggering the `publication_warning` to True when updating shifts """
        result = super(PlanningShift, self)._get_fields_breaking_publication()
        result.extend(['project_id', 'task_id'])
        return result

    def _name_get_fields(self):
        fields = super(PlanningShift, self)._name_get_fields()
        fields.insert(1, 'project_id')
        fields.insert(2, 'task_id')
        return fields

    def _prepare_template_values(self):
        result = super(PlanningShift, self)._prepare_template_values()
        return {
            'project_id': self.project_id.id,
            'task_id': self.task_id.id,
            **result
        }

    @api.model
    def _get_template_fields(self):
        values = super(PlanningShift, self)._get_template_fields()
        return {'project_id': 'project_id', 'task_id': 'task_id', **values}

    def _get_domain_template_slots(self):
        domain = super(PlanningShift, self)._get_domain_template_slots()
        if self.task_id:
            domain += ['|', ('task_id', '=', self.task_id.id), ('project_id', '=', False)]
        elif self.project_id:
            domain += ['|', ('project_id', '=', self.project_id.id), ('project_id', '=', False)]
        return domain

    @api.depends('role_id', 'employee_id', 'project_id', 'task_id')
    def _compute_template_autocomplete_ids(self):
        super(PlanningShift, self)._compute_template_autocomplete_ids()

    @api.depends('role_id', 'employee_id', 'project_id', 'task_id', 'start_datetime', 'allocated_hours')
    def _compute_template_id(self):
        super(PlanningShift, self)._compute_template_id()

    @api.depends('template_id', 'role_id', 'allocated_hours', 'project_id', 'task_id')
    def _compute_allow_template_creation(self):
        super(PlanningShift, self)._compute_allow_template_creation()

    @api.depends('task_id')
    def _compute_resource_id(self):
        for slot in self:
            if slot.resource_id or not slot.task_id:
                continue
            user_to_assign = slot.task_id.user_ids
            if len(user_to_assign) > 1:
                user_to_assign = (slot.role_id.employee_ids.user_id & user_to_assign)[:1] or user_to_assign[:1]
            slot.resource_id = user_to_assign.employee_id.resource_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('task_id'):
                vals['project_id'] = self.env['project.task'].browse(vals.get('task_id')).project_id.id
        return super().create(vals_list)

    def write(self, values):
        if 'task_id' in values and values['task_id'] and 'project_id' not in values:
            values['project_id'] = self.env['project.task'].browse(values['task_id']).project_id.id
        return super(PlanningShift, self).write(values)

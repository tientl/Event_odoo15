# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta, datetime, time
import pytz

from odoo import Command, fields, models, api, _


# YTI TODO: Split file into 2
class Project(models.Model):
    _inherit = "project.project"

    is_fsm = fields.Boolean("Field Service", default=False, help="Display tasks in the Field Service module and allow planning with start/end dates.")
    allow_subtasks = fields.Boolean(
        compute="_compute_allow_subtasks", store=True, readonly=False)
    allow_task_dependencies = fields.Boolean(compute='_compute_allow_task_dependencies', store=True, readonly=False)

    @api.depends("is_fsm")
    def _compute_allow_subtasks(self):
        has_group = self.env.user.has_group("project.group_subtask_project")
        for project in self:
            project.allow_subtasks = has_group and not project.is_fsm

    @api.depends('is_fsm')
    def _compute_allow_task_dependencies(self):
        has_group = self.user_has_groups('project.group_project_task_dependencies')
        for project in self:
            project.allow_task_dependencies = has_group and not project.is_fsm

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if 'allow_subtasks' in fields_list:
            defaults['allow_subtasks'] = defaults.get('allow_subtasks', False) and not defaults.get('is_fsm')
        if 'allow_task_dependencies' in fields_list:
            defaults['allow_task_dependencies'] = defaults.get('allow_task_dependencies', False) and not defaults.get('is_fsm')
        return defaults


class Task(models.Model):
    _inherit = "project.task"

    @api.model
    def default_get(self, fields_list):
        result = super(Task, self).default_get(fields_list)
        is_fsm_mode = self._context.get('fsm_mode')
        if 'project_id' in fields_list and not result.get('project_id') and is_fsm_mode:
            company_id = self.env.context.get('default_company_id') or self.env.company.id
            fsm_project = self.env['project.project'].search([('is_fsm', '=', True), ('company_id', '=', company_id)], order='sequence', limit=1)
            if fsm_project:
                result['stage_id'] = self.stage_find(fsm_project.id, [('fold', '=', False), ('is_closed', '=', False)])
            result['project_id'] = fsm_project.id

        date_begin = result.get('planned_date_begin')
        date_end = result.get('planned_date_end')
        if is_fsm_mode and (date_begin or date_end):
            if not date_begin:
                date_begin = date_end.replace(hour=0, minute=0, second=1)
            if not date_end:
                date_end = date_begin.replace(hour=23, minute=59, second=59)
            date_diff = date_end - date_begin
            if date_diff.days > 0:
                # force today if default is more than 24 hours (for eg. "Add" button in gantt view)
                today = fields.Date.context_today(self)
                date_begin = datetime.combine(today, time(0, 0, 0))
                date_end = datetime.combine(today, time(23, 59, 59))
            if date_diff.seconds / 3600 > 23.5:
                # if the interval between both dates are more than 23 hours and 30 minutes
                # then we changes those dates to fit with the working schedule of the assigned user or the current company
                # because we assume here, the planned dates are not the ones chosen by the current user.
                user_tz = pytz.timezone(self.env.context.get('tz') or 'UTC')
                date_begin = pytz.utc.localize(date_begin).astimezone(user_tz)
                date_end = pytz.utc.localize(date_end).astimezone(user_tz)
                user_ids_list = [res[2] for res in result.get('user_ids', []) if len(res) == 3 and res[0] == Command.SET]  # user_ids = [(Command.SET, 0, <user_ids>)]
                user_ids = user_ids_list[-1] if user_ids_list else []
                users = self.env['res.users'].sudo().browse(user_ids)
                user = len(users) == 1 and users
                if user and user.employee_id:  # then the default start/end hours correspond to what is configured on the employee calendar
                    resource_calendar = user.resource_calendar_id
                else:  # Otherwise, the default start/end hours correspond to what is configured on the company calendar
                    company = self.env['res.company'].sudo().browse(result.get('company_id')) if result.get(
                        'company_id') else self.env.user.company_id
                    resource_calendar = company.resource_calendar_id
                if resource_calendar:
                    resources_work_intervals = resource_calendar._work_intervals_batch(date_begin, date_end)
                    work_intervals = [(start, stop) for start, stop, meta in resources_work_intervals[False]]
                    if work_intervals:
                        planned_date_begin = work_intervals[0][0].astimezone(pytz.utc).replace(tzinfo=None)
                        planned_date_end = work_intervals[-1][1].astimezone(pytz.utc).replace(tzinfo=None)
                        result['planned_date_begin'] = planned_date_begin
                        result['planned_date_end'] = planned_date_end
                else:
                    result['planned_date_begin'] = date_begin.replace(hour=9, minute=0, second=1).astimezone(pytz.utc).replace(tzinfo=None)
                    result['planned_date_end'] = date_end.astimezone(pytz.utc).replace(tzinfo=None)
        return result

    is_fsm = fields.Boolean(related='project_id.is_fsm', search='_search_is_fsm')
    fsm_done = fields.Boolean("Task Done", compute='_compute_fsm_done', readonly=False, store=True, copy=False)
    user_ids = fields.Many2many(group_expand='_read_group_user_ids')
    # Use to count conditions between : time, worksheet and materials
    # If 2 over 3 are enabled for the project, the required count = 2
    # If 1 over 3 is met (enabled + encoded), the satisfied count = 2
    display_enabled_conditions_count = fields.Integer(compute='_compute_display_conditions_count')
    display_satisfied_conditions_count = fields.Integer(compute='_compute_display_conditions_count')
    display_mark_as_done_primary = fields.Boolean(compute='_compute_mark_as_done_buttons')
    display_mark_as_done_secondary = fields.Boolean(compute='_compute_mark_as_done_buttons')
    has_complete_partner_address = fields.Boolean(compute='_compute_has_complete_partner_address')

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS | {'is_fsm',
                                              'planned_date_begin',
                                              'planned_date_end',
                                              'fsm_done',
                                              'partner_phone',
                                              'partner_city',
                                              'has_complete_partner_address'}

    @api.depends(
        'fsm_done', 'is_fsm', 'timer_start',
        'display_enabled_conditions_count', 'display_satisfied_conditions_count')
    def _compute_mark_as_done_buttons(self):
        for task in self:
            primary, secondary = True, True
            if task.fsm_done or not task.is_fsm or task.timer_start:
                primary, secondary = False, False
            else:
                if task.display_enabled_conditions_count == task.display_satisfied_conditions_count:
                    secondary = False
                else:
                    primary = False
            task.update({
                'display_mark_as_done_primary': primary,
                'display_mark_as_done_secondary': secondary,
            })

    @api.depends('project_id.allow_timesheets', 'total_hours_spent')
    def _compute_display_conditions_count(self):
        for task in self:
            enabled = 1 if task.project_id.allow_timesheets else 0
            satisfied = 1 if enabled and task.total_hours_spent else 0
            task.update({
                'display_enabled_conditions_count': enabled,
                'display_satisfied_conditions_count': satisfied
            })

    @api.depends('fsm_done', 'display_timesheet_timer', 'timer_start', 'total_hours_spent')
    def _compute_display_timer_buttons(self):
        fsm_done_tasks = self.filtered(lambda task: task.fsm_done)
        fsm_done_tasks.update({
            'display_timer_start_primary': False,
            'display_timer_start_secondary': False,
            'display_timer_stop': False,
            'display_timer_pause': False,
            'display_timer_resume': False,
        })
        super(Task, self - fsm_done_tasks)._compute_display_timer_buttons()

    @api.depends('partner_id')
    def _compute_has_complete_partner_address(self):
        for task in self:
            task.has_complete_partner_address = task.partner_id.city and task.partner_id.country_id

    @api.model
    def _search_is_fsm(self, operator, value):
        query = """
            SELECT p.id
            FROM project_project P
            WHERE P.active = 't' AND P.is_fsm
        """
        operator_new = operator == "=" and "inselect" or "not inselect"
        return [('project_id', operator_new, (query, ()))]

    @api.model
    def _read_group_user_ids(self, users, domain, order):
        if self.env.context.get('fsm_mode'):
            recently_created_tasks = self.env['project.task'].search([
                ('create_date', '>', datetime.now() - timedelta(days=30)),
                ('is_fsm', '=', True),
                ('user_ids', '!=', False)
            ])
            search_domain = ['&',('company_id', 'in', self.env.companies.ids) ,'|', '|', ('id', 'in', users.ids), ('groups_id', 'in', self.env.ref('industry_fsm.group_fsm_user').id), ('id', 'in', recently_created_tasks.mapped('user_ids.id'))]
            return users.search(search_domain, order=order)
        return users

    def _compute_fsm_done(self):
        for task in self:
            closed_stage = task.project_id.type_ids.filtered('is_closed')
            if closed_stage:
                task.fsm_done = task.stage_id in closed_stage

    def action_view_timesheets(self):
        kanban_view = self.env.ref('hr_timesheet.view_kanban_account_analytic_line')
        form_view = self.env.ref('industry_fsm.timesheet_view_form')
        tree_view = self.env.ref('industry_fsm.timesheet_view_tree_user_inherit')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Time'),
            'res_model': 'account.analytic.line',
            'view_mode': 'list,form,kanban',
            'views': [(tree_view.id, 'list'), (kanban_view.id, 'kanban'), (form_view.id, 'form')],
            'domain': [('task_id', '=', self.id), ('project_id', '!=', False)],
            'context': {
                'fsm_mode': True,
                'default_project_id': self.project_id.id,
                'default_task_id': self.id,
            }
        }

    def action_fsm_validate(self):
        """ Moves Task to next stage.
            If allow billable on task, timesheet product set on project and user has privileges :
            Create SO confirmed with time and material.
        """
        self._stop_all_timers_and_create_timesheets()
        closed_stage_by_project = {
            project.id:
                project.type_ids.filtered(lambda stage: stage.is_closed)[:1] or project.type_ids[-1:]
            for project in self.project_id
        }
        for task in self:
            # determine closed stage for task
            closed_stage = closed_stage_by_project.get(self.project_id.id)
            values = {'fsm_done': True}
            if closed_stage:
                values['stage_id'] = closed_stage.id

            task.write(values)

    def _stop_all_timers_and_create_timesheets(self):
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        Timesheet = self.env['account.analytic.line']
        Timer = self.env['timer.timer']

        tasks_running_timer_ids = Timer.search([('res_model', '=', 'project.task'), ('res_id', 'in', self.ids)])
        timesheets = Timesheet.sudo().search([('task_id', 'in', self.ids)])
        timesheets_running_timer_ids = None
        if timesheets:
            timesheets_running_timer_ids = Timer.search([
                ('res_model', '=', 'account.analytic.line'),
                ('res_id', 'in', timesheets.ids)])
        if not tasks_running_timer_ids and not timesheets_running_timer_ids:
            return Timesheet

        result = Timesheet
        minimum_duration = int(ConfigParameter.get_param('hr_timesheet.timesheet_min_duration', 0))
        rounding = int(ConfigParameter.get_param('hr_timesheet.timesheet_rounding', 0))
        if tasks_running_timer_ids:
            task_dict = {task.id: task for task in self}
            timesheets_val = []
            for timer in tasks_running_timer_ids:
                minutes_spent = timer._get_minutes_spent()
                time_spent = self._timer_rounding(minutes_spent, minimum_duration, rounding) / 60
                task = task_dict[timer.res_id]
                timesheets_val.append({
                    'task_id': task.id,
                    'project_id': task.project_id.id,
                    'user_id': timer.user_id.id,
                    'unit_amount': time_spent,
                })
            tasks_running_timer_ids.sudo().unlink()
            result += Timesheet.sudo().create(timesheets_val)

        if timesheets_running_timer_ids:
            timesheets_dict = {timesheet.id: timesheet for timesheet in timesheets}
            for timer in timesheets_running_timer_ids:
                timesheet = timesheets_dict[timer.res_id]
                minutes_spent = timer._get_minutes_spent()
                timesheet._add_timesheet_time(minutes_spent)
                result += timesheet
            timesheets_running_timer_ids.sudo().unlink()

        return result

    def action_fsm_navigate(self):
        if not self.partner_id.partner_latitude and not self.partner_id.partner_longitude:
            self.partner_id.geo_localize()
        url = "https://www.google.com/maps/dir/?api=1&destination=%s,%s" % (self.partner_id.partner_latitude, self.partner_id.partner_longitude)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new'
        }

    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        return self.env.user.employee_id._get_unusual_days(date_from, date_to)

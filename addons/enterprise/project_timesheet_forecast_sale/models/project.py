# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import api, fields, models, _, _lt

class Project(models.Model):
    _inherit = 'project.project'

    display_planning_timesheet_analysis = fields.Boolean(compute='_compute_display_planning_timesheet_analysis', help='Should we display the planning and timesheet analysis button?')

    @api.depends('allow_timesheets', 'allow_forecast')
    @api.depends_context('uid')
    def _compute_display_planning_timesheet_analysis(self):
        is_user_authorized = self.env.user.has_group('planning.group_planning_manager') and self.env.user.has_group('hr_timesheet.group_hr_timesheet_approver')
        if not is_user_authorized:
            self.display_planning_timesheet_analysis = False
        else:
            for project in self:
                project.display_planning_timesheet_analysis = project.allow_timesheets and project.allow_forecast

    # -------------------------------------------
    # Actions
    # -------------------------------------------

    def open_timesheets_planning_report(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("project_timesheet_forecast.project_timesheet_forecast_report_action")
        action.update({
            'name': 'Timesheets and Planning Analysis',
            'domain': [('project_id', '=', self.id)],
            'context': {
                'pivot_row_groupby': ['entry_date:month', 'sale_line_id'],
            }
        })
        return action

    # ----------------------------
    #  Project Updates
    # ----------------------------

    def _get_sold_items(self):
        sols = self._get_sale_order_lines()
        sold_items = super()._get_sold_items()
        sold_items['allow_forecast'] = self.allow_forecast
        planned_hours = self.env['planning.slot'].read_group([
            ('start_datetime', '>=', fields.Date.today()),
            '|',
            ('project_id', '=', self.id),
            ('order_line_id', 'in', sols.ids),
        ], ['allocated_hours'], [])
        uom_hour = self.env.ref('uom.product_uom_hour')
        if planned_hours and planned_hours[0]['allocated_hours']:
            sold_items['planned_sold'] = uom_hour._compute_quantity(planned_hours[0]['allocated_hours'], self.env.company.timesheet_encode_uom_id, raise_if_failure=False)
        else:
            sold_items['planned_sold'] = 0.0
        remaining = sold_items['remaining']['value'] - sold_items['planned_sold']
        sold_items['remaining'] = {
            'value': remaining,
            'color': 'red' if remaining < 0 else 'black',
        }
        return sold_items

    def _get_stat_buttons(self):
        buttons = super(Project, self)._get_stat_buttons()
        buttons.append({
            'icon': 'clock-o',
            'text': _lt('Timesheets and Planning'),
            'action_type': 'object',
            'action': 'open_timesheets_planning_report',
            'additional_context': json.dumps({
                'active_id': self.id,
            }),
            'show': self.display_planning_timesheet_analysis,
            'sequence': 8,
        })
        return buttons

class Task(models.Model):

    _inherit = 'project.task'

    def name_get(self):
        if 'project_task_display_forecast' in self._context:
            result = []
            for task in self:
                result.append((task.id, _('%s (%s remaining hours)') % (task.name, task.remaining_hours)))
            return result
        return super(Task, self).name_get()

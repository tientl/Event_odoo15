# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Project(models.Model):
    _inherit = 'project.project'

    def action_billable_time_button(self):
        action = super().action_billable_time_button()
        action['view_mode'] = 'tree,grid,kanban,pivot,graph,form'
        form_view_id = self.env.ref('timesheet_grid.timesheet_view_form').id
        action['views'] = [
            [form_view_id, view_mode] if view_mode == 'form' else [view_id, view_mode]
            for view_id, view_mode in action['views']
        ]
        action['views'].insert(1, [self.env.ref('timesheet_grid.timesheet_view_grid_by_employee').id, 'grid'])
        return action

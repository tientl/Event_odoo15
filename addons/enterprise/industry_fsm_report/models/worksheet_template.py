# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from ast import literal_eval

from odoo import api, models, _
from odoo.exceptions import UserError


class WorksheetTemplate(models.Model):
    _inherit = 'worksheet.template'

    def action_analysis_report(self):
        res = super().action_analysis_report()
        res['context'] = dict(literal_eval(res.get('context', '{}')), fsm_mode=True)
        return res

    @api.model
    def _get_models_to_check_dict(self):
        res = super()._get_models_to_check_dict()
        res['project.task'] = [('project.task', 'Task'), ('project.project', 'Project')]
        return res

    @api.model
    def _get_project_task_user_group(self):
        return self.env.ref('project.group_project_user')

    @api.model
    def _get_project_task_manager_group(self):
        return self.env.ref('project.group_project_manager')

    @api.model
    def _get_project_task_access_all_groups(self):
        return self.env.ref('project.group_project_manager') | self.env.ref('industry_fsm.group_fsm_user')

    @api.model
    def _get_project_task_module_name(self):
        return 'industry_fsm_report'

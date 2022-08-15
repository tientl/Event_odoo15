# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import format_amount

class ProjectUpdate(models.Model):
    _inherit = 'project.update'

    @api.model
    def _get_template_values(self, project):
        return {
            **super(ProjectUpdate, self)._get_template_values(project),
            'budget': self._get_budget_values(project),
        }

    @api.model
    def _get_budget_values(self, project):
        if not (self.user_has_groups('account.group_account_readonly') and (project.analytic_account_id)):
            return {}
        profitability = project._get_profitability_common()
        return {
            'percentage': round((-profitability['costs'] / project.budget) * 100 if project.budget != 0 else 0, 0),
            'amount': format_amount(self.env, project.budget, project.company_id.currency_id),
        }

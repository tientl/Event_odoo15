# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, api, models
from odoo.tools import html2plaintext, is_html_empty


class HrAppraisalGoal(models.Model):
    _name = "hr.appraisal.goal"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Appraisal Goal"

    name = fields.Char(required=True)
    employee_id = fields.Many2one('hr.employee', string="Employee",
        default=lambda self: self.env.user.employee_id, required=True)
    employee_autocomplete_ids = fields.Many2many('hr.employee', compute='_compute_is_manager')
    is_implicit_manager = fields.Boolean(compute='_compute_is_manager')
    manager_id = fields.Many2one('hr.employee', string="Manager", compute="_compute_manager_id", readonly=False, store=True, required=True)
    manager_user_id = fields.Many2one('res.users', related='manager_id.user_id')
    progression = fields.Selection(selection=[
        ('0', '0 %'),
        ('25', '25 %'),
        ('50', '50 %'),
        ('75', '75 %'),
        ('100', '100 %')
    ], string="Progress", default="0", required=True)
    description = fields.Html()
    deadline = fields.Date()
    is_manager = fields.Boolean(compute='_compute_is_manager')

    @api.depends_context('uid')
    @api.depends('employee_id')
    def _compute_is_manager(self):
        self.is_manager = self.env.user.has_group('hr_appraisal.group_hr_appraisal_user')
        for goal in self:
            if goal.is_manager:
                goal.is_implicit_manager = False
                goal.employee_autocomplete_ids = self.env['hr.employee'].search([])
            else:
                child_ids = self.env.user.employee_id.child_ids
                appraisal_child_ids = self.env.user.employee_id.appraisal_child_ids
                goal.employee_autocomplete_ids = child_ids + appraisal_child_ids + self.env.user.employee_id
                goal.is_implicit_manager = len(goal.employee_autocomplete_ids) > 1

    @api.depends('employee_id')
    def _compute_manager_id(self):
        for goal in self:
            goal.manager_id = goal.employee_id.parent_id

    def action_confirm(self):
        self.write({'progression': '100'})

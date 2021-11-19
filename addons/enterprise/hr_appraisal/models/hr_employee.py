# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    next_appraisal_date = fields.Date(
        string='Next Appraisal Date', groups="hr.group_hr_user",
        help="The date of the next appraisal is computed by the appraisal plan's dates (first appraisal + periodicity).")
    last_appraisal_date = fields.Date(
        string='Last Appraisal Date', groups="hr.group_hr_user",
        help="The date of the last appraisal",
        default=fields.Date.today)
    related_partner_id = fields.Many2one('res.partner', compute='_compute_related_partner', groups="hr.group_hr_user")
    appraisal_count = fields.Integer(compute='_compute_appraisal_count', store=True, groups="hr.group_hr_user")
    uncomplete_goals_count = fields.Integer(compute='_compute_uncomplete_goals_count')
    appraisal_child_ids = fields.Many2many('hr.employee', compute='_compute_appraisal_child_ids')
    appraisal_ids = fields.One2many('hr.appraisal', 'employee_id')

    def _compute_related_partner(self):
        for rec in self:
            rec.related_partner_id = rec.user_id.partner_id

    @api.depends('appraisal_ids')
    def _compute_appraisal_count(self):
        read_group_result = self.env['hr.appraisal'].with_context(active_test=False).read_group([('employee_id', 'in', self.ids)], ['employee_id'], ['employee_id'])
        result = dict((data['employee_id'][0], data['employee_id_count']) for data in read_group_result)
        for employee in self:
            employee.appraisal_count = result.get(employee.id, 0)

    def _compute_uncomplete_goals_count(self):
        read_group_result = self.env['hr.appraisal.goal'].read_group([('employee_id', 'in', self.ids), ('progression', '!=', '100')], ['employee_id'], ['employee_id'])
        result = dict((data['employee_id'][0], data['employee_id_count']) for data in read_group_result)
        for employee in self:
            employee.uncomplete_goals_count = result.get(employee.id, 0)

    def _compute_appraisal_child_ids(self):
        for employee in self:
            employee.appraisal_child_ids = self.env['hr.appraisal'].search([('manager_ids', '=', employee.id)]).employee_id

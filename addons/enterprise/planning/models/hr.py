# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import uuid

from odoo import fields, models, _, api

_logger = logging.getLogger(__name__)


class Employee(models.Model):
    _inherit = "hr.employee"

    def _default_employee_token(self):
        return str(uuid.uuid4())

    default_planning_role_id = fields.Many2one('planning.role', string="Default Planning Role", groups='hr.group_hr_user')
    planning_role_ids = fields.Many2many('planning.role', string="Planning Roles", groups='hr.group_hr_user', compute='_compute_planning_role_ids', store=True, readonly=False)
    employee_token = fields.Char('Security Token', default=_default_employee_token, copy=False, groups='hr.group_hr_user', readonly=True)

    _sql_constraints = [
        ('employee_token_unique', 'unique(employee_token)', 'Error: each employee token must be unique')
    ]

    def _fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        if not view_id and view_type == 'form' and self._context.get('force_email'):
            view_id = self.env.ref('planning.hr_employee_view_form_simplified').id
        return super()._fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

    def _init_column(self, column_name):
        # to avoid generating a single default employee_token when installing the module,
        # we need to set the default row by row for this column
        if column_name == "employee_token":
            _logger.debug("Table '%s': setting default value of new column %s to unique values for each row", self._table, column_name)
            self.env.cr.execute("SELECT id FROM %s WHERE employee_token IS NULL" % self._table)
            acc_ids = self.env.cr.dictfetchall()
            query_list = [{'id': acc_id['id'], 'employee_token': self._default_employee_token()} for acc_id in acc_ids]
            query = 'UPDATE ' + self._table + ' SET employee_token = %(employee_token)s WHERE id = %(id)s;'
            self.env.cr._obj.executemany(query, query_list)
        else:
            super(Employee, self)._init_column(column_name)

    def _planning_get_url(self, planning):
        result = {}
        for employee in self:
            if employee.user_id and employee.user_id.has_group('planning.group_planning_user'):
                result[employee.id] = '/web?date_start=%s&date_end=%s#action=planning.planning_action_open_shift&menu_id=' % (planning.date_start, planning.date_end)
            else:
                result[employee.id] = '/planning/%s/%s' % (planning.access_token, employee.employee_token)
        return result

    def _slot_get_url(self, slot):
        action_id = self.env.ref('planning.planning_action_open_shift').id
        menu_id = self.env.ref('planning.planning_menu_root').id
        dbname = self.env.cr.dbname or [''],
        start_date = slot.start_datetime.date() if slot else ''
        end_date = slot.end_datetime.date() if slot else ''
        link = "/web?date_start=%s&date_end=%s#action=%s&model=planning.slot&menu_id=%s&db=%s" % (start_date, end_date, action_id, menu_id, dbname[0])
        return {employee.id: link for employee in self}

    @api.depends('default_planning_role_id')
    def _compute_planning_role_ids(self):
        # Set the planning_role_ids to False where there's no value set yet, to avoid CacheMiss
        for employee in self.filtered(lambda s: s.planning_role_ids is None):
            employee.planning_role_ids = False

        for employee in self.filtered(lambda s: s.default_planning_role_id):
            if employee.default_planning_role_id and employee.default_planning_role_id not in employee.planning_role_ids:
                employee.planning_role_ids |= employee.default_planning_role_id

    def write(self, vals):
        res = super(Employee, self).write(vals)

        if 'default_planning_role_id' in vals or 'planning_role_ids' in vals:
            # Ensures the default_planning_role_id is added to the planning_role_ids
            self.env.add_to_compute(self._fields['planning_role_ids'], self)

        return res

class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    def action_view_planning(self):
        action = self.env["ir.actions.actions"]._for_xml_id("planning.planning_action_schedule_by_resource")
        action.update({
            'name': _('View Planning'),
            'domain': [('resource_id', 'in', self.resource_id.ids)],
            'context': {
                'search_default_group_by_resource': True,
                'filter_resource_ids': self.resource_id.ids,
                'hide_open_shift': True,
                'default_resource_id': self.resource_id.id if len(self) == 1 else False,
            }
        })
        return action

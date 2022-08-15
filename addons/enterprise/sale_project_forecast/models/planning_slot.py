# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class PlanningSlot(models.Model):
    _inherit = 'planning.slot'

    sale_line_id = fields.Many2one(compute='_compute_sale_line_id', store=True, readonly=False)

    @api.depends('sale_line_id.project_id', 'sale_line_id.task_id.project_id')
    def _compute_project_id(self):
        slot_without_sol_project = self.env['planning.slot']
        for slot in self:
            if not slot.project_id and slot.sale_line_id and (slot.sale_line_id.project_id or slot.sale_line_id.task_id.project_id):
                slot.project_id = slot.sale_line_id.task_id.project_id or slot.sale_line_id.project_id
            else:
                slot_without_sol_project |= slot
        super(PlanningSlot, slot_without_sol_project)._compute_project_id()

    @api.depends('project_id', 'task_id')
    def _compute_sale_line_id(self):
        for slot in self:
            if not slot.sale_line_id and slot.project_id:
                slot.sale_line_id = slot.task_id.sale_line_id or slot.project_id.sale_line_id

    @api.depends('sale_line_id.task_id')
    def _compute_task_id(self):
        slot_without_sol_task = self.env['planning.slot']
        for slot in self:
            if not slot.task_id and slot.sale_line_id and slot.sale_line_id.task_id and slot.project_id:
                slot.task_id = slot.sale_line_id.task_id
            else:
                slot_without_sol_task |= slot
        super(PlanningSlot, slot_without_sol_task)._compute_task_id()

    @api.depends('task_id')
    def _compute_resource_id(self):
        super(PlanningSlot, self.filtered('start_datetime'))._compute_resource_id()

    # -----------------------------------------------------------------
    # ORM Override
    # -----------------------------------------------------------------

    def _name_get_fields(self):
        """ List of fields that can be displayed in the name_get """
        # Ensure this will be displayed in the right order
        name_get_fields = [item for item in super()._name_get_fields() if item not in ['sale_line_id', 'project_id', 'task_id']]
        return name_get_fields + ['sale_line_id', 'project_id', 'task_id']

    # -----------------------------------------------------------------
    # Business methods
    # -----------------------------------------------------------------

    # -----------------------------------------------------------------
    # Assign sales order lines
    # -----------------------------------------------------------------

    @api.model
    def _get_employee_to_assign_priority_list(self):
        """
            This method will extend the possible priorities criteria.
            It makes sure any other priority is not skipped.
        """
        priority_list = super()._get_employee_to_assign_priority_list()

        def insert_after_or_append(preceding_priority, priority_to_insert):
            if preceding_priority in priority_list:
                priority_list.insert(priority_list.index(preceding_priority) + 1, priority_to_insert)
            else:
                priority_list.append(priority_to_insert)

        insert_after_or_append('previous_slot', 'task_assignee')
        return priority_list

    def _get_employee_per_priority(self, priority, employee_ids_to_exclude, cache):
        """
            This method returns the id of an employee filling the priority criterias and
            not present in the employee_ids_to_exclude.
        """
        employee_id = super()._get_employee_per_priority(priority, employee_ids_to_exclude, cache)
        if employee_id or priority in cache:
            return employee_id
        if priority == 'task_assignee' and self.task_id and len(self.task_id.user_ids) == 1:
            tmp_emp_id = self.task_id.user_ids.employee_id.id
            if tmp_emp_id not in employee_ids_to_exclude:
                cache[priority] = [tmp_emp_id]
        return cache[priority].pop(0) if cache.get(priority) else employee_id

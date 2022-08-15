# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression


class HrEmployee(models.Model):
    _name = 'hr.employee'
    _inherit = ['hr.employee', 'documents.mixin']

    document_count = fields.Integer(compute='_compute_document_count')

    def _get_document_folder(self):
        return self.company_id.documents_hr_folder if self.company_id.documents_hr_settings else False

    def _get_document_owner(self):
        return self.user_id

    def _get_document_partner(self):
        return self.address_home_id

    def _check_create_documents(self):
        return self.company_id.documents_hr_settings and super()._check_create_documents()

    def _get_employee_document_domain(self):
        self.ensure_one()
        user_domain = [('partner_id', '=', self.address_home_id.id)]
        if self.user_id:
            user_domain = expression.OR([user_domain,
                                        [('owner_id', '=', self.user_id.id)]])
        return user_domain

    def _compute_document_count(self):
        # Method not optimized for batches since it is only used in the form view.
        for employee in self:
            if employee.address_home_id:
                employee.document_count = self.env['documents.document'].search_count(
                    employee._get_employee_document_domain())
            else:
                employee.document_count = 0

    def action_open_documents(self):
        self.ensure_one()
        if not self.address_home_id:
            # Prevent opening documents if the employee's address is not set or no user is linked.
            raise ValidationError(_('You must set an address on the employee to use Documents features.'))
        hr_folder = self._get_document_folder()
        action = self.env['ir.actions.act_window']._for_xml_id('documents.document_action')
        # Documents created within that action will be 'assigned' to the employee
        # Also makes sure that the views starts on the hr_holder
        action['context'] = {
            'default_partner_id': self.address_home_id.id,
            'searchpanel_default_folder_id': hr_folder and hr_folder.id,
        }
        action['domain'] = self._get_employee_document_domain()
        return action

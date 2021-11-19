# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_encode, url_join

from odoo.addons.http_routing.models.ir_http import slug
from odoo import api, models, fields

class CalendarAppointmentShare(models.TransientModel):
    _name = 'calendar.appointment.share'
    _description = 'Calendar Appointment Share Wizard'

    def _domain_appointment_type_ids(self):
        return [('category', '=', 'website')]

    appointment_type_ids = fields.Many2many('calendar.appointment.type', domain=_domain_appointment_type_ids, string='Appointments')
    appointment_type_count = fields.Integer('Selected Appointments Count', compute='_compute_appointment_type_count')
    suggested_employee_ids = fields.Many2many('hr.employee', related='appointment_type_ids.employee_ids', string='Possible employees',
        help="Get the employees link to the appointment type selected to apply a domain on the employees that can be selected")
    employee_ids = fields.Many2many('hr.employee', domain=[('user_id', '!=', False)], string='Employees',
        compute='_compute_employee_id', inverse='_inverse_employee_id',
        help="The employees that will be display/filter for the user to make its appointment")
    share_link = fields.Char('Link', compute='_compute_share_link')

    @api.depends('appointment_type_ids')
    def _compute_appointment_type_count(self):
        for appointment_link in self:
            appointment_link.appointment_type_count = len(appointment_link.appointment_type_ids)

    @api.depends('appointment_type_ids')
    def _compute_employee_ids(self):
        for appointment_link in self:
            employees = appointment_link.appointment_type_ids.employee_ids._origin
            if len(employees) == 1:
                appointment_link.employee_ids = employees
            else:
                appointment_link.employee_ids = self.env.user.employee_id if self.env.user.employee_id in employees else False

    def _inverse_employee_ids(self):
        pass

    @api.depends('appointment_type_ids', 'employee_ids')
    def _compute_share_link(self):
        """
        Compute a link that will be share for the user depending on the appointment types and employees
        selected. We allow to preselect a group of employees if there is only one appointment type selected.
        Indeed, it would be too complex to manage employees with multiple appointment types.
        Two possible params can be generated with the link:
            - filter_employee_ids: which allows the user to select an employee between the ones selected
            - filter_appointment_type_ids: which display a selection of appointment types to user from which
            he can choose
        """
        calendar_url = url_join(self.get_base_url(), '/calendar')
        for appointment_link in self:
            url_param = dict()
            if len(appointment_link.appointment_type_ids) == 1:
                # If only one appointment type is selected, we share the appointment link with the possible employees selected
                if appointment_link.employee_ids:
                    url_param.update({
                        'filter_employee_ids': str(appointment_link.employee_ids.ids)
                    })
                appt_link = url_join('%s/' % calendar_url, slug(appointment_link.appointment_type_ids._origin))
                share_link = '%s?%s' % (appt_link, url_encode(url_param))
            elif appointment_link.appointment_type_ids:
                # If there are multiple appointment types selected, we share the link that will filter the appointments to the user
                url_param.update({
                    'filter_appointment_type_ids': str(appointment_link.appointment_type_ids.ids)
                })
                share_link = '%s?%s' % (calendar_url, url_encode(url_param))
            else:
                share_link = calendar_url

            appointment_link.share_link = share_link

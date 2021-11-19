# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.appointment.controllers.calendar import AppointmentController
from odoo.osv.expression import AND


class WebsiteAppointmentController(AppointmentController):
    def _get_employee_appointment_type_domain(self, employee):
        domain = super()._get_employee_appointment_type_domain(employee)
        return AND([domain, [('website_published', '=', True)]])

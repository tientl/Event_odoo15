# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.http_routing.models.ir_http import slug


class CalendarAppointmentType(models.Model):
    _name = "calendar.appointment.type"
    _inherit = [
        'calendar.appointment.type',
        'website.seo.metadata',
        'website.published.mixin',
        'website.cover_properties.mixin',
    ]

    @api.model
    def default_get(self, default_fields):
        result = super().default_get(default_fields)
        if result.get('category') in ['custom', 'work_hours']:
            result['is_published'] = True
        return result

    def _default_cover_properties(self):
        res = super()._default_cover_properties()
        res.update({
            'background-image': 'url("/website_appointment/static/src/img/appointment_cover_0.jpg")',
            'resize_class': 'o_record_has_cover o_half_screen_height',
            'opacity': '0.4',
        })
        return res

    is_published = fields.Boolean(
        compute='_compute_is_published', default=None,  # force None to avoid default computation from mixin
        readonly=False, store=True)

    @api.depends('category')
    def _compute_is_published(self):
        for appointment_type in self:
            if appointment_type.category in ['custom', 'work_hours']:
                appointment_type.is_published = True
            else:
                appointment_type.is_published = False

    def _compute_website_url(self):
        super(CalendarAppointmentType, self)._compute_website_url()
        for appointment_type in self:
            if appointment_type.id:
                appointment_type.website_url = '/calendar/%s/appointment' % (slug(appointment_type),)
            else:
                appointment_type.website_url = False

    def create_and_get_website_url(self, **kwargs):
        if 'appointment_tz' not in kwargs:
            # appointment_tz is a mandatory field defaulting to the environment user's timezone
            # however, sometimes the current user timezone is not defined, let's use a fallback
            website_visitor = self.env['website.visitor']._get_visitor_from_request(force_create=False)
            kwargs['appointment_tz'] = self.env.user.tz or website_visitor.timezone or 'UTC'

        return super().create_and_get_website_url(**kwargs)

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        """ Force False manually for all categories of appointment type when duplicating
        even for categories that should be auto-publish. """
        default = default if default is not None else {}
        default['is_published'] = False
        return super().copy(default)

    def get_backend_menu_id(self):
        return self.env.ref('calendar.mail_menu_calendar').id

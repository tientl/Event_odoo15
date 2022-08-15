# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import http
from odoo.http import request
from odoo.osv import expression

from odoo.addons.appointment.controllers.main import Appointment
from odoo.addons.website.controllers.main import QueryURL


class WebsiteAppointment(Appointment):

    #----------------------------------------------------------
    # Appointment HTTP Routes
    #----------------------------------------------------------

    @http.route()
    def calendar_appointments(self, page=1, **kwargs):
        """
        Display the appointments to choose (the display depends of a custom option called 'Card Design')

        :param page: the page number displayed when the appointments are organized by cards

        A param filter_appointment_type_ids can be passed to display a define selection of appointments types.
        This param is propagated through templates to allow people to go back with the initial appointment
        types filter selection
        """
        cards_layout = request.website.viewref('website_appointment.opt_appointments_list_cards').active

        if cards_layout:
            return request.render('website_appointment.appointments_cards_layout', self._prepare_appointments_cards_data(page, **kwargs))
        else:
            return super().calendar_appointments(page, **kwargs)

    #----------------------------------------------------------
    # Utility Methods
    #----------------------------------------------------------

    def _prepare_appointments_cards_data(self, page, **kwargs):
        """
            Compute specific data for the cards layout like the the search bar and the pager.
        """
        domain = self._appointments_base_domain(kwargs.get('filter_appointment_type_ids'))

        Appointment = request.env['calendar.appointment.type']
        website = request.website

        # Add domain related to the search bar
        if kwargs.get('search'):
            domain = expression.AND([domain, [('name', 'ilike', kwargs.get('search'))]])

        APPOINTMENTS_PER_PAGE = 12
        appointment_count = Appointment.search_count(domain)
        pager = website.pager(
            url='/calendar',
            url_args=kwargs,
            total=appointment_count,
            page=page,
            step=APPOINTMENTS_PER_PAGE,
            scope=5,
        )

        appointment_types = Appointment.search(domain, limit=APPOINTMENTS_PER_PAGE, offset=pager['offset'])
        keep = QueryURL('/calendar', search=kwargs.get('search'), filter_appointment_type_ids=kwargs.get('filter_appointment_type_ids'))

        return {
            'appointment_types': appointment_types,
            'current_search': kwargs.get('search'),
            'keep': keep,
            'pager': pager,
        }

    def _get_customer_partner(self):
        partner = super()._get_customer_partner()
        if not partner:
            partner = request.env['website.visitor']._get_visitor_from_request().partner_id
        return partner

    def _get_customer_country(self):
        """
            Find the country from the geoip lib or fallback on the user or the visitor
        """
        country = super()._get_customer_country()
        if not country:
            visitor = request.env['website.visitor']._get_visitor_from_request()
            country = visitor.country_id
        return country

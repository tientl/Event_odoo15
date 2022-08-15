# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.mail_plugin.controllers import mail_plugin


class MailPluginController(mail_plugin.MailPluginController):

    def _get_contact_data(self, partner):
        contact_values = super(MailPluginController, self)._get_contact_data(partner)

        contact_values['tickets'] = self._fetch_partner_tickets(partner) if partner else []

        return contact_values

    def _fetch_partner_tickets(self, partner, offset=0, limit=5):
        """Returns an array containing partner tickets, each ticket will have the following structure :
                {
                    ticket_id: the ticket's id,
                    name: the ticket's name,
                    is_closed: True if the ticket has been closed, false otherwise
                }
        """
        tickets = request.env['helpdesk.ticket'].search(
            [('partner_id', '=', partner.id)], offset=offset, limit=limit)

        return [{
            'ticket_id': ticket.id,
            'name': ticket.display_name,
            'is_closed': ticket.stage_id.is_close
        } for ticket in tickets]

    def _mail_content_logging_models_whitelist(self):
        return super(MailPluginController, self)._mail_content_logging_models_whitelist() + ['helpdesk.ticket']

    def _translation_modules_whitelist(self):
        return super(MailPluginController, self)._translation_modules_whitelist() + ['helpdesk_mail_plugin']

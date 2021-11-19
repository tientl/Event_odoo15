# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from lxml import etree


from odoo import api, fields, models
from odoo.addons.http_routing.models.ir_http import slug


class HelpdeskTeam(models.Model):
    _inherit = ['helpdesk.team']

    website_form_view_id = fields.Many2one('ir.ui.view', string="Form")

    @api.model_create_multi
    def create(self, vals_list):
        teams = super(HelpdeskTeam, self).create(vals_list)
        teams.filtered('use_website_helpdesk_form')._ensure_submit_form_view()
        return teams

    def write(self, vals):
        if 'use_website_helpdesk_form' in vals and vals['use_website_helpdesk_form']:
            self._ensure_submit_form_view()
        return super(HelpdeskTeam, self).write(vals)

    def unlink(self):
        teams_with_submit_form = self.filtered(lambda t: t.website_form_view_id is not False)
        for team in teams_with_submit_form:
            team.website_form_view_id.unlink()
        return super(HelpdeskTeam, self).unlink()

    def _ensure_submit_form_view(self):
        for team in self:
            if not team.website_form_view_id:
                default_form = etree.fromstring(self.env.ref('website_helpdesk_form.ticket_submit_form').arch)
                xmlid = 'website_helpdesk_form.team_form_' + str(team.id)
                form_template = self.env['ir.ui.view'].create({
                    'type': 'qweb',
                    'arch': etree.tostring(default_form),
                    'name': xmlid,
                    'key': xmlid
                })
                self.env['ir.model.data'].create({
                    'module': 'website_helpdesk_form',
                    'name': xmlid.split('.')[1],
                    'model': 'ir.ui.view',
                    'res_id': form_template.id,
                    'noupdate': True
                })

                team.write({'website_form_view_id': form_template.id})

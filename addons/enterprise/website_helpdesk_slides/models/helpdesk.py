# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HelpdeskTeam(models.Model):
    _inherit = "helpdesk.team"

    elearning_id = fields.Many2one('slide.channel', 'eLearning')
    elearning_url = fields.Char('Presentations URL', readonly=True, related='elearning_id.website_url')

    @api.model
    def _create_elearnings_batch(self, vals_list):
        elearnings = self.env['slide.channel'].create(vals_list)
        return {course.name: course for course in elearnings}

    @api.model_create_multi
    def create(self, vals_list):
        elearnings_vals_list = [{'name': vals['name']} for vals in vals_list if vals.get('use_website_helpdesk_slides') and not vals.get('elearning_id')]
        elearnings_by_name = self._create_elearnings_batch(elearnings_vals_list)
        for vals in vals_list:
            if vals.get('use_website_helpdesk_slides') and not vals.get('elearning_id'):
                vals['elearning_id'] = elearnings_by_name.get(vals['name']).id
        return super().create(vals_list)

    def write(self, vals):
        if 'use_website_helpdesk_slides' in vals and not vals['use_website_helpdesk_slides']:
            vals['elearning_id'] = False
        result = super().write(vals)
        elearnings_vals_list = [{'name': team.name} for team in self if team.use_website_helpdesk_slides and not team.elearning_id]
        elearnings_by_name = self._create_elearnings_batch(elearnings_vals_list)
        for team in self:
            if team.use_website_helpdesk_slides and not team.elearning_id:
                team.elearning_id = elearnings_by_name.get(team.name)
        return result
